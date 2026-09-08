"""Editing and cancelling — the two things a working tool needs that
"create and advance" alone does not give you, and the two most dangerous to
get wrong, because both can silently disagree with a physical shelf."""


def make(client, part_id="filters", quantity=3):
    return client.post(
        "/api/requirements",
        json={
            "machine_serial": "ZX350-4521",
            "part_id": part_id,
            "quantity": quantity,
            "reason": "Scheduled service",
        },
    ).json()


def stock(client, part_id="filters"):
    return client.get(f"/api/parts/{part_id}/stock").json()["qty_on_hand"]


def test_edit_changes_the_fields_and_records_what_changed(client):
    req = make(client)
    r = client.patch(
        f"/api/requirements/{req['id']}",
        json={"machine_serial": "ZX490-0002", "reason": "Revised after inspection"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["machine_serial"] == "ZX490-0002"
    assert body["reason"] == "Revised after inspection"
    assert any("Edited" in (e["note"] or "") for e in body["events"])


def test_patch_leaves_omitted_fields_alone(client):
    req = make(client, quantity=3)
    body = client.patch(f"/api/requirements/{req['id']}", json={"quantity": 5}).json()
    assert body["quantity"] == 5
    assert body["machine_serial"] == "ZX350-4521"
    assert body["reason"] == "Scheduled service"


def test_changing_quantity_invalidates_a_previous_availability_answer(client):
    req = make(client, quantity=3)
    client.post(f"/api/requirements/{req['id']}/check-availability")

    body = client.patch(f"/api/requirements/{req['id']}", json={"quantity": 90}).json()
    # A "yes, 3 are on the shelf" is not an answer about 90.
    assert body["stage"] == "identified"
    assert body["available_at_check"] is None
    assert body["next_stage"] == "availability_checked"


def test_editing_is_refused_once_stock_has_been_drawn_down(client):
    req = make(client, quantity=3)
    rid = req["id"]
    client.post(f"/api/requirements/{rid}/check-availability")
    client.post(f"/api/requirements/{rid}/order", json={})
    client.post(f"/api/requirements/{rid}/allocate")

    r = client.patch(f"/api/requirements/{rid}", json={"quantity": 1})
    assert r.status_code == 409
    assert "drawn down" in r.json()["detail"]


def test_cancelling_before_allocation_leaves_stock_untouched(client):
    before = stock(client)
    req = make(client, quantity=3)
    assert client.delete(f"/api/requirements/{req['id']}").status_code == 204
    assert stock(client) == before
    assert client.get(f"/api/requirements/{req['id']}").status_code == 404


def test_cancelling_after_allocation_puts_the_stock_back(client):
    before = stock(client)
    req = make(client, quantity=3)
    rid = req["id"]
    client.post(f"/api/requirements/{rid}/check-availability")
    client.post(f"/api/requirements/{rid}/order", json={})
    client.post(f"/api/requirements/{rid}/allocate")
    assert stock(client) == before - 3

    assert client.delete(f"/api/requirements/{rid}").status_code == 204
    # The part never left the building, so it is back on the shelf.
    assert stock(client) == before


def test_cancelling_after_receipt_does_not_invent_stock(client):
    before = stock(client)
    req = make(client, quantity=3)
    rid = req["id"]
    for action in ("check-availability", "order", "allocate", "ship", "receive"):
        client.post(f"/api/requirements/{rid}/{action}", json={})
    assert stock(client) == before - 3

    assert client.delete(f"/api/requirements/{rid}").status_code == 204
    # The part is on the machine. Deleting the paperwork must not put it back.
    assert stock(client) == before - 3


def test_cancelling_something_that_is_not_there_is_404(client):
    assert client.delete("/api/requirements/999999").status_code == 404


def test_stock_can_be_received_in_and_taken_out(client):
    before = stock(client, "swing-bearing")
    assert before == 0

    r = client.post("/api/parts/swing-bearing/stock/adjust", json={"delta": 4})
    assert r.status_code == 200
    assert r.json()["qty_on_hand"] == 4

    r = client.post("/api/parts/swing-bearing/stock/adjust", json={"delta": -1})
    assert r.json()["qty_on_hand"] == 3


def test_stock_cannot_be_driven_negative(client):
    r = client.post("/api/parts/swing-bearing/stock/adjust", json={"delta": -1})
    assert r.status_code == 409
    assert client.get("/api/parts/swing-bearing/stock").json()["qty_on_hand"] == 0


def test_adjusting_stock_for_an_unknown_part_is_404(client):
    assert (
        client.post("/api/parts/nope/stock/adjust", json={"delta": 1}).status_code == 404
    )
