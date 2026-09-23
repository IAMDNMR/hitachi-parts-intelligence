"""
backend/app/modules/availability/service.py

Phase 4 Availability Engine — Neo4j backend.

Data written to Neo4j:
  - (:FulfilmentRequest) node — created or verified
  - (:InventoryCache) nodes — one per source, each availability check
  - (:AuditRecord) node — via audit service

Business rules enforced:
  - BR-01: Stale inventory (age > TTL or is_stale=True) → status UNKNOWN, never 0
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.errors.exceptions import NotFoundError, ValidationError, UnprocessableError
from app.integrations.contracts.inventory import (
    SourceAvailabilityQuery,
    SourceInventoryItem,
    InventoryStatus,
    AvailabilityResponse,
)
from app.integrations.factory import get_inventory_provider
from app.audit.service import record_audit_event
from app.logging_config.logger import logger


def check_availability(
    session,
    fulfilment_request_id: Optional[str],
    part_number: str,
    quantity: int,
    destination_branch_id: str = "DEALER-BRANCH-NL-01",
    customer_id: str = "CUST-DEFAULT",
    machine_context: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero")

    # 1. Resolve or create FulfilmentRequest node
    if fulfilment_request_id:
        result = session.run(
            "MATCH (r:FulfilmentRequest {id: $id}) RETURN r.id, r.status, r.partNumber, r.quantity",
            {"id": fulfilment_request_id},
        ).single()
        if not result:
            raise NotFoundError(f"Fulfilment request '{fulfilment_request_id}' not found")

        req_id = result["r.id"]
        current_status = result["r.status"]
        if current_status not in ["DRAFT", "REQUESTED", "AVAILABILITY_CHECKED"]:
            raise UnprocessableError(
                f"Cannot run availability check on fulfilment request in status '{current_status}'"
            )
    else:
        req_id = f"freq-{uuid.uuid4()}"
        create_cypher = """
            CREATE (r:FulfilmentRequest {
                id:                  $id,
                partNumber:          $part_number,
                quantity:            $quantity,
                machineContext:      $machine_context,
                customerId:          $customer_id,
                destinationBranchId: $destination_branch_id,
                status:              'REQUESTED',
                createdAt:           datetime(),
                updatedAt:           datetime()
            })
        """
        params: Dict[str, Any] = {
            "id": req_id,
            "part_number": part_number,
            "quantity": quantity,
            "machine_context": machine_context,
            "customer_id": customer_id,
            "destination_branch_id": destination_branch_id,
        }
        if test_run_id:
            create_cypher = create_cypher.rstrip() + "\nSET r.testRunId = $test_run_id"
            params["test_run_id"] = test_run_id
        session.run(create_cypher, params).consume()

    # 2. Query Inventory Provider
    provider = get_inventory_provider()
    query_dto = SourceAvailabilityQuery(
        part_number=part_number,
        quantity=quantity,
        destination_branch_id=destination_branch_id,
        customer_id=customer_id,
        machine_context=machine_context,
    )
    raw_sources = provider.get_availability(query_dto)

    # 3. Process BR-01 UNKNOWN discipline and Freshness check
    now = datetime.now(timezone.utc)
    ttl_seconds = settings.AVAILABILITY_FRESHNESS_TTL_SECONDS
    processed_sources: List[SourceInventoryItem] = []

    total_avail_qty = 0
    has_unknown = False
    reman_available = False

    for s in raw_sources:
        try:
            ts = datetime.fromisoformat(s.inventory_timestamp)
            age_seconds = (now - ts).total_seconds()
        except Exception:
            age_seconds = ttl_seconds + 999

        if age_seconds > ttl_seconds or s.is_stale:
            # BR-01: mark as UNKNOWN
            s.status = InventoryStatus.UNKNOWN
            s.is_stale = True

        if s.status == InventoryStatus.UNKNOWN:
            has_unknown = True
        else:
            total_avail_qty += s.available_qty

        if s.source_type == "REMAN_FACILITY" and s.available_qty > 0:
            reman_available = True

        # 4. Save InventoryCache node
        cache_id = f"icache-{uuid.uuid4()}"
        cache_cypher = """
            CREATE (c:InventoryCache {
                id:                 $id,
                partNumber:         $part_number,
                sourceId:           $source_id,
                locationId:         $location_id,
                onHandQty:          $on_hand,
                reservedQty:        $reserved,
                allocatedQty:       $allocated,
                availableQty:       $available,
                status:             $status,
                provenance:         $provenance,
                synthetic:          $synthetic,
                data_source:        $data_source,
                inventoryTimestamp: datetime()
            })
        """
        cache_params: Dict[str, Any] = {
            "id": cache_id,
            "part_number": part_number,
            "source_id": s.source_id,
            "location_id": s.location_id,
            "on_hand": s.on_hand_qty,
            "reserved": s.reserved_qty,
            "allocated": s.allocated_qty,
            "available": s.available_qty,
            "status": s.status.value,
            "provenance": s.provenance,
            "synthetic": s.provenance == "SYNTHETIC_DEMO",
            "data_source": "SYNTHETIC_DEMO" if s.provenance == "SYNTHETIC_DEMO" else None,
        }
        if test_run_id:
            cache_cypher = cache_cypher.rstrip() + "\nSET c.testRunId = $test_run_id"
            cache_params["test_run_id"] = test_run_id
        session.run(cache_cypher, cache_params).consume()

        processed_sources.append(s)

    # Calculate overall status
    if not processed_sources or has_unknown:
        if total_avail_qty >= quantity and not any(
            s.status == InventoryStatus.UNKNOWN for s in processed_sources
        ):
            overall_status = "AVAILABLE"
        elif total_avail_qty > 0:
            overall_status = "PARTIAL"
        else:
            overall_status = "UNKNOWN"
    else:
        if total_avail_qty >= quantity:
            overall_status = "AVAILABLE"
        elif total_avail_qty > 0:
            overall_status = "PARTIAL"
        else:
            overall_status = "UNAVAILABLE"

    # 5. Update FulfilmentRequest status
    session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        SET r.status    = 'AVAILABILITY_CHECKED',
            r.updatedAt = datetime()
        """,
        {"id": req_id},
    ).consume()

    # 6. Audit
    record_audit_event(
        session=session,
        action="AVAILABILITY_CHECKED",
        entity_type="FULFILMENT_REQUEST",
        entity_id=req_id,
        previous_state="REQUESTED",
        new_state="AVAILABILITY_CHECKED",
        details={
            "part_number": part_number,
            "requested_qty": quantity,
            "overall_status": overall_status,
            "total_available_qty": total_avail_qty,
            "source_count": len(processed_sources),
        },
        test_run_id=test_run_id,
    )

    response_data = {
        "fulfilment_request_id": req_id,
        "part_number": part_number,
        "requested_qty": quantity,
        "overall_status": overall_status,
        "total_available_qty": total_avail_qty,
        "reman_alternative_available": reman_available,
        "checked_at": now.isoformat(),
        "freshness_ttl_seconds": ttl_seconds,
        "sources": [s.model_dump() for s in processed_sources],
        "availabilityResults": [s.model_dump() for s in processed_sources],
    }

    return response_data
