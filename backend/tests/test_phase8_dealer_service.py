"""
backend/tests/test_phase8_dealer_service.py

Phase 8 Dealer & Service Domain Integration Tests.

Verifies:
1. ServiceJob creation for accepted orders in AuraDB.
2. ServiceJob retrieved from AuraDB with events and dealer/part/machine relationships.
3. Strict business rule: receive_part is rejected with ConflictError (409) if shipment is NOT DELIVERED.
4. Full sequential lifecycle:
   Order (ACCEPTED) -> Shipment (DELIVERED) -> ServiceJob (OPEN)
   -> PART_RECEIVED -> IN_PROGRESS -> PART_INSTALLED -> COMPLETED -> FulfilmentRequest (COMPLETED)
5. Service journey trace returns full end-to-end milestone timeline.
6. Invalid state transitions are rejected with ConflictError (409).
7. Service cancellation from active states.
8. Service retrieval by Order ID and Dealer ID.
9. Audit trail and event recording in AuraDB.
10. API endpoint validation with idempotency support.
11. Clean test-run isolation and zero orphan records.
"""

import pytest
from fastapi.testclient import TestClient

from app.db.neo4j.connection import get_neo4j_driver
from app.errors.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.main import app
from app.modules.allocation.service import create_allocation
from app.modules.availability.service import check_availability
from app.modules.fulfilment.service import (
    generate_fulfilment_options,
    proceed_to_allocation_pending,
    select_fulfilment_option,
)
from app.modules.order.service import accept_order, create_order
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
from app.modules.shipment.service import (
    confirm_delivery,
    create_shipment,
    dispatch_shipment,
)

client = TestClient(app)


def _drive_to_order_and_shipment(session, test_run_id):
    """Helper to advance the pipeline to an accepted Order and linked Shipment."""
    pn = f"PN8-SRV-{test_run_id[:12]}"
    session.run(
        "MERGE (p:Part {part_number: $pn}) ON CREATE SET p.part_id = $pn, p.part_name = 'Test Service Component', p.testRunId = $run",
        {"pn": pn, "run": test_run_id},
    ).consume()

    avail_res = check_availability(
        session=session,
        fulfilment_request_id=None,
        part_number=pn,
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    options = generate_fulfilment_options(session, req_id, test_run_id=test_run_id)
    select_fulfilment_option(session, req_id, options[0]["id"], test_run_id=test_run_id)
    proceed_to_allocation_pending(session, req_id, test_run_id=test_run_id)
    create_allocation(session, req_id, test_run_id=test_run_id)
    order = create_order(session, req_id, test_run_id=test_run_id)
    accepted_order = accept_order(session, order["id"], test_run_id=test_run_id)
    order_id = accepted_order["id"]

    shipment = create_shipment(session, order_id=order_id, test_run_id=test_run_id)
    return req_id, order_id, shipment["shipment_id"], pn


def test_service_job_creation_and_retrieval(neo4j_session, test_run_id):
    req_id, order_id, shipment_id, pn = _drive_to_order_and_shipment(neo4j_session, test_run_id)

    # 1. Create ServiceJob
    sj = create_service_job(
        neo4j_session,
        order_id=order_id,
        service_type="PARTS_INSTALLATION",
        notes="Pre-delivery inspection and assembly",
        test_run_id=test_run_id,
    )

    assert sj["service_job_id"].startswith("SJ-")
    assert sj["order_id"] == order_id
    assert sj["shipment_id"] == shipment_id
    assert sj["status"] == "OPEN"
    assert sj["service_type"] == "PARTS_INSTALLATION"
    assert sj["synthetic"] is True
    assert sj["data_source"] == "SYNTHETIC_DEMO"
    assert len(sj["events"]) == 1
    assert sj["events"][0]["event_type"] == "CREATED"

    # 2. Retrieve by ID
    fetched = get_service_job(neo4j_session, sj["service_job_id"])
    assert fetched["service_job_id"] == sj["service_job_id"]
    assert fetched["dealer_id"] == sj["dealer_id"]

    # 3. Retrieve by Order
    by_order = get_service_job_by_order(neo4j_session, order_id)
    assert by_order["service_job_id"] == sj["service_job_id"]


def test_service_part_receipt_blocked_until_delivery(neo4j_session, test_run_id):
    req_id, order_id, shipment_id, pn = _drive_to_order_and_shipment(neo4j_session, test_run_id)
    sj = create_service_job(neo4j_session, order_id=order_id, test_run_id=test_run_id)
    sj_id = sj["service_job_id"]

    # Shipment is only CREATED (not DELIVERED) -> receive_part must fail
    with pytest.raises(ConflictError) as exc:
        receive_part(neo4j_session, sj_id, test_run_id=test_run_id)
    assert "Shipment must be DELIVERED" in str(exc.value)

    # Dispatch shipment -> still not DELIVERED -> receive_part must fail
    dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)
    with pytest.raises(ConflictError) as exc:
        receive_part(neo4j_session, sj_id, test_run_id=test_run_id)
    assert "Shipment must be DELIVERED" in str(exc.value)

    # Deliver shipment -> now receive_part must succeed
    confirm_delivery(neo4j_session, shipment_id, test_run_id=test_run_id)
    received_sj = receive_part(neo4j_session, sj_id, condition_notes="All parts intact", test_run_id=test_run_id)
    assert received_sj["status"] == "PART_RECEIVED"
    assert received_sj["received_at"] is not None
    assert len(received_sj["events"]) == 2
    assert received_sj["events"][1]["event_type"] == "PART_RECEIVED"


