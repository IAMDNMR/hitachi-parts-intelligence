from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.db.neo4j.connection import get_neo4j_session
from app.idempotency.service import check_idempotency, save_idempotency_record
from app.middleware.auth import get_current_user, AuthUser
from app.modules.order.service import create_order, get_order

fulfilment_router = APIRouter(prefix="/fulfilment-requests", tags=["Order"])
order_router = APIRouter(prefix="/orders", tags=["Order"])


@fulfilment_router.post("/{request_id}/order")
def place_order(
    request_id: str,
    x_idempotency_key: Optional[str] = Header(None),
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    endpoint = f"/api/v1/fulfilment-requests/{request_id}/order"
    payload = {"request_id": request_id}

    if x_idempotency_key:
        exists, status, cached = check_idempotency(session, endpoint, x_idempotency_key, payload)
        if exists:
            return cached

    result = create_order(
        session=session,
        fulfilment_request_id=request_id,
        actor_id=user.user_id,
        actor_role=user.role,
        test_run_id=x_test_run_id,
    )

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, payload, 200, result)

    return result


@order_router.get("/{order_id}")
def read_order(
    order_id: str,
    session=Depends(get_neo4j_session),
):
    return get_order(session, order_id)


@order_router.post("/{order_id}/accept")
def accept_existing_order(
    order_id: str,
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    from app.modules.order.service import accept_order
    return accept_order(session, order_id, actor_id=user.user_id, actor_role=user.role, test_run_id=x_test_run_id)


@order_router.post("/{order_id}/cancel")
def cancel_existing_order(
    order_id: str,
    reason: str = "Order cancelled",
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    from app.modules.order.service import cancel_order
    return cancel_order(session, order_id, reason=reason, actor_id=user.user_id, actor_role=user.role, test_run_id=x_test_run_id)

