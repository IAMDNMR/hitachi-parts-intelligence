"""
backend/app/modules/allocation/service.py

Phase 6 Allocation domain service — Neo4j backend.

State machine (canonical names per docs/business-process/ALLOCATION_PROCESS.md
and docs/architecture/ALLOCATION_ARCHITECTURE.md — NOT invented here):

    FulfilmentRequest: OPTION_SELECTED -> ALLOCATION_PENDING (fulfilment module)
    Allocation:        PENDING -> RESERVED -> CONFIRMED -> CONSUMED
                                            -> EXPIRED
                        PENDING -> FAILED
                        RESERVED/CONFIRMED -> RELEASED

This module never imports the LLM provider — Gemini has zero role in
Allocation (verified: no `import app.modules.intelligence...` anywhere here).

Concurrency + idempotency are delegated to the existing, already-tested
primitives:
  - app.modules.allocation.ledger.attempt_inventory_allocation  (optimistic
    version-locked InventoryLedger — ADR-007 / test_allocation_concurrency_lock)
  - app.idempotency.service (IdempotencyRecord cache, used at the route layer)

This module adds what ledger.py deliberately does not do:
  - Precondition validation (FulfilmentRequest exists & in ALLOCATION_PENDING,
    selected FulfilmentOption exists, canonical Part exists).
  - Reading the *authoritative* available quantity from the existing
    Availability (:InventoryCache) snapshot instead of ever inventing one.
  - Refusing to allocate against UNKNOWN/stale availability.
  - Linking the canonical graph relationships (HAS_ALLOCATION, ALLOCATES).
  - The CONFIRMED / RELEASED transitions and FulfilmentRequest -> ALLOCATED.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.audit.service import record_audit_event
from app.errors.exceptions import ConflictError, NotFoundError, UnprocessableError, ValidationError
from app.logging_config.logger import logger
from app.modules.allocation.ledger import attempt_inventory_allocation

# Note: deliberately NOT importing anything from app.modules.intelligence.*


def _load_fulfilment_request(session, fulfilment_request_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        RETURN r.id AS id, r.status AS status, r.partNumber AS partNumber,
               r.quantity AS quantity, r.selectedOptionId AS selectedOptionId
        """,
        {"id": fulfilment_request_id},
    ).single()
    if not row:
        raise NotFoundError(f"Fulfilment request '{fulfilment_request_id}' not found")
    return dict(row)


