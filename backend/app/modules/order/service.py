"""
backend/app/modules/order/service.py

Phase 6 Order domain service — Neo4j backend.

Canonical state names per docs/business-process/ORDER_PROCESS.md §4 and
docs/architecture/ORDER_ARCHITECTURE.md §2:

    CREATED -> ACCEPTED -> (fulfilled, out of scope here)
            -> CANCELLED

CREATED corresponds to internal assembly; this module also uses an internal
pre-CREATED `DRAFT` step purely to make idempotent request handling and the
"never auto-submit" UI requirement explicit — DRAFT is not one of the
documented business states and is never returned as a final order status.

Rules enforced:
  - Order requires a CONFIRMED allocation for the fulfilment request.
  - Quantity matches the allocated quantity.
  - Canonical Part identity preserved (MATCH, never CREATE).
  - Pricing only from an authoritative PricingProvider; NOT_AVAILABLE is
    never converted into a fabricated number.
  - Order creation is idempotent (delegated to app.idempotency.service at
    the route layer, mirroring every other module).
  - No import of the LLM provider anywhere in this module.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.audit.service import record_audit_event
from app.errors.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.integrations.contracts.order import OrderSubmission
from app.integrations.contracts.pricing import PricingQuery
from app.integrations.factory import get_order_provider, get_pricing_provider
from app.modules.allocation.service import get_allocation, is_demo_part_number

order_provider = get_order_provider()
pricing_provider = get_pricing_provider()


def create_order(
    session,
    fulfilment_request_id: str,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    req = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        RETURN r.id AS id, r.status AS status, r.partNumber AS partNumber,
               r.destinationBranchId AS destinationBranchId, r.selectedOptionId AS selectedOptionId
        """,
        {"id": fulfilment_request_id},
    ).single()
    if not req:
        raise NotFoundError(f"Fulfilment request '{fulfilment_request_id}' not found")
    req = dict(req)

    # An order already exists for this request -> idempotent no-op path
    # (route-layer idempotency key handles the primary case; this guards
    # direct/duplicate calls without a key too). Checked BEFORE the
    # allocation-status check because a successful first call consumes the
    # allocation (CONFIRMED -> CONSUMED), so a duplicate request must still
    # short-circuit here rather than hit the CONFIRMED-required guard below.
    existing = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $req_id})-[:HAS_ORDER]->(o:Order)
        RETURN o.id AS id, o.status AS status
        """,
        {"req_id": fulfilment_request_id},
    ).single()
    if existing:
        return get_order(session, existing["id"])

    # Do not create an order before successful allocation.
    alloc = get_allocation(session, fulfilment_request_id)
    if alloc["status"] != "CONFIRMED":
        raise ConflictError(
            f"Cannot create order: allocation is in status '{alloc['status']}', requires CONFIRMED."
        )

    part = session.run(
        "MATCH (p:Part {part_number: $pn}) RETURN p.part_id AS part_id, p.part_number AS part_number",
        {"pn": req["partNumber"]},
    ).single()
    if not part and is_demo_part_number(req["partNumber"]):
        part = {"part_id": req["partNumber"], "part_number": req["partNumber"]}  # DEMO- reference: no canonical Part node
    if not part:
        raise NotFoundError(f"Part '{req['partNumber']}' not found (canonical Part must exist)")
    part = dict(part)

    quantity = alloc["quantity"]

    quote = pricing_provider.get_price(
        PricingQuery(part_number=req["partNumber"], quantity=quantity)
    )

    order_id = f"order-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)

    create_order_cypher = """
        CREATE (o:Order {
            id:                  $id,
            fulfilmentRequestId: $req_id,
            partNumber:          $part_number,
            quantity:            $quantity,
            sourceId:            $source_id,
            destinationBranchId: $dest,
            unitPrice:           $unit_price,
            currency:            $currency,
            pricingStatus:       $pricing_status,
            status:              'CREATED',
            provenance:          'INTERNAL_TEST_WORKFLOW',
            external_order_id:   $external_order_id,
            synced_at:           $synced_at,
            data_source:         $data_source,
            createdAt:           datetime(),
            updatedAt:           datetime()
        })
    """
    order_params = {
        "id": order_id,
        "req_id": fulfilment_request_id,
        "part_number": req["partNumber"],
        "quantity": quantity,
        "source_id": alloc["sourceId"],
        "dest": req["destinationBranchId"],
        "unit_price": quote.unit_price,
        "currency": quote.currency,
        "pricing_status": quote.status,
        "external_order_id": None,
        "synced_at": None,
        "data_source": "SYNTHETIC_DEMO",
    }
    # Tag with testRunId when this Order is created by an automated test run,
    # so the per-test cleanup fixture (see tests/conftest.py) can delete it —
    # without this, every API-level test leaks a real, untagged Order into
    # the live database (Phase 10B finding).
    if test_run_id:
        create_order_cypher = create_order_cypher.rstrip() + "\nSET o.testRunId = $test_run_id"
        order_params["test_run_id"] = test_run_id
    session.run(create_order_cypher, order_params).consume()

    session.run(
        """
        MATCH (o:Order {id: $order_id})
        MATCH (a:Allocation {id: $alloc_id})
        MATCH (r:FulfilmentRequest {id: $req_id})
        MERGE (o)-[:BASED_ON_ALLOCATION]->(a)
        MERGE (r)-[:HAS_ORDER]->(o)
        SET a.status = 'CONSUMED'
        """,
        {"order_id": order_id, "alloc_id": alloc["id"], "req_id": fulfilment_request_id},
    ).consume()

    session.run(
        """
        MATCH (r:FulfilmentRequest {id: $req_id})
        SET r.status = 'ORDERED', r.updatedAt = datetime()
        """,
        {"req_id": fulfilment_request_id},
    ).consume()

    record_audit_event(
        session=session,
        action="ORDER_CREATED",
        entity_type="ORDER",
        entity_id=order_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=None,
        new_state="CREATED",
        details={
            "fulfilment_request_id": fulfilment_request_id,
            "allocation_id": alloc["id"],
            "part_number": req["partNumber"],
            "quantity": quantity,
            "pricing_status": quote.status,
        },
        test_run_id=test_run_id,
    )

    # Internal test/development submission attempt — never presented as a
    # real HCME integration (see TestOrderProvider docstring).
    submission_result = order_provider.submit_order(
        OrderSubmission(
            order_id=order_id,
            part_number=req["partNumber"],
            quantity=quantity,
            source_id=alloc["sourceId"],
            destination_branch_id=req["destinationBranchId"],
        )
    )

    ext_order_id = submission_result.external_order_reference
    synced_at = datetime.now(timezone.utc).isoformat()
    data_source = "HCME_SAP_ERP" if submission_result.accepted else "SYNTHETIC_DEMO"
    session.run(
        """
        MATCH (o:Order {id: $id})
        SET o.external_order_id = $ext_id,
            o.synced_at = $synced_at,
            o.data_source = $data_source,
            o.synthetic = ($data_source = 'SYNTHETIC_DEMO')
        """,
        {"id": order_id, "ext_id": ext_order_id, "synced_at": synced_at, "data_source": data_source},
    ).consume()

    record_audit_event(
        session=session,
        action="ORDER_SUBMISSION_ATTEMPTED",
        entity_type="ORDER",
        entity_id=order_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="CREATED",
        new_state="CREATED",
        source="TEST_ORDER_PROVIDER",
        details={"provider_status": submission_result.status, "message": submission_result.message},
        test_run_id=test_run_id,
    )

    return get_order(session, order_id)


def get_order(session, order_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (o:Order {id: $id})
        RETURN o.id AS id, o.fulfilmentRequestId AS fulfilmentRequestId,
               o.partNumber AS partNumber, o.quantity AS quantity,
               o.sourceId AS sourceId, o.destinationBranchId AS destinationBranchId,
               o.unitPrice AS unitPrice, o.currency AS currency,
               o.pricingStatus AS pricingStatus, o.status AS status,
               o.provenance AS provenance, o.createdAt AS createdAt,
               o.external_order_id AS external_order_id,
               o.synced_at AS synced_at,
               o.data_source AS data_source
        """,
        {"id": order_id},
    ).single()
    if not row:
        raise NotFoundError(f"Order '{order_id}' not found")
    data = dict(row)
    if data.get("createdAt") is not None:
        data["createdAt"] = str(data["createdAt"])
    data["external_order_id"] = data.get("external_order_id")
    data["synced_at"] = data.get("synced_at")
    data["data_source"] = data.get("data_source") or "SYNTHETIC_DEMO"
    data["integration_status"] = "NOT_CONNECTED"
    data["integration_label"] = "TEST/DEVELOPMENT — no real HCME order system is connected"
    return data


