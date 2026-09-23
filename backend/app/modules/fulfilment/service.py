"""
backend/app/modules/fulfilment/service.py

Phase 5 Fulfilment Options engine — Neo4j backend.

Node labels:
  FulfilmentRequest  — state machine parent
  FulfilmentOption   — candidate option ([:OPTION_OF]->FulfilmentRequest)
  InventoryCache     — latest availability snapshot per source

State transitions managed here:
  AVAILABILITY_CHECKED → (options generated, no state change yet)
  AVAILABILITY_CHECKED / OPTION_SELECTED → OPTION_SELECTED  (select_fulfilment_option)
  OPTION_SELECTED → ALLOCATION_PENDING                       (proceed_to_allocation_pending)

Business rules:
  BR-01: UNKNOWN inventory source → UNCONFIRMED confidence
  BR-03: Options presented without auto-selection
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.errors.exceptions import NotFoundError, ValidationError, ConflictError, UnprocessableError
from app.integrations.contracts.routing import RouteQuery
from app.integrations.contracts.shipping_rate import ShippingRateQuery
from app.integrations.factory import get_routing_provider, get_shipping_rate_provider
from app.audit.service import record_audit_event
from app.logging_config.logger import logger

routing_provider = get_routing_provider()
rate_provider = get_shipping_rate_provider()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _req_row_to_dict(record) -> Dict[str, Any]:
    """Convert a Neo4j Record with r.* keys into a plain dict."""
    return {
        "id": record["r.id"],
        "partNumber": record["r.partNumber"],
        "quantity": record["r.quantity"],
        "destinationBranchId": record["r.destinationBranchId"],
        "customerId": record["r.customerId"],
        "status": record["r.status"],
    }


# ---------------------------------------------------------------------------
# generate_fulfilment_options
# ---------------------------------------------------------------------------

def generate_fulfilment_options(
    session,
    fulfilment_request_id: str,
    test_run_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # 1. Fetch FulfilmentRequest
    req_result = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        RETURN r.id, r.partNumber, r.quantity, r.destinationBranchId, r.customerId, r.status
        """,
        {"id": fulfilment_request_id},
    ).single()
    if not req_result:
        raise NotFoundError(f"Fulfilment request '{fulfilment_request_id}' not found")

    req_id = req_result["r.id"]
    part_number = req_result["r.partNumber"]
    quantity = req_result["r.quantity"]
    dest_branch = req_result["r.destinationBranchId"]
    customer_id = req_result["r.customerId"]
    current_status = req_result["r.status"]

    # Precondition (STATE_TRANSITION_ARCHITECTURE.md §A)
    if current_status not in ["AVAILABILITY_CHECKED", "OPTION_SELECTED"]:
        raise ConflictError(
            f"Cannot compute fulfilment options for request in status '{current_status}'. "
            "Must be in AVAILABILITY_CHECKED or OPTION_SELECTED state."
        )

    # 2. Read latest InventoryCache per source for this part
    caches_all = session.run(
        """
        MATCH (c:InventoryCache {partNumber: $part_number})
        RETURN c.sourceId AS sourceId,
               c.locationId AS locationId,
               c.onHandQty AS onHandQty,
               c.reservedQty AS reservedQty,
               c.allocatedQty AS allocatedQty,
               c.availableQty AS availableQty,
               c.status AS status,
               c.synthetic AS synthetic,
               c.inventoryTimestamp AS inventoryTimestamp
        ORDER BY c.inventoryTimestamp DESC
        """,
        {"part_number": part_number},
    ).data()

    seen: set = set()
    unique_caches = []
    for c in caches_all:
        s_id = c["sourceId"]
        if s_id not in seen:
            seen.add(s_id)
            unique_caches.append(c)
    caches_result = unique_caches

    if not caches_result:
        raise UnprocessableError(
            f"No availability data found for part '{part_number}'. "
            "Availability check must be performed before computing fulfilment options."
        )

    # 3. Remove non-selected options for this request (re-generation)
    session.run(
        """
        MATCH (o:FulfilmentOption {fulfilmentRequestId: $req_id, isSelected: false})
        DELETE o
        """,
        {"req_id": req_id},
    ).consume()

    options: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    partial_sources = []

    # 4. For each available/unknown source — compute routes + rates
    for c in caches_result:
        s_id = c["sourceId"]
        loc_id = c["locationId"]
        on_hand = c["onHandQty"]
        reserved = c["reservedQty"]
        allocated = c["allocatedQty"]
        avail_qty = c["availableQty"]
        inv_status = c["status"]

        # Skip confirmed-empty sources
        if avail_qty == 0 and inv_status != "UNKNOWN":
            continue

        if 0 < avail_qty < quantity and inv_status != "UNKNOWN":
            partial_sources.append(c)

        # Confidence per BR-01
        if inv_status == "UNKNOWN":
            confidence = "UNCONFIRMED"
        elif avail_qty < quantity:
            confidence = "PARTIAL"
        else:
            confidence = "CONFIRMED"

        # Determine source type
        s_upper = s_id.upper()
        if "DEALER" in s_upper:
            source_type = "DEALER"
        elif "REGIONAL" in s_upper:
            source_type = "REGIONAL_DEPOT"
        elif "REMAN" in s_upper:
            source_type = "REMAN_FACILITY"
        else:
            source_type = "CENTRAL_DEPOT"

        # Multi-modal European Transport Engine (Phase 10)
        from app.modules.transport.engine import compute_transport_comparison
        transport_comparison = compute_transport_comparison(
            session=session,
            origin_id=s_id,
            destination_branch_id=dest_branch,
            part_number=part_number,
            quantity=quantity,
            now=now,
        )

        for t_opt in transport_comparison.options:
            opt_id = f"fopt-{uuid.uuid4()}"
            mode = t_opt.mode.value
            carrier = t_opt.carrier_label
            service = t_opt.service_level.value
            transit_days = t_opt.transit_days
            eta = t_opt.estimated_delivery_date
            cost = t_opt.total_cost
            curr = t_opt.currency
            transport_status = "CONFIRMED"
            details = {
                "source_location": loc_id,
                "available_qty": avail_qty,
                "inventory_status": inv_status,
                "distance_band": transport_comparison.distance_band,
                "distance_band_name": transport_comparison.distance_band_name,
                "straight_line_distance_km": transport_comparison.straight_line_distance_km,
                "estimated_road_distance_km": transport_comparison.estimated_road_distance_km,
                "highlight_tag": t_opt.highlight_tag,
                "cutoff_time": t_opt.dispatch_cutoff_time,
                "base_cost": t_opt.base_cost,
                "distance_cost": t_opt.distance_cost,
                "service_level_cost": t_opt.service_level_cost,
                "provenance_note": t_opt.provenance_note,
            }

            create_opt_cypher = """
                CREATE (o:FulfilmentOption {
                    id:                   $id,
                    fulfilmentRequestId:  $req_id,
                    sourceId:             $source_id,
                    sourceType:           $source_type,
                    destinationBranchId:  $dest,
                    transportMode:        $mode,
                    carrierCode:          $carrier,
                    serviceLevel:         $service,
                    transitDays:          $days,
                    eta:                  $eta,
                    transportCost:        $cost,
                    currency:             $curr,
                    confidence:           $confidence,
                    transportDataStatus:  $transport_status,
                    synthetic:            true,
                    data_source:          'SYNTHETIC_DEMO',
                    isSelected:           false,
                    isSplit:              false,
                    detailsJson:          $details,
                    createdAt:            datetime()
                })
            """
            opt_params: Dict[str, Any] = {
                "id": opt_id,
                "req_id": req_id,
                "source_id": s_id,
                "source_type": source_type,
                "dest": dest_branch,
                "mode": mode,
                "carrier": carrier,
                "service": service,
                "days": transit_days,
                "eta": eta,
                "cost": cost,
                "curr": curr,
                "confidence": confidence,
                "transport_status": transport_status,
                "details": json.dumps(details),
            }
            if test_run_id:
                create_opt_cypher = create_opt_cypher.rstrip() + "\nSET o.testRunId = $test_run_id"
                opt_params["test_run_id"] = test_run_id
            session.run(create_opt_cypher, opt_params).consume()

            options.append({
                "id": opt_id,
                "fulfilment_request_id": req_id,
                "source_id": s_id,
                "source_type": source_type,
                "destination_branch_id": dest_branch,
                "transport_mode": mode,
                "carrier_code": carrier,
                "service_level": service,
                "transit_days": transit_days,
                "eta": eta,
                "transport_cost": cost,
                "currency": curr,
                "confidence": confidence,
                "transport_data_status": transport_status,
                "synthetic": True,
                "is_selected": False,
                "is_split": False,
                "details": details,
            })

    # 5. Multi-source / Split Option Support
    if len(partial_sources) >= 2:
        total_split_qty = sum(c["availableQty"] for c in partial_sources)
        if total_split_qty >= quantity:
            opt_id = f"fopt-split-{uuid.uuid4()}"
            split_synthetic = any(c.get("synthetic") for c in partial_sources)
            split_details = {
                "legs": [
                    {
                        "source_id": c["sourceId"],
                        "available_qty": c["availableQty"],
                    }
                    for c in partial_sources
                ],
                "total_available_qty": total_split_qty,
            }
            split_cypher = """
                CREATE (o:FulfilmentOption {
                    id:                   $id,
                    fulfilmentRequestId:  $req_id,
                    sourceId:             'MULTI_SOURCE_SPLIT',
                    sourceType:           'MULTI_DEPOT',
                    destinationBranchId:  $dest,
                    serviceLevel:         'SPLIT',
                    confidence:           'CONFIRMED',
                    transportDataStatus:  'NOT_CONNECTED',
                    synthetic:            $synthetic,
                    isSelected:           false,
                    isSplit:              true,
                    detailsJson:          $details,
                    createdAt:            datetime()
                })
            """
            split_params: Dict[str, Any] = {
                "id": opt_id,
                "req_id": req_id,
                "dest": dest_branch,
                "synthetic": split_synthetic,
                "details": json.dumps(split_details),
            }
            if test_run_id:
                split_cypher = split_cypher.rstrip() + "\nSET o.testRunId = $test_run_id"
                split_params["test_run_id"] = test_run_id
            session.run(split_cypher, split_params).consume()

            options.append({
                "id": opt_id,
                "fulfilment_request_id": req_id,
                "source_id": "MULTI_SOURCE_SPLIT",
                "source_type": "MULTI_DEPOT",
                "destination_branch_id": dest_branch,
                "transport_mode": None,
                "carrier_code": None,
                "service_level": "SPLIT",
                "transit_days": None,
                "eta": None,
                "transport_cost": None,
                "currency": None,
                "confidence": "CONFIRMED",
                "transport_data_status": "NOT_CONNECTED",
                "synthetic": split_synthetic,
                "is_selected": False,
                "is_split": True,
                "details": split_details,
            })

    return options