def _load_selected_option(session, fulfilment_request_id: str, option_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (o:FulfilmentOption {id: $opt_id, fulfilmentRequestId: $req_id})
        RETURN o.id AS id, o.sourceId AS sourceId, o.confidence AS confidence
        """,
        {"opt_id": option_id, "req_id": fulfilment_request_id},
    ).single()
    if not row:
        raise NotFoundError(
            f"Fulfilment option '{option_id}' not found for request '{fulfilment_request_id}'"
        )
    return dict(row)


def _load_canonical_part(session, part_number: str) -> Dict[str, Any]:
    row = session.run(
        "MATCH (p:Part {part_number: $pn}) RETURN p.part_id AS part_id, p.part_number AS part_number",
        {"pn": part_number},
    ).single()
    if not row:
        raise NotFoundError(f"Part '{part_number}' not found (canonical Part must exist)")
    return dict(row)


def _load_authoritative_availability(session, part_number: str, source_id: str) -> Dict[str, Any]:
    """
    Read the latest Availability snapshot for (part, source) written by the
    Availability module. Never invents a figure. UNKNOWN/stale is returned
    as-is and MUST be rejected by the caller — never silently treated as
    zero or as available.
    """
    row = session.run(
        """
        MATCH (c:InventoryCache {partNumber: $pn, sourceId: $source_id})
        RETURN c.availableQty AS availableQty, c.status AS status,
               c.inventoryTimestamp AS inventoryTimestamp
        ORDER BY c.inventoryTimestamp DESC
        LIMIT 1
        """,
        {"pn": part_number, "source_id": source_id},
    ).single()
    if not row:
        return {"availableQty": None, "status": "UNKNOWN", "inventoryTimestamp": None}
    return dict(row)


def create_allocation(
    session,
    fulfilment_request_id: str,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    idempotency_key: Optional[str] = None,
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Allocate inventory for a FulfilmentRequest's selected FulfilmentOption.

    Preconditions (all validated here, none assumed):
      - FulfilmentRequest exists and is in ALLOCATION_PENDING.
      - It has a selectedOptionId, and that FulfilmentOption exists.
      - The canonical Part (matched, never created) exists for the request's
        partNumber.
      - Availability for (part, source) is known and not stale/UNKNOWN.
    """
    req = _load_fulfilment_request(session, fulfilment_request_id)

    if req["status"] != "ALLOCATION_PENDING":
        raise ConflictError(
            f"Cannot allocate for request in status '{req['status']}'. "
            "Must be in ALLOCATION_PENDING state (proceed-to-allocation must run first)."
        )

    option_id = req["selectedOptionId"]
    if not option_id:
        raise ValidationError("Cannot allocate: no fulfilment option selected on this request")

    quantity = req["quantity"]
    if quantity is None or quantity <= 0:
        raise ValidationError("Fulfilment request quantity must be greater than zero")

    part_number = req["partNumber"]
    part = _load_canonical_part(session, part_number)

    option = _load_selected_option(session, fulfilment_request_id, option_id)
    source_id = option["sourceId"]

    # MULTI_SOURCE_SPLIT options have no single ledger row to allocate against —
    # out of scope for this synchronous single-source allocator.
    if source_id == "MULTI_SOURCE_SPLIT":
        raise UnprocessableError(
            "Split multi-source fulfilment options are not yet supported by Allocation"
        )

    availability = _load_authoritative_availability(session, part_number, source_id)
    if availability["status"] == "UNKNOWN" or availability["availableQty"] is None:
        raise UnprocessableError(
            "Cannot allocate against UNKNOWN or unconfirmed availability",
            details={"part_number": part_number, "source_id": source_id, "status": "UNKNOWN"},
        )

    idemp_key = idempotency_key or f"alloc-{fulfilment_request_id}"

    success, result_code, details = attempt_inventory_allocation(
        session=session,
        part_number=part_number,
        source_id=source_id,
        requested_qty=quantity,
        fulfilment_request_id=fulfilment_request_id,
        idempotency_key=idemp_key,
        initial_stock_for_test=availability["availableQty"],
        test_run_id=test_run_id,
    )

    if not success:
        status_for_conflict = "CONFLICT" if result_code == "CONCURRENCY_VERSION_MISMATCH" else "FAILED"
        record_audit_event(
            session=session,
            action="ALLOCATION_FAILED",
            entity_type="FULFILMENT_REQUEST",
            entity_id=fulfilment_request_id,
            actor_id=actor_id,
            actor_role=actor_role,
            previous_state="ALLOCATION_PENDING",
            new_state="FAILED" if status_for_conflict == "FAILED" else "ALLOCATION_PENDING",
            details={"reason": result_code, **details},
            test_run_id=test_run_id,
        )
        raise ConflictError(
            message=f"Allocation failed: {result_code}",
            details={"reason": result_code, **details},
        )

    allocation_id = result_code  # ledger returns alloc_id as result_code on success

    # Link canonical graph relationships — MATCH the existing Part, never CREATE.
    session.run(
        """
        MATCH (r:FulfilmentRequest {id: $req_id})
        MATCH (a:Allocation {id: $alloc_id})
        MATCH (p:Part {part_number: $pn})
        MERGE (r)-[:HAS_ALLOCATION]->(a)
        MERGE (a)-[:ALLOCATES]->(p)
        """,
        {"req_id": fulfilment_request_id, "alloc_id": allocation_id, "pn": part_number},
    ).consume()

    # Synchronous confirmation: this flow confirms the reservation immediately
    # rather than deferring to a separate async confirmation step/expiry
    # window (ALLOCATION_ARCHITECTURE.md §6 leaves the exact mechanism to
    # Phase 3+ implementation choice).
    session.run(
        """
        MATCH (a:Allocation {id: $alloc_id})
        SET a.status = 'CONFIRMED', a.confirmedAt = datetime()
        """,
        {"alloc_id": allocation_id},
    ).consume()

    session.run(
        """
        MATCH (r:FulfilmentRequest {id: $req_id})
        SET r.status = 'ALLOCATED', r.updatedAt = datetime()
        """,
        {"req_id": fulfilment_request_id},
    ).consume()

    record_audit_event(
        session=session,
        action="ALLOCATION_CONFIRMED",
        entity_type="ALLOCATION",
        entity_id=allocation_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="RESERVED",
        new_state="CONFIRMED",
        details={
            "fulfilment_request_id": fulfilment_request_id,
            "part_number": part_number,
            "source_id": source_id,
            "quantity": quantity,
            "idempotency_key": idemp_key,
        },
        test_run_id=test_run_id,
    )

    return {
        "allocation_id": allocation_id,
        "fulfilment_request_id": fulfilment_request_id,
        "part_number": part_number,
        "part_id": part["part_id"],
        "source_id": source_id,
        "quantity": quantity,
        "status": "CONFIRMED",
        "expiry_at": details.get("expiry_at"),
    }


def get_allocation(session, fulfilment_request_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $req_id})-[:HAS_ALLOCATION]->(a:Allocation)
        RETURN a.id AS id, a.partNumber AS partNumber, a.sourceId AS sourceId,
               a.quantity AS quantity, a.status AS status,
               a.reservedAt AS reservedAt, a.confirmedAt AS confirmedAt,
               a.releasedAt AS releasedAt, a.idempotencyKey AS idempotencyKey
        ORDER BY a.reservedAt DESC
        LIMIT 1
        """,
        {"req_id": fulfilment_request_id},
    ).single()
    if not row:
        raise NotFoundError(f"No allocation found for fulfilment request '{fulfilment_request_id}'")
    data = dict(row)
    for key in ("reservedAt", "confirmedAt", "releasedAt"):
        if data.get(key) is not None:
            data[key] = str(data[key])
    return data


def release_allocation(
    session,
    fulfilment_request_id: str,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    alloc = get_allocation(session, fulfilment_request_id)

    if alloc["status"] not in ("RESERVED", "CONFIRMED"):
        raise ConflictError(
            f"Cannot release allocation in status '{alloc['status']}'. "
            "Must be RESERVED or CONFIRMED."
        )

    ledger_id = f"{alloc['partNumber']}:{alloc['sourceId']}"

    # Return quantity to the ledger using the same optimistic-lock pattern
    # (single conditional UPDATE gated on version) as the reservation path.
    row = session.run(
        "MATCH (l:InventoryLedger {id: $id}) RETURN l.version AS version",
        {"id": ledger_id},
    ).single()
    if row:
        version = row["version"]
        session.run(
            """
            MATCH (l:InventoryLedger {id: $id})
            WHERE l.version = $version
            SET l.totalAllocatedQty = l.totalAllocatedQty - $qty,
                l.version = $new_version,
                l.updatedAt = datetime()
            """,
            {"id": ledger_id, "version": version, "qty": alloc["quantity"], "new_version": version + 1},
        ).consume()

    session.run(
        """
        MATCH (a:Allocation {id: $id})
        SET a.status = 'RELEASED', a.releasedAt = datetime()
        """,
        {"id": alloc["id"]},
    ).consume()

    record_audit_event(
        session=session,
        action="ALLOCATION_RELEASED",
        entity_type="ALLOCATION",
        entity_id=alloc["id"],
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=alloc["status"],
        new_state="RELEASED",
        details={"fulfilment_request_id": fulfilment_request_id, "quantity": alloc["quantity"]},
        test_run_id=test_run_id,
    )

    return {"allocation_id": alloc["id"], "status": "RELEASED"}
