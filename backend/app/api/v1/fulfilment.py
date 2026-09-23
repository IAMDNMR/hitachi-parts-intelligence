import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.db.neo4j.connection import get_neo4j_session
from app.errors.exceptions import ValidationError, NotFoundError
from app.middleware.auth import get_current_user, AuthUser
from app.idempotency.service import check_idempotency, save_idempotency_record
from app.modules.fulfilment.service import (
    generate_fulfilment_options,
    get_fulfilment_options,
    select_fulfilment_option,
    proceed_to_allocation_pending,
)

router = APIRouter(prefix="/fulfilment-requests", tags=["Fulfilment"])


# NOTE (Phase 6 fix, found during live browser E2E verification): the
# existing frontend (components/AvailabilityChecker.tsx,
# FulfilmentOptionSelector.tsx — both Phase 5, unmodified in this change)
# has always sent camelCase JSON bodies (partNumber, destinationBranchId,
# optionId, ...), but these DTOs only declared snake_case fields, with no
# alias — so POST /api/v1/fulfilment-requests always 422'd for real browser
# traffic. No existing test caught this because the backend test suite
# calls the service layer directly, never this route with a JSON body
# (verified via `grep -rn "client.post(\"/api/v1/fulfilment-requests\""
# tests/` — zero matches). Adding `populate_by_name` + a camelCase alias
# generator accepts BOTH spellings — purely additive, does not change any
# existing snake_case behavior or field default.
class _CamelAliasModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateFulfilmentRequestDTO(_CamelAliasModel):
    part_number: str
    quantity: int
    customer_id: str = "CUST-DEFAULT"
    # Phase 10B: capture WHO is requesting the part, persisted in Neo4j (see
    # docs/business-process/ACTORS_AND_RESPONSIBILITIES.md — Select Part is
    # owned by the Customer). Optional so existing callers/tests that only
    # send customer_id keep working; when requester_email is given it
    # becomes the real, stable customer_id instead of the CUST-DEFAULT
    # placeholder.
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    destination_branch_id: str = "DEALER-BRANCH-NL-01"
    machine_context: Optional[str] = None
    required_by_date: Optional[str] = None


class SelectOptionDTO(_CamelAliasModel):
    option_id: str


@router.post("")
def create_fulfilment_request(
    dto: CreateFulfilmentRequestDTO,
    x_idempotency_key: Optional[str] = Header(None),
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    if dto.quantity <= 0:
        raise ValidationError("Quantity must be greater than zero")

    endpoint = "/api/v1/fulfilment-requests"
    if x_idempotency_key:
        exists, status, cached_resp = check_idempotency(session, endpoint, x_idempotency_key, dto.model_dump())
        if exists:
            return cached_resp

    req_id = f"freq-{uuid.uuid4()}"
    # A real requester identity (email) becomes the customer_id, replacing
    # the CUST-DEFAULT placeholder; the identity itself is persisted as a
    # Customer node, reusing the existing (:Customer) model rather than
    # inventing a new one (see docs/business-process/ACTORS_AND_RESPONSIBILITIES.md).
    customer_id = (dto.requester_email or dto.customer_id or "CUST-DEFAULT").strip()
    session.run(
        """
        CREATE (r:FulfilmentRequest {
            id:                  $id,
            partNumber:          $part_number,
            quantity:            $quantity,
            machineContext:      $machine_context,
            customerId:          $customer_id,
            destinationBranchId: $destination_branch_id,
            status:              'REQUESTED',
            createdAt:           datetime(),
            updatedAt:           datetime(),
            testRunId:           $test_run_id
        })
        WITH r
        CALL (r) {
            WITH r WHERE $requester_email IS NOT NULL AND $requester_email <> ''
            MERGE (c:Customer {email: $requester_email})
            ON CREATE SET c.name = $requester_name, c.createdAt = datetime(), c.testRunId = $test_run_id
            ON MATCH SET c.name = coalesce($requester_name, c.name)
            MERGE (c)-[:REQUESTED]->(r)
        }
        """,
        {
            "id": req_id,
            "part_number": dto.part_number,
            "quantity": dto.quantity,
            "machine_context": dto.machine_context,
            "customer_id": customer_id,
            "destination_branch_id": dto.destination_branch_id,
            "test_run_id": x_test_run_id,
            "requester_email": (dto.requester_email or "").strip() or None,
            "requester_name": dto.requester_name,
        },
    ).consume()

    response_body = {
        "id": req_id,
        "part_number": dto.part_number,
        "quantity": dto.quantity,
        "customer_id": customer_id,
        "destination_branch_id": dto.destination_branch_id,
        "machine_context": dto.machine_context,
        "status": "REQUESTED",
    }

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, dto.model_dump(), 201, response_body)

    return response_body


