"""
backend/app/api/v1/shipment.py

Phase 7 Shipment & Tracking API router.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, Query

from app.db.neo4j.connection import get_neo4j_session
from app.idempotency.service import check_idempotency, save_idempotency_record
from app.modules.shipment.schemas import (

    PublicTrackingResponse,
    ShipmentCreateRequest,
    ShipmentEventCreate,
    ShipmentResponse,
)
from app.modules.shipment.service import (
    cancel_shipment,
    confirm_delivery,
    create_shipment,
    dispatch_shipment,
    get_shipment,
    get_shipment_by_order,
    get_tracking,
    record_tracking_event,
)

router = APIRouter(tags=["Shipments & Tracking"])


@router.post("/shipments", response_model=ShipmentResponse)
def create_new_shipment(
    dto: ShipmentCreateRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    endpoint = "/api/v1/shipments"
    payload = dto.model_dump()

    if x_idempotency_key:
        exists, status, cached = check_idempotency(session, endpoint, x_idempotency_key, payload)
        if exists:
            return cached

    result = create_shipment(
        session=session,
        order_id=dto.order_id,
        service_tier=dto.service_tier,
        test_run_id=test_run_id,
    )

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, payload, 200, result, test_run_id=test_run_id)

    return result


@router.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
def get_shipment_details(
    shipment_id: str,
    session=Depends(get_neo4j_session),
):
    return get_shipment(session, shipment_id)


@router.get("/shipments/by-order/{order_id}", response_model=ShipmentResponse)
def get_order_shipment(
    order_id: str,
    session=Depends(get_neo4j_session),
):
    return get_shipment_by_order(session, order_id)


@router.post("/shipments/{shipment_id}/dispatch", response_model=ShipmentResponse)
def dispatch_shipment_endpoint(
    shipment_id: str,
    location: Optional[str] = Query(None),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return dispatch_shipment(session, shipment_id, location=location, test_run_id=test_run_id)


@router.post("/shipments/{shipment_id}/events", response_model=ShipmentResponse)
def append_tracking_event(
    shipment_id: str,
    dto: ShipmentEventCreate,
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return record_tracking_event(
        session,
        shipment_id=shipment_id,
        event_type=dto.event_type,
        description=dto.description,
        location=dto.location,
        test_run_id=test_run_id,
    )


@router.post("/shipments/{shipment_id}/deliver", response_model=ShipmentResponse)
def confirm_shipment_delivery(
    shipment_id: str,
    location: Optional[str] = Query(None),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return confirm_delivery(session, shipment_id, location=location, test_run_id=test_run_id)


@router.post("/shipments/{shipment_id}/cancel", response_model=ShipmentResponse)
def cancel_shipment_endpoint(
    shipment_id: str,
    reason: str = Query("Cancelled by user or carrier exception"),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return cancel_shipment(session, shipment_id, reason=reason, test_run_id=test_run_id)


@router.get("/tracking/{tracking_number}", response_model=PublicTrackingResponse)
def public_tracking_lookup(
    tracking_number: str,
    session=Depends(get_neo4j_session),
):
    return get_tracking(session, tracking_number)