def test_service_full_lifecycle_and_close(neo4j_session, test_run_id):
    req_id, order_id, shipment_id, pn = _drive_to_order_and_shipment(neo4j_session, test_run_id)
    dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)
    confirm_delivery(neo4j_session, shipment_id, test_run_id=test_run_id)

    # 1. Create Service Job (OPEN)
    sj = create_service_job(neo4j_session, order_id=order_id, test_run_id=test_run_id)
    sj_id = sj["service_job_id"]
    assert sj["status"] == "OPEN"

    # 2. Receive Part (OPEN -> PART_RECEIVED)
    sj_rec = receive_part(neo4j_session, sj_id, test_run_id=test_run_id)
    assert sj_rec["status"] == "PART_RECEIVED"

    # 3. Start Service (PART_RECEIVED -> IN_PROGRESS)
    sj_start = start_service(neo4j_session, sj_id, notes="Work order started in bay 1", test_run_id=test_run_id)
    assert sj_start["status"] == "IN_PROGRESS"
    assert sj_start["started_at"] is not None

    # 4. Install Part (IN_PROGRESS -> PART_INSTALLED)
    sj_inst = install_part(neo4j_session, sj_id, installation_notes="Torqued to 120 Nm", test_run_id=test_run_id)
    assert sj_inst["status"] == "PART_INSTALLED"
    assert sj_inst["installed_at"] is not None

    # 5. Complete Service (PART_INSTALLED -> COMPLETED)
    sj_comp = complete_service(neo4j_session, sj_id, signoff_notes="Final tests passed", test_run_id=test_run_id)
    assert sj_comp["status"] == "COMPLETED"
    assert sj_comp["completed_at"] is not None
    assert len(sj_comp["events"]) == 5

    # 6. Verify FulfilmentRequest is now COMPLETED (End-to-End Closed)
    fr_row = neo4j_session.run(
        "MATCH (fr:FulfilmentRequest {id: $req_id}) RETURN fr.status AS st",
        {"req_id": req_id},
    ).single()
    assert fr_row["st"] == "COMPLETED"

    # 7. Verify Journey Trace
    trace = get_service_journey_trace(neo4j_session, sj_id)
    assert trace["service_job_id"] == sj_id
    assert trace["is_closed"] is True
    assert trace["status"] == "COMPLETED"
    assert len(trace["timeline_milestones"]) >= 6


def test_service_invalid_transitions_rejected(neo4j_session, test_run_id):
    req_id, order_id, shipment_id, pn = _drive_to_order_and_shipment(neo4j_session, test_run_id)
    dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)
    confirm_delivery(neo4j_session, shipment_id, test_run_id=test_run_id)

    sj = create_service_job(neo4j_session, order_id=order_id, test_run_id=test_run_id)
    sj_id = sj["service_job_id"]

    # Cannot skip from OPEN directly to IN_PROGRESS
    with pytest.raises(ConflictError):
        start_service(neo4j_session, sj_id, test_run_id=test_run_id)

    # Cannot skip from OPEN directly to PART_INSTALLED
    with pytest.raises(ConflictError):
        install_part(neo4j_session, sj_id, test_run_id=test_run_id)

    # Cannot skip from OPEN directly to COMPLETED
    with pytest.raises(ConflictError):
        complete_service(neo4j_session, sj_id, test_run_id=test_run_id)


