"""
backend/app/api/v1/service_jobs.py

Phase 8 Dealer & Service API router.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query

from app.db.neo4j.connection import get_neo4j_session
from app.idempotency.service import check_idempotency, save_idempotency_record
from app.modules.service.schemas import (
    ServiceJobCreateRequest,
    ServiceJobResponse,
    ServiceJourneyTraceResponse,
)
from app.modules.service.service import (
    cancel_service_job,
    complete_service,
    create_service_job,
    get_service_job,
    get_service_job_by_order,
    get_service_jobs_by_dealer,
    get_service_journey_trace,
    install_part,
    receive_part,
    start_service,
)

router = APIRouter(tags=["Dealer & Service"])


@router.post("/service-jobs", response_model=ServiceJobResponse)
def create_new_service_job(
    dto: ServiceJobCreateRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    endpoint = "/api/v1/service-jobs"
    payload = dto.model_dump()

    if x_idempotency_key:
        exists, status, cached = check_idempotency(session, endpoint, x_idempotency_key, payload)
        if exists:
            return cached

    result = create_service_job(
        session=session,
        order_id=dto.order_id,
        service_type=dto.service_type,
        technician_role=dto.technician_role,
        notes=dto.notes,
        test_run_id=test_run_id,
    )

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, payload, 200, result, test_run_id=test_run_id)

    return result


@router.get("/service-jobs/{service_job_id}", response_model=ServiceJobResponse)
def get_service_job_details(
    service_job_id: str,
    session=Depends(get_neo4j_session),
):
    return get_service_job(session, service_job_id)


@router.get("/service-jobs/by-order/{order_id}", response_model=ServiceJobResponse)
def get_order_service_job(
    order_id: str,
    session=Depends(get_neo4j_session),
):
    return get_service_job_by_order(session, order_id)


@router.get("/service-jobs/by-dealer/{dealer_id}", response_model=List[ServiceJobResponse])
def get_dealer_service_jobs(
    dealer_id: str,
    limit: int = Query(50, ge=1, le=200),
    session=Depends(get_neo4j_session),
):
    return get_service_jobs_by_dealer(session, dealer_id, limit=limit)


@router.get("/service-jobs/{service_job_id}/journey", response_model=ServiceJourneyTraceResponse)
def get_service_journey_trace_endpoint(
    service_job_id: str,
    session=Depends(get_neo4j_session),
):
    return get_service_journey_trace(session, service_job_id)


@router.post("/service-jobs/{service_job_id}/receive", response_model=ServiceJobResponse)
def confirm_dealer_part_receipt(
    service_job_id: str,
    condition_notes: Optional[str] = Query(None),
    technician_role: Optional[str] = Query("DEALER_PARTS_INSPECTOR"),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return receive_part(
        session=session,
        service_job_id=service_job_id,
        condition_notes=condition_notes,
        technician_role=technician_role,
        test_run_id=test_run_id,
    )


@router.post("/service-jobs/{service_job_id}/start", response_model=ServiceJobResponse)
def start_technician_service(
    service_job_id: str,
    notes: Optional[str] = Query(None),
    technician_role: Optional[str] = Query("CERTIFIED_SERVICE_TECHNICIAN"),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return start_service(
        session=session,
        service_job_id=service_job_id,
        notes=notes,
        technician_role=technician_role,
        test_run_id=test_run_id,
    )


@router.post("/service-jobs/{service_job_id}/install", response_model=ServiceJobResponse)
def confirm_part_installed(
    service_job_id: str,
    installation_notes: Optional[str] = Query(None),
    technician_role: Optional[str] = Query("CERTIFIED_SERVICE_TECHNICIAN"),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return install_part(
        session=session,
        service_job_id=service_job_id,
        installation_notes=installation_notes,
        technician_role=technician_role,
        test_run_id=test_run_id,
    )


@router.post("/service-jobs/{service_job_id}/complete", response_model=ServiceJobResponse)
def complete_service_job_endpoint(
    service_job_id: str,
    signoff_notes: Optional[str] = Query(None),
    technician_role: Optional[str] = Query("WORKSHOP_MANAGER"),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return complete_service(
        session=session,
        service_job_id=service_job_id,
        signoff_notes=signoff_notes,
        technician_role=technician_role,
        test_run_id=test_run_id,
    )


@router.post("/service-jobs/{service_job_id}/cancel", response_model=ServiceJobResponse)
def cancel_service_job_endpoint(
    service_job_id: str,
    reason: str = Query("Service cancelled by dealer/customer request"),
    test_run_id: Optional[str] = Query(None),
    session=Depends(get_neo4j_session),
):
    return cancel_service_job(
        session=session,
        service_job_id=service_job_id,
        reason=reason,
        test_run_id=test_run_id,
    )