def accept_order(
    session,
    order_id: str,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    order = get_order(session, order_id)
    if order["status"] != "CREATED":
        raise ConflictError(
            f"Cannot accept order '{order_id}' in status '{order['status']}'. Requires CREATED."
        )

    session.run(
        "MATCH (o:Order {id: $id}) SET o.status = 'ACCEPTED', o.updatedAt = datetime()",
        {"id": order_id},
    ).consume()

    record_audit_event(
        session=session,
        action="ORDER_ACCEPTED",
        entity_type="ORDER",
        entity_id=order_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="CREATED",
        new_state="ACCEPTED",
        test_run_id=test_run_id,
    )

    return get_order(session, order_id)


def cancel_order(
    session,
    order_id: str,
    reason: str = "Order cancelled",
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    order = get_order(session, order_id)
    if order["status"] == "CANCELLED":
        return order

    # If linked to a shipment that is already shipped/delivered, cannot cancel order directly
    sh = session.run(
        "MATCH (o:Order {id: $id})-[:HAS_SHIPMENT]->(sh:Shipment) RETURN sh.status AS status",
        {"id": order_id},
    ).single()
    if sh and sh["status"] in ("DISPATCHED", "IN_TRANSIT", "DELIVERED"):
        raise ConflictError(
            f"Cannot cancel order '{order_id}' whose shipment is already in status '{sh['status']}'."
        )

    session.run(
        "MATCH (o:Order {id: $id}) SET o.status = 'CANCELLED', o.updatedAt = datetime()",
        {"id": order_id},
    ).consume()

    # Cancel linked FulfilmentRequest
    session.run(
        """
        MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o:Order {id: $id})
        SET fr.status = 'CANCELLED', fr.updatedAt = datetime()
        """,
        {"id": order_id},
    ).consume()

    record_audit_event(
        session=session,
        action="ORDER_CANCELLED",
        entity_type="ORDER",
        entity_id=order_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=order["status"],
        new_state="CANCELLED",
        details={"reason": reason},
        test_run_id=test_run_id,
    )

    return get_order(session, order_id)


# ---------------------------------------------------------------------------
# Phase 10C — Order State Machine Advancement & Invariant Enforcement
#
# State machine (full):
#   CREATED → ACCEPTED → FULFILLED → CLOSED
#                      ↘ CANCELLED (from CREATED or ACCEPTED only)
#
# Neo4j-driven advancement: the Order's effective state is determined by the
# linked Shipment and ServiceJob states. This function advances the Order node
# without ever regressing it.
# ---------------------------------------------------------------------------

# Valid forward-only progressions.
_VALID_ADVANCES = {
    "CREATED": {"ACCEPTED", "FULFILLED", "CANCELLED"},
    "ACCEPTED": {"FULFILLED", "CANCELLED"},
    "FULFILLED": {"CLOSED"},
    "CLOSED": set(),      # terminal
    "CANCELLED": set(),   # terminal
}

# Shipment statuses that mean the part has been delivered.
_SHIPMENT_DELIVERED_STATUSES = {"DELIVERED"}

# ServiceJob statuses that mean the job is complete.
_SERVICE_COMPLETED_STATUSES = {"COMPLETED", "CLOSED"}


def get_order_lifecycle(session, order_id: str) -> Dict[str, Any]:
    """Read the linked Shipment and ServiceJob states for an Order.

    Returns a dict with effective_status (the computed state) and the raw
    states of linked records, so callers can decide whether to advance.
    """
    row = session.run(
        """
        MATCH (o:Order {id: $id})
        OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
        OPTIONAL MATCH (sh)-[:HAS_SERVICE_JOB]->(sj:ServiceJob)
        RETURN o.status AS order_status,
               sh.status AS shipment_status,
               sh.shipment_id AS shipment_id,
               sj.status AS service_job_status,
               sj.service_job_id AS service_job_id
        """,
        {"id": order_id},
    ).single()
    if not row:
        raise NotFoundError(f"Order '{order_id}' not found")
    order_status = row["order_status"]
    shipment_status = row["shipment_status"]
    service_job_status = row["service_job_status"]
    # Compute effective status based on downstream state.
    if service_job_status in _SERVICE_COMPLETED_STATUSES:
        effective_status = "CLOSED"
    elif shipment_status in _SHIPMENT_DELIVERED_STATUSES:
        effective_status = "FULFILLED"
    else:
        effective_status = order_status
    return {
        "order_id": order_id,
        "order_status": order_status,
        "effective_status": effective_status,
        "shipment_id": row["shipment_id"],
        "shipment_status": shipment_status,
        "service_job_id": row["service_job_id"],
        "service_job_status": service_job_status,
        "state_consistent": (order_status == effective_status
                             or effective_status in _VALID_ADVANCES.get(order_status, set())),
    }


def enforce_order_state_invariant(session, order_id: str) -> Dict[str, Any]:
    """Check and optionally fix a state inconsistency for one Order.

    Rule: An Order cannot remain in CREATED or ACCEPTED status when its linked
    Shipment is DELIVERED or its linked ServiceJob is COMPLETED. This is the
    invariant defined in Phase 10C.

    Returns a dict describing what was found and what (if anything) was fixed.
    Does NOT raise — callers can decide what to do with the result.
    """
    lifecycle = get_order_lifecycle(session, order_id)
    if lifecycle["state_consistent"]:
        return {**lifecycle, "action": "NONE", "note": "State is consistent."}
    # Advance to effective_status.
    target = lifecycle["effective_status"]
    current = lifecycle["order_status"]
    if target not in _VALID_ADVANCES.get(current, set()):
        return {
            **lifecycle, "action": "SKIPPED",
            "note": (f"Cannot advance from {current} to {target}: "
                     "not a valid forward transition.")
        }
    session.run(
        "MATCH (o:Order {id: $id}) SET o.status = $status, o.updatedAt = datetime()",
        {"id": order_id, "status": target},
    ).consume()
    record_audit_event(
        session=session,
        action="ORDER_STATE_ADVANCED",
        entity_type="ORDER",
        entity_id=order_id,
        actor_id="SYSTEM",
        actor_role="SYSTEM",
        previous_state=current,
        new_state=target,
        details={
            "reason": "Phase 10C invariant enforcement: downstream state advanced order",
            "shipment_status": lifecycle["shipment_status"],
            "service_job_status": lifecycle["service_job_status"],
        },
    )
    return {**lifecycle, "order_status": target, "action": "ADVANCED",
            "note": f"Order advanced from {current} to {target}."}


def advance_order_state(
    session,
    order_id: str,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Advance an Order's state based on its downstream Shipment/ServiceJob state.

    Called from the shipment and service-job post-update hooks so Order status
    stays synchronised. Idempotent: advancing an already-current state is a no-op.
    """
    lifecycle = get_order_lifecycle(session, order_id)
    target = lifecycle["effective_status"]
    current = lifecycle["order_status"]
    if target == current:
        return get_order(session, order_id)
    if target not in _VALID_ADVANCES.get(current, set()):
        return get_order(session, order_id)  # Cannot advance — no error raised
    params = {"id": order_id, "status": target}
    cypher = "MATCH (o:Order {id: $id}) SET o.status = $status, o.updatedAt = datetime()"
    if test_run_id:
        cypher += "\nSET o.testRunId = $run"
        params["run"] = test_run_id
    session.run(cypher, params).consume()
    record_audit_event(
        session=session,
        action=f"ORDER_{target}",
        entity_type="ORDER",
        entity_id=order_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=current,
        new_state=target,
        details={
            "shipment_status": lifecycle["shipment_status"],
            "service_job_status": lifecycle["service_job_status"],
        },
        test_run_id=test_run_id,
    )
    return get_order(session, order_id)
