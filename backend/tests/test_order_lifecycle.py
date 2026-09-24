"""
Customer order placement -> Orders list -> business lifecycle, with every step checked directly in Neo4j (a separate session/driver read,
not the API response), so the data is proven to be in the database and not held by the app.
"""
import re

from fastapi.testclient import TestClient

from app.db.neo4j.connection import get_neo4j_driver
from app.main import app

client = TestClient(app)
API = "/api/v1"
PART = "4663907"   # PT-001, a real orderable battery


def _h(run_id):
    return {"x-test-run-id": run_id, "x-test-user-id": "u", "x-test-role": "CUSTOMER"}


def _db(cypher, **params):
    """Independent read straight from the database."""
    with get_neo4j_driver().session() as s:
        return s.run(cypher, **params).data()


def _place(run_id, dealer="DLR-045"):
    H = _h(run_id)
    rid = client.post(f"{API}/fulfilment-requests", json={"part_number": PART, "quantity": 2, "destination_branch_id": dealer,
                                                          "requester_name": "Lifecycle Tester", "requester_email": "tester@example.eu"}, headers=H).json()["id"]
    client.post(f"{API}/fulfilment-requests/{rid}/availability", json={"part_number": PART, "quantity": 2, "destination_branch_id": dealer}, headers=H)
    opt = client.post(f"{API}/fulfilment-requests/{rid}/options", headers=H).json()["options"][0]["id"]
    assert client.post(f"{API}/fulfilment-requests/{rid}/select-option", json={"option_id": opt}, headers={**H, "x-idempotency-key": f"k-{run_id}"}).status_code == 200
    assert client.post(f"{API}/fulfilment-requests/{rid}/proceed-to-allocation", headers=H).status_code == 200
    r = client.post(f"{API}/fulfilment-requests/{rid}/place-order", headers=H,
                    json={"customer_name": "Lifecycle Tester", "customer_email": "tester@example.eu", "customer_phone": "+31 6 1234 5678", "customer_company": "Test BV"})
    return rid, opt, r


def test_placing_an_order_persists_all_customer_and_order_data_in_the_database(test_run_id):
    rid, opt, r = _place(test_run_id)
    assert r.status_code == 200, r.text
    o = r.json()
    assert re.fullmatch(r"HCME-ORD-\d{6}", o["order_id"])
    assert o["status"] == "CREATED"

    row = _db("MATCH (o:Order {id: $id}) RETURN o", id=o["order_id"])[0]["o"]      # straight from Aura
    assert row["customerName"] == "Lifecycle Tester" and row["customerEmail"] == "tester@example.eu"
    assert row["customerPhone"] == "+31 6 1234 5678"
    assert row["shipToDealerId"] == "DLR-045" and row["shipToDealerName"]
    assert row["partNumber"] == PART and row["quantity"] == 2
    assert row["fulfilmentOptionId"] == opt and row["fulfilmentMode"]
    assert row["placedAt"] is not None and row["status"] == "CREATED"
    assert row["data_source"] == "SYNTHETIC_DEMO"          # demo label preserved

    # placing again for the same request returns the same order (no duplicate)
    again = client.post(f"{API}/fulfilment-requests/{rid}/place-order", headers=_h(test_run_id),
                        json={"customer_name": "x", "customer_email": "y@z.eu"})
    assert again.json()["order_id"] == o["order_id"]
    assert len(_db("MATCH (:FulfilmentRequest {id: $id})-[:HAS_ORDER]->(o:Order) RETURN o.id AS id", id=rid)) == 1


def test_order_ids_are_unique_and_increasing(test_run_id):
    _, _, a = _place(test_run_id)
    _, _, b = _place(test_run_id + "b")
    na, nb = int(a.json()["order_id"][-6:]), int(b.json()["order_id"][-6:])
    assert nb > na


def test_orders_screen_reads_the_list_from_the_database(test_run_id):
    _, _, r = _place(test_run_id)
    oid = r.json()["order_id"]
    rows = client.get(f"{API}/orders").json()["orders"]
    mine = next(x for x in rows if x["order_id"] == oid)
    assert mine["customer_name"] == "Lifecycle Tester" and mine["status"] == "CREATED"
    assert mine["parts"][0]["part_number"] == PART and mine["dealer_name"] and mine["placed_at"]


