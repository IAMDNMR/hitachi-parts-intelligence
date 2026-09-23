from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.db.neo4j.connection import get_neo4j_session
from app.idempotency.service import check_idempotency, save_idempotency_record
from app.middleware.auth import get_current_user, AuthUser
from app.modules.allocation.service import create_allocation, get_allocation, release_allocation

router = APIRouter(prefix="/fulfilment-requests", tags=["Allocation"])


@router.post("/{request_id}/allocation")
def allocate(
    request_id: str,
    x_idempotency_key: Optional[str] = Header(None),
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    endpoint = f"/api/v1/fulfilment-requests/{request_id}/allocation"
    payload = {"request_id": request_id}

    if x_idempotency_key:
        exists, status, cached = check_idempotency(session, endpoint, x_idempotency_key, payload)
        if exists:
            return cached

    result = create_allocation(
        session=session,
        fulfilment_request_id=request_id,
        actor_id=user.user_id,
        actor_role=user.role,
        idempotency_key=x_idempotency_key,
        test_run_id=x_test_run_id,
    )

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, payload, 200, result)

    return result


@router.get("/{request_id}/allocation")
def read_allocation(
    request_id: str,
    session=Depends(get_neo4j_session),
):
    return get_allocation(session, request_id)


@router.post("/{request_id}/allocation/release")
def release(
    request_id: str,
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    return release_allocation(
        session=session,
        fulfilment_request_id=request_id,
        actor_id=user.user_id,
        actor_role=user.role,
        test_run_id=x_test_run_id,
    )