# ---------------------------------------------------------------------------
# get_fulfilment_options
# ---------------------------------------------------------------------------

def get_fulfilment_options(
    session,
    fulfilment_request_id: str,
) -> List[Dict[str, Any]]:
    records = session.run(
        """
        MATCH (o:FulfilmentOption {fulfilmentRequestId: $req_id})
        RETURN o.id, o.fulfilmentRequestId, o.sourceId, o.sourceType,
               o.destinationBranchId, o.transportMode, o.carrierCode,
               o.serviceLevel, o.transitDays, o.eta, o.transportCost,
               o.currency, o.confidence, o.transportDataStatus, o.synthetic, o.isSelected, o.isSplit, o.detailsJson
        ORDER BY o.createdAt ASC
        """,
        {"req_id": fulfilment_request_id},
    ).data()

    options = []
    for r in records:
        options.append({
            "id": r["o.id"],
            "fulfilment_request_id": r["o.fulfilmentRequestId"],
            "source_id": r["o.sourceId"],
            "source_type": r["o.sourceType"],
            "destination_branch_id": r["o.destinationBranchId"],
            "transport_mode": r["o.transportMode"],
            "carrier_code": r["o.carrierCode"],
            "service_level": r["o.serviceLevel"],
            "transit_days": r["o.transitDays"],
            "eta": r["o.eta"],
            "transport_cost": float(r["o.transportCost"]) if r["o.transportCost"] is not None else None,
            "currency": r["o.currency"],
            "confidence": r["o.confidence"],
            "transport_data_status": r["o.transportDataStatus"] or "NOT_CONNECTED",
            "synthetic": bool(r["o.synthetic"]),
            "is_selected": bool(r["o.isSelected"]),
            "is_split": bool(r["o.isSplit"]),
            "details": json.loads(r["o.detailsJson"]) if r["o.detailsJson"] else {},
        })
    return options


