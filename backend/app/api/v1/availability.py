from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.db.neo4j.connection import get_neo4j_session
from app.errors.exceptions import NotFoundError, ValidationError
from app.modules.availability.service import check_availability
from app.middleware.auth import get_current_user, AuthUser
from app.idempotency.service import check_idempotency, save_idempotency_record

router = APIRouter(prefix="/fulfilment-requests", tags=["Availability"])


# See the matching note in app/api/v1/fulfilment.py — this DTO had the same
# camelCase-vs-snake_case gap against components/AvailabilityChecker.tsx.
class AvailabilityCheckDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    part_number: str
    quantity: int
    destination_branch_id: str = "DEALER-BRANCH-NL-01"
    customer_id: str = "CUST-DEFAULT"
    machine_context: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


@router.post("/{request_id}/availability")
def trigger_availability_check(
    request_id: str,
    dto: AvailabilityCheckDTO,
    x_idempotency_key: Optional[str] = Header(None),
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    endpoint = f"/api/v1/fulfilment-requests/{request_id}/availability"
    if x_idempotency_key:
        exists, status, cached = check_idempotency(session, endpoint, x_idempotency_key, dto.model_dump())
        if exists:
            return cached

    result = check_availability(
        session=session,
        fulfilment_request_id=request_id if request_id != "new" else None,
        part_number=dto.part_number,
        quantity=dto.quantity,
        destination_branch_id=dto.destination_branch_id,
        customer_id=dto.customer_id,
        machine_context=dto.machine_context,
        options=dto.options,
        test_run_id=x_test_run_id,
    )

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, dto.model_dump(), 200, result)

    return result


@router.get("/{request_id}/availability")
def get_availability_results(
    request_id: str,
    session=Depends(get_neo4j_session),
):
    req_result = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        RETURN r.id, r.partNumber, r.quantity, r.status
        """,
        {"id": request_id},
    ).single()
    if not req_result:
        raise NotFoundError(f"Fulfilment request '{request_id}' not found")

    f_id = req_result["r.id"]
    part_number = req_result["r.partNumber"]
    quantity = req_result["r.quantity"]
    status = req_result["r.status"]

    cache_records = session.run(
        """
        MATCH (c:InventoryCache {partNumber: $part_number})
        RETURN c.sourceId, c.locationId, c.onHandQty, c.reservedQty,
               c.allocatedQty, c.availableQty, c.status, c.inventoryTimestamp
        ORDER BY c.inventoryTimestamp DESC
        """,
        {"part_number": part_number},
    ).data()

    sources = []
    total_avail = 0
    for r in cache_records:
        sources.append({
            "source_id": r["c.sourceId"],
            "location_id": r["c.locationId"],
            "on_hand_qty": r["c.onHandQty"],
            "reserved_qty": r["c.reservedQty"],
            "allocated_qty": r["c.allocatedQty"],
            "available_qty": r["c.availableQty"],
            "status": r["c.status"],
            "inventory_timestamp": str(r["c.inventoryTimestamp"]),
        })
        if r["c.status"] != "UNKNOWN":
            total_avail += r["c.availableQty"]

    return {
        "fulfilment_request_id": f_id,
        "part_number": part_number,
        "requested_qty": quantity,
        "status": status,
        "total_available_qty": total_avail,
        "sources": sources,
    }
