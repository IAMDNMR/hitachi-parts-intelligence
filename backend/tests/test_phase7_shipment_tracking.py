"""
backend/tests/test_phase7_shipment_tracking.py

Phase 7 Shipment & Tracking domain and API integration tests.

Verifies:
- Order (ACCEPTED) -> Shipment created -> DISPATCHED -> IN_TRANSIT -> DELIVERED
- Exception and Cancellation state transitions
- Invalid transitions are rejected with ConflictError (409)
- Audit trail recording for all transitions
- Provider abstraction and test provider response contracts
- Public tracking lookup
- Zero regression on existing Phase 6 allocation/order behavior.
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
from app.modules.order.service import accept_order, cancel_order, create_order, get_order
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

client = TestClient(app)


def _drive_to_order_accepted(session, test_run_id):
    pn = f"PN7-SHIP-{test_run_id}-{session.run('RETURN randomUUID() AS u').single()['u'][:8]}"
    session.run(
        "MERGE (p:Part {part_number: $pn}) ON CREATE SET p.part_id = $pn, p.testRunId = $run",
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
    return accepted_order["id"], pn


def test_shipment_full_lifecycle(neo4j_session, test_run_id):
    order_id, _ = _drive_to_order_accepted(neo4j_session, test_run_id)

    # 1. Create Shipment
    sh = create_shipment(neo4j_session, order_id=order_id, test_run_id=test_run_id)
    assert sh["status"] == "CREATED"
    assert sh["carrier"] == "Demo European Logistics Partner"
    assert sh["tracking_number"] is not None
    assert sh["integration_status"] == "NOT_CONNECTED"
    assert sh["synthetic"] is True
    assert len(sh["events"]) == 1
    assert sh["events"][0]["event_type"] == "CREATED"

    shipment_id = sh["shipment_id"]
    tracking_num = sh["tracking_number"]

    # 2. Dispatch Shipment
    sh_disp = dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)
    assert sh_disp["status"] == "DISPATCHED"
    assert sh_disp["shipped_at"] is not None
    assert len(sh_disp["events"]) == 2
    assert sh_disp["events"][1]["event_type"] == "DISPATCHED"

    # 3. Transit tracking event
    sh_transit = record_tracking_event(
        neo4j_session,
        shipment_id=shipment_id,
        event_type="IN_TRANSIT",
        description="Shipment arrived at distribution hub",
        location="Eindhoven Logistics Hub, NL",
        test_run_id=test_run_id,
    )
    assert sh_transit["status"] == "IN_TRANSIT"
    assert len(sh_transit["events"]) == 3

    # 4. Confirm Delivery
    sh_deliv = confirm_delivery(neo4j_session, shipment_id, location="Dealer Facility", test_run_id=test_run_id)
    assert sh_deliv["status"] == "DELIVERED"
    assert sh_deliv["delivered_at"] is not None
    assert len(sh_deliv["events"]) == 4

    # 5. Verify Public Tracking Query
    track_res = get_tracking(neo4j_session, tracking_num)
    assert track_res["status"] == "DELIVERED"
    assert track_res["tracking_number"] == tracking_num
    assert len(track_res["events"]) == 4


def test_shipment_invalid_transitions_rejected(neo4j_session, test_run_id):
    order_id, _ = _drive_to_order_accepted(neo4j_session, test_run_id)
    sh = create_shipment(neo4j_session, order_id=order_id, test_run_id=test_run_id)
    shipment_id = sh["shipment_id"]

    # Cannot dispatch twice
    dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)
    with pytest.raises(ConflictError):
        dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)

    # Deliver shipment
    confirm_delivery(neo4j_session, shipment_id, test_run_id=test_run_id)

    # Cannot deliver again after delivered
    with pytest.raises(ConflictError):
        confirm_delivery(neo4j_session, shipment_id, test_run_id=test_run_id)

    # Cannot cancel after delivered
    with pytest.raises(ConflictError):
        cancel_shipment(neo4j_session, shipment_id, reason="Too late", test_run_id=test_run_id)


def test_shipment_exception_and_cancellation(neo4j_session, test_run_id):
    order_id, _ = _drive_to_order_accepted(neo4j_session, test_run_id)
    sh = create_shipment(neo4j_session, order_id=order_id, test_run_id=test_run_id)
    shipment_id = sh["shipment_id"]
    dispatch_shipment(neo4j_session, shipment_id, test_run_id=test_run_id)

    # Record exception
    sh_ex = record_tracking_event(
        neo4j_session,
        shipment_id=shipment_id,
        event_type="EXCEPTION",
        description="Severe weather delay in transit",
        location="Antwerp Hub",
        test_run_id=test_run_id,
    )
    assert sh_ex["status"] == "EXCEPTION"

    # Cancel unrecoverable shipment
    sh_cancel = cancel_shipment(neo4j_session, shipment_id, reason="Lost in transit", test_run_id=test_run_id)
    assert sh_cancel["status"] == "CANCELLED"


def test_shipment_api_endpoints(neo4j_session, test_run_id):
    order_id, _ = _drive_to_order_accepted(neo4j_session, test_run_id)

    # API POST /shipments
    res = client.post(
        "/api/v1/shipments",
        json={"order_id": order_id, "service_tier": "EXPEDITED"},
        headers={"X-Idempotency-Key": f"idem-ship-{test_run_id}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["order_id"] == order_id
    assert data["status"] == "CREATED"
    shipment_id = data["shipment_id"]
    tracking_num = data["tracking_number"]

    # API GET /shipments/{id}
    res_get = client.get(f"/api/v1/shipments/{shipment_id}")
    assert res_get.status_code == 200
    assert res_get.json()["shipment_id"] == shipment_id

    # API GET /shipments/by-order/{order_id}
    res_order = client.get(f"/api/v1/shipments/by-order/{order_id}")
    assert res_order.status_code == 200
    assert res_order.json()["shipment_id"] == shipment_id

    # API POST /shipments/{id}/dispatch
    res_disp = client.post(f"/api/v1/shipments/{shipment_id}/dispatch")
    assert res_disp.status_code == 200
    assert res_disp.json()["status"] == "DISPATCHED"

    # API GET /tracking/{number}
    res_track = client.get(f"/api/v1/tracking/{tracking_num}")
    assert res_track.status_code == 200
    assert res_track.json()["status"] == "DISPATCHED"