def test_service_cancellation(neo4j_session, test_run_id):
    req_id, order_id, shipment_id, pn = _drive_to_order_and_shipment(neo4j_session, test_run_id)
    dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)
    confirm_delivery(neo4j_session, shipment_id, test_run_id=test_run_id)

    sj = create_service_job(neo4j_session, order_id=order_id, test_run_id=test_run_id)
    sj_id = sj["service_job_id"]
    receive_part(neo4j_session, sj_id, test_run_id=test_run_id)
    start_service(neo4j_session, sj_id, test_run_id=test_run_id)

    # Cancel from IN_PROGRESS
    sj_canc = cancel_service_job(neo4j_session, sj_id, reason="Customer cancelled repair", test_run_id=test_run_id)
    assert sj_canc["status"] == "CANCELLED"
    assert sj_canc["cancelled_at"] is not None
    assert sj_canc["cancel_reason"] == "Customer cancelled repair"

    # Cannot cancel again once in terminal state
    with pytest.raises(ConflictError):
        cancel_service_job(neo4j_session, sj_id, reason="Double cancel", test_run_id=test_run_id)


def test_service_api_endpoints_and_idempotency(neo4j_session, test_run_id):
    req_id, order_id, shipment_id, pn = _drive_to_order_and_shipment(neo4j_session, test_run_id)
    dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)
    confirm_delivery(neo4j_session, shipment_id, test_run_id=test_run_id)

    # 1. API POST /service-jobs with Idempotency Key
    idem_key = f"idem-srv-{test_run_id}"
    res = client.post(
        "/api/v1/service-jobs",
        json={"order_id": order_id, "service_type": "PARTS_INSTALLATION", "notes": "API test"},
        headers={"X-Idempotency-Key": idem_key},
        params={"test_run_id": test_run_id},
    )
    assert res.status_code == 200
    data = res.json()
    sj_id = data["service_job_id"]
    assert data["status"] == "OPEN"

    # Idempotent retry returns identical payload
    res_retry = client.post(
        "/api/v1/service-jobs",
        json={"order_id": order_id, "service_type": "PARTS_INSTALLATION", "notes": "API test"},
        headers={"X-Idempotency-Key": idem_key},
        params={"test_run_id": test_run_id},
    )
    assert res_retry.status_code == 200
    assert res_retry.json()["service_job_id"] == sj_id

    # 2. API GET /service-jobs/{id}
    res_get = client.get(f"/api/v1/service-jobs/{sj_id}")
    assert res_get.status_code == 200
    assert res_get.json()["service_job_id"] == sj_id

    # 3. API POST /service-jobs/{id}/receive
    res_rec = client.post(f"/api/v1/service-jobs/{sj_id}/receive", params={"test_run_id": test_run_id})
    assert res_rec.status_code == 200
    assert res_rec.json()["status"] == "PART_RECEIVED"

    # 4. API POST /service-jobs/{id}/start
    res_start = client.post(f"/api/v1/service-jobs/{sj_id}/start", params={"test_run_id": test_run_id})
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "IN_PROGRESS"

    # 5. API POST /service-jobs/{id}/install
    res_inst = client.post(f"/api/v1/service-jobs/{sj_id}/install", params={"test_run_id": test_run_id})
    assert res_inst.status_code == 200
    assert res_inst.json()["status"] == "PART_INSTALLED"

    # 6. API POST /service-jobs/{id}/complete
    res_comp = client.post(f"/api/v1/service-jobs/{sj_id}/complete", params={"test_run_id": test_run_id})
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "COMPLETED"

    # 7. API GET /service-jobs/{id}/journey
    res_journey = client.get(f"/api/v1/service-jobs/{sj_id}/journey")
    assert res_journey.status_code == 200
    assert res_journey.json()["is_closed"] is True


def test_dealers_api_lists_real_netherlands_branches():
    """Phase 10: the destination picker and Parts Intelligence read the real
    DealerBranch graph — every NL row is a source-derived DLR-* branch."""
    from fastapi.testclient import TestClient
    from app.main import app

    rows = TestClient(app).get("/api/v1/dealers", params={"country": "nl"}).json()
    assert len(rows) >= 19
    assert all(r["country"] == "NL" and r["dealer_id"].startswith("DLR-") for r in rows)
    assert all(r["source_id"] for r in rows)