# ---------------------------------------------------------------------------
# select_fulfilment_option
# ---------------------------------------------------------------------------

def select_fulfilment_option(
    session,
    fulfilment_request_id: str,
    option_id: str,
    actor_id: str = "CUSTOMER",
    actor_role: str = "CUSTOMER",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    # 1. Check request state
    req_result = session.run(
        "MATCH (r:FulfilmentRequest {id: $id}) RETURN r.id, r.status",
        {"id": fulfilment_request_id},
    ).single()
    if not req_result:
        raise NotFoundError(f"Fulfilment request '{fulfilment_request_id}' not found")

    r_id = req_result["r.id"]
    status = req_result["r.status"]
    if status not in ["AVAILABILITY_CHECKED", "OPTION_SELECTED"]:
        raise ConflictError(
            f"Cannot select fulfilment option in state '{status}'. "
            "Must be in AVAILABILITY_CHECKED or OPTION_SELECTED state."
        )

    # 2. Check option exists and belongs to request
    opt_result = session.run(
        """
        MATCH (o:FulfilmentOption {id: $opt_id, fulfilmentRequestId: $req_id})
        RETURN o.id, o.sourceId, o.sourceType, o.transportMode,
               o.carrierCode, o.serviceLevel, o.transportCost, o.confidence
        """,
        {"opt_id": option_id, "req_id": fulfilment_request_id},
    ).single()
    if not opt_result:
        raise NotFoundError(
            f"Fulfilment option '{option_id}' not found for request '{fulfilment_request_id}'"
        )

    # 3. Deselect all options for this request, then select the chosen one
    session.run(
        """
        MATCH (o:FulfilmentOption {fulfilmentRequestId: $req_id})
        SET o.isSelected = false
        """,
        {"req_id": fulfilment_request_id},
    ).consume()
    session.run(
        "MATCH (o:FulfilmentOption {id: $opt_id}) SET o.isSelected = true",
        {"opt_id": option_id},
    ).consume()

    # 4. Transition FulfilmentRequest → OPTION_SELECTED
    session.run(
        """
        MATCH (r:FulfilmentRequest {id: $req_id})
        SET r.status           = 'OPTION_SELECTED',
            r.selectedOptionId = $opt_id,
            r.updatedAt        = datetime()
        """,
        {"req_id": fulfilment_request_id, "opt_id": option_id},
    ).consume()

    # 5. Audit
    record_audit_event(
        session=session,
        action="FULFILMENT_OPTION_SELECTED",
        entity_type="FULFILMENT_REQUEST",
        entity_id=fulfilment_request_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=status,
        new_state="OPTION_SELECTED",
        details={
            "selected_option_id": option_id,
            "source_id": opt_result["o.sourceId"],
            "source_type": opt_result["o.sourceType"],
            "transport_mode": opt_result["o.transportMode"],
            "carrier_code": opt_result["o.carrierCode"],
            "confidence": opt_result["o.confidence"],
        },
        test_run_id=test_run_id,
    )

    return {
        "fulfilment_request_id": fulfilment_request_id,
        "status": "OPTION_SELECTED",
        "selected_option_id": option_id,
    }


# ---------------------------------------------------------------------------
# proceed_to_allocation_pending
# ---------------------------------------------------------------------------

def proceed_to_allocation_pending(
    session,
    fulfilment_request_id: str,
    actor_id: str = "CUSTOMER",
    actor_role: str = "CUSTOMER",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    # 1. Check request state
    req_result = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        RETURN r.id, r.status, r.selectedOptionId
        """,
        {"id": fulfilment_request_id},
    ).single()
    if not req_result:
        raise NotFoundError(f"Fulfilment request '{fulfilment_request_id}' not found")

    r_id = req_result["r.id"]
    status = req_result["r.status"]
    selected_opt = req_result["r.selectedOptionId"]

    # Precondition: strictly OPTION_SELECTED
    if status != "OPTION_SELECTED":
        raise ConflictError(
            f"Cannot advance to ALLOCATION_PENDING from state '{status}'. "
            "Request must be in OPTION_SELECTED state with a valid selected option."
        )

    if not selected_opt:
        raise ValidationError("Cannot advance to ALLOCATION_PENDING: No fulfilment option selected.")

    # 2. Transition → ALLOCATION_PENDING
    session.run(
        """
        MATCH (r:FulfilmentRequest {id: $req_id})
        SET r.status    = 'ALLOCATION_PENDING',
            r.updatedAt = datetime()
        """,
        {"req_id": fulfilment_request_id},
    ).consume()

    # 3. Audit
    record_audit_event(
        session=session,
        action="ADVANCED_TO_ALLOCATION_PENDING",
        entity_type="FULFILMENT_REQUEST",
        entity_id=fulfilment_request_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="OPTION_SELECTED",
        new_state="ALLOCATION_PENDING",
        details={"selected_option_id": selected_opt},
        test_run_id=test_run_id,
    )

    return {
        "fulfilment_request_id": fulfilment_request_id,
        "status": "ALLOCATION_PENDING",
        "selected_option_id": selected_opt,
    }