@router.get("/{request_id}")
def get_fulfilment_request(
    request_id: str,
    session=Depends(get_neo4j_session),
):
    result = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        RETURN r.id, r.partNumber, r.quantity, r.destinationBranchId,
               r.customerId, r.machineContext, r.status, r.selectedOptionId,
               r.createdAt, r.updatedAt
        """,
        {"id": request_id},
    ).single()
    if not result:
        raise NotFoundError(f"Fulfilment request '{request_id}' not found")

    return {
        "id": result["r.id"],
        "part_number": result["r.partNumber"],
        "quantity": result["r.quantity"],
        "destination_branch_id": result["r.destinationBranchId"],
        "customer_id": result["r.customerId"],
        "machine_context": result["r.machineContext"],
        "status": result["r.status"],
        "selected_option_id": result["r.selectedOptionId"],
        "created_at": str(result["r.createdAt"]),
        "updated_at": str(result["r.updatedAt"]),
    }


@router.post("/{request_id}/options")
def compute_fulfilment_options(
    request_id: str,
    x_idempotency_key: Optional[str] = Header(None),
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    endpoint = f"/api/v1/fulfilment-requests/{request_id}/options"
    if x_idempotency_key:
        exists, status, cached = check_idempotency(session, endpoint, x_idempotency_key, {})
        if exists:
            return cached

    options = generate_fulfilment_options(session, request_id, test_run_id=x_test_run_id)
    response_body = {
        "fulfilment_request_id": request_id,
        "options": options,
        "total_options": len(options),
    }

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, {}, 200, response_body)

    return response_body


@router.get("/{request_id}/options")
def retrieve_fulfilment_options(
    request_id: str,
    session=Depends(get_neo4j_session),
):
    options = get_fulfilment_options(session, request_id)
    return {
        "fulfilment_request_id": request_id,
        "options": options,
        "total_options": len(options),
    }


@router.post("/{request_id}/select-option")
def select_option(
    request_id: str,
    dto: SelectOptionDTO,
    x_idempotency_key: Optional[str] = Header(None),
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    endpoint = f"/api/v1/fulfilment-requests/{request_id}/select-option"
    if x_idempotency_key:
        exists, status, cached = check_idempotency(session, endpoint, x_idempotency_key, dto.model_dump())
        if exists:
            return cached

    result = select_fulfilment_option(
        session=session,
        fulfilment_request_id=request_id,
        option_id=dto.option_id,
        actor_id=user.user_id,
        actor_role=user.role,
        test_run_id=x_test_run_id,
    )

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, dto.model_dump(), 200, result)

    return result


@router.post("/{request_id}/proceed-to-allocation")
def advance_to_allocation(
    request_id: str,
    x_idempotency_key: Optional[str] = Header(None),
    x_test_run_id: Optional[str] = Header(None, alias="x-test-run-id"),
    session=Depends(get_neo4j_session),
    user: AuthUser = Depends(get_current_user),
):
    endpoint = f"/api/v1/fulfilment-requests/{request_id}/proceed-to-allocation"
    if x_idempotency_key:
        exists, status, cached = check_idempotency(session, endpoint, x_idempotency_key, {})
        if exists:
            return cached

    result = proceed_to_allocation_pending(
        session=session,
        fulfilment_request_id=request_id,
        actor_id=user.user_id,
        actor_role=user.role,
        test_run_id=x_test_run_id,
    )

    if x_idempotency_key:
        save_idempotency_record(session, endpoint, x_idempotency_key, {}, 200, result)

    return result
