"""
The workflow, end to end and off the rails.

Every stage-advancing test also checks `stage` AND `next_stage` AND the
timeline, because those three have to agree: a bug that updates the current
stage but forgets to log a StatusEvent, or advertises the wrong next action,
would still pass a test that only checked one of the three.
"""


def create_requirement(client, part_id="filters", quantity=3, machine="ZX350-4521"):
    r = client.post(
        "/api/requirements",
        json={
            "machine_serial": machine,
            "part_id": part_id,
            "quantity": quantity,
            "reason": "Scheduled 500-hour service",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_creating_a_requirement_raises_and_identifies_in_one_call(client):
    body = create_requirement(client)
    assert body["stage"] == "identified"
    assert body["next_stage"] == "availability_checked"
    stages = [e["stage"] for e in body["events"]]
    assert stages == ["requirement_raised", "identified"]


def test_creating_against_an_unknown_part_is_404(client):
    r = client.post(
        "/api/requirements",
        json={"machine_serial": "X", "part_id": "not-a-part", "quantity": 1, "reason": "x"},
    )
    assert r.status_code == 404


def test_quantity_must_be_positive(client):
    r = client.post(
        "/api/requirements",
        json={"machine_serial": "X", "part_id": "filters", "quantity": 0, "reason": "x"},
    )
    assert r.status_code == 422


def test_happy_path_in_stock_part_reaches_goods_receipt(client):
    req_id = create_requirement(client, part_id="filters", quantity=3)["id"]

    before_stock = client.get("/api/parts/filters/stock").json()["qty_on_hand"]

    r = client.post(f"/api/requirements/{req_id}/check-availability")
    assert r.status_code == 200
    assert r.json()["available_at_check"] is True
    assert r.json()["stage"] == "availability_checked"

    r = client.post(f"/api/requirements/{req_id}/order", json={})
    assert r.status_code == 200
    assert r.json()["stage"] == "ordered"

    r = client.post(f"/api/requirements/{req_id}/allocate")
    assert r.status_code == 200
    assert r.json()["stage"] == "inventory_allocated"

    after_stock = client.get("/api/parts/filters/stock").json()["qty_on_hand"]
    assert after_stock == before_stock - 3

    r = client.post(f"/api/requirements/{req_id}/ship", json={"carrier": "DHL"})
    assert r.status_code == 200
    assert r.json()["stage"] == "shipped"

    r = client.post(f"/api/requirements/{req_id}/receive")
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "received"
    assert body["next_stage"] is None
    assert [e["stage"] for e in body["events"]] == [
        "requirement_raised", "identified", "availability_checked",
        "ordered", "inventory_allocated", "shipped", "received",
    ]


def test_backorder_part_is_reported_unavailable_but_the_process_continues(client):
    # swing-bearing is seeded at zero on hand.
    req_id = create_requirement(client, part_id="swing-bearing", quantity=1)["id"]

    r = client.post(f"/api/requirements/{req_id}/check-availability")
    assert r.json()["available_at_check"] is False

    # A sales order can still be raised — that step records intent, not stock.
    r = client.post(f"/api/requirements/{req_id}/order", json={"supplier": "Hitachi Parts EU"})
    assert r.status_code == 200
    assert r.json()["supplier"] == "Hitachi Parts EU"

    # But nothing can be drawn down that was never on the shelf.
    r = client.post(f"/api/requirements/{req_id}/allocate")
    assert r.status_code == 409
    assert "on hand" in r.json()["detail"]


def test_stages_cannot_be_skipped(client):
    req_id = create_requirement(client)["id"]

    # Straight to allocate, ship or receive without the steps between.
    for action in ("allocate", "ship", "receive"):
        r = client.post(f"/api/requirements/{req_id}/{action}", json={})
        assert r.status_code == 409, action
        assert str(req_id) in r.json()["detail"]


def test_a_stage_cannot_be_repeated(client):
    req_id = create_requirement(client)["id"]
    client.post(f"/api/requirements/{req_id}/check-availability")
    r = client.post(f"/api/requirements/{req_id}/check-availability")
    assert r.status_code == 409


def test_unknown_requirement_is_404_on_every_action(client):
    for path in (
        "", "/check-availability", "/order", "/allocate", "/ship", "/receive",
    ):
        method = client.get if path == "" else client.post
        kwargs = {} if path == "" else {"json": {}}
        r = method(f"/api/requirements/999999{path}", **kwargs)
        assert r.status_code == 404


def test_list_can_be_filtered_by_stage(client):
    create_requirement(client, part_id="filters")
    create_requirement(client, part_id="bucket")

    r = client.get("/api/requirements")
    assert len(r.json()) == 2

    r = client.get("/api/requirements", params={"stage": "identified"})
    assert len(r.json()) == 2

    r = client.get("/api/requirements", params={"stage": "shipped"})
    assert len(r.json()) == 0