def test_full_business_lifecycle_is_persisted_step_by_step(test_run_id):
    rid, _, r = _place(test_run_id)
    oid = r.json()["order_id"]
    H = _h(test_run_id)

    def ops():
        return client.get(f"{API}/orders/{oid}/operations").json()

    def status_in_db():
        return _db("MATCH (o:Order {id: $id}) RETURN o.status AS s", id=oid)[0]["s"]

    assert [s["state"] for s in ops()["steps"]][:2] == ["done", "current"]           # order placed, allocation is next
    assert ops()["next_action"]["key"] == "allocate"

    # out-of-order actions are refused
    assert client.post(f"{API}/orders/{oid}/ops/create_shipment", headers=H).status_code == 409

    expected = [("allocate", "CREATED"), ("fulfil", "ACCEPTED"), ("create_shipment", "ACCEPTED"), ("dispatch", "ACCEPTED"),
                ("in_transit", "ACCEPTED"), ("deliver", "FULFILLED"), ("create_service_job", "FULFILLED"), ("receive", "FULFILLED"), ("start", "FULFILLED"),
                ("install", "FULFILLED"), ("complete", "CLOSED")]
    for action, order_status in expected:
        assert ops()["next_action"]["key"] == action
        res = client.post(f"{API}/orders/{oid}/ops/{action}", headers=H)
        assert res.status_code == 200, (action, res.text)
        if order_status:
            assert status_in_db() == order_status, action

    # each persisted node, read directly from the database
    assert _db("MATCH (:Order {id: $id})-[:BASED_ON_ALLOCATION]->(a:Allocation) RETURN a.status AS s", id=oid)[0]["s"] == "CONSUMED"
    assert _db("MATCH (:Order {id: $id})-[:HAS_SHIPMENT]->(sh:Shipment) RETURN sh.status AS s", id=oid)[0]["s"] == "DELIVERED"
    ev = _db("MATCH (:Order {id: $id})-[:HAS_SHIPMENT]->(:Shipment)-[:HAS_EVENT]->(e:ShipmentEvent) RETURN e.event_type AS t", id=oid)
    assert {"DISPATCHED", "IN_TRANSIT", "DELIVERED"} <= {e["t"] for e in ev}
    assert _db("MATCH (:Order {id: $id})-[:HAS_SERVICE_JOB]->(j:ServiceJob) RETURN j.status AS s", id=oid)[0]["s"] == "COMPLETED"
    assert status_in_db() == "CLOSED"

    final = ops()                                        # the completed lifecycle is retrievable
    assert final["completed"] is True and final["next_action"] is None
    assert all(s["state"] == "done" for s in final["steps"])
    assert final["order"]["order_id"] == oid


def test_an_order_can_be_cancelled_before_dispatch_and_stock_is_released(test_run_id):
    _, _, r = _place(test_run_id)
    oid = r.json()["order_id"]
    H = _h(test_run_id)
    assert client.post(f"{API}/orders/{oid}/ops/allocate", headers=H).status_code == 200
    assert client.get(f"{API}/orders/{oid}/operations").json()["can_cancel"] is True
    res = client.post(f"{API}/orders/{oid}/ops/cancel", headers=H)
    assert res.status_code == 200 and res.json()["cancelled"] is True and res.json()["next_action"] is None
    assert _db("MATCH (o:Order {id: $id}) RETURN o.status AS s", id=oid)[0]["s"] == "CANCELLED"
    assert _db("MATCH (:Order {id: $id})-[:BASED_ON_ALLOCATION]->(a:Allocation) RETURN a.status AS s", id=oid)[0]["s"] == "RELEASED"
    assert client.post(f"{API}/orders/{oid}/ops/allocate", headers=H).status_code == 409      # nothing more can happen to it


def test_a_dispatched_order_cannot_be_cancelled(test_run_id):
    _, _, r = _place(test_run_id)
    oid = r.json()["order_id"]
    H = _h(test_run_id)
    for a in ("allocate", "fulfil", "create_shipment", "dispatch"):
        assert client.post(f"{API}/orders/{oid}/ops/{a}", headers=H).status_code == 200
    assert client.get(f"{API}/orders/{oid}/operations").json()["can_cancel"] is False
    assert client.post(f"{API}/orders/{oid}/ops/cancel", headers=H).status_code == 409
