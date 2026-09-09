"""
The Machine, and the rule it makes possible.

A requirement used to name its machine as free text; the database still holds
"AXZ120", which is not a Hitachi model and matches no fitment record. These
tests hold the line that made that impossible: a requirement names a real
machine, and a machine only accepts parts the catalogue lists against its own
model.
"""
from .conftest import A_MACHINE, A_SMALL_MACHINE


# --------------------------------------------------------------- the record


def test_the_fleet_lists_machines_with_their_context(client):
    rows = client.get("/api/machines").json()
    assert len(rows) >= 2
    one = next(r for r in rows if r["id"] == A_MACHINE)
    assert one["serial_number"] == "ZX350-4521"
    assert one["model"] == "ZX350LC-7"
    assert one["customer"]["name"]
    assert one["dealer"]["name"]


def test_a_machine_reports_what_it_is_waiting_on(client):
    """The number a fleet list exists to show at a glance."""
    before = next(r for r in client.get("/api/machines").json() if r["id"] == A_MACHINE)
    client.post(
        "/api/requirements",
        json={"machine_id": A_MACHINE, "part_id": "filters", "quantity": 1, "reason": "x"},
    )
    after = next(r for r in client.get("/api/machines").json() if r["id"] == A_MACHINE)
    assert after["open_requirements"] == before["open_requirements"] + 1


def test_machines_can_be_found_and_filtered(client):
    assert all(
        m["model"] == "ZX210-7" for m in client.get("/api/machines?model=ZX210-7").json()
    )
    found = client.get("/api/machines?search=ZX210").json()
    assert any(m["id"] == A_SMALL_MACHINE for m in found)
    # Searchable by the customer that owns it, not only by its own fields.
    by_customer = client.get("/api/machines?search=Terra").json()
    assert by_customer
    assert all("Terra" in m["customer"]["name"] for m in by_customer)


def test_warranty_state_is_derived_not_stored(client):
    """A stored flag is wrong the day after it is written."""
    for m in client.get("/api/machines").json():
        assert isinstance(m["in_warranty"], bool)
    assert client.get("/api/machines?warranty=in").status_code == 200


def test_an_unknown_machine_is_404(client):
    assert client.get("/api/machines/no-such-machine").status_code == 404


# ------------------------------------------------------------- registration


def _new(serial="ZX350-9001", model="ZX350LC-7", **over):
    body = {
        "serial_number": serial,
        "model": model,
        "customer_id": "terra-bouw",
        "dealer_id": "hcme-benelux",
    }
    body.update(over)
    return body


def test_a_machine_can_be_commissioned(client):
    r = client.post("/api/machines", json=_new())
    assert r.status_code == 201
    assert r.json()["serial_number"] == "ZX350-9001"


def test_a_serial_cannot_be_registered_twice(client):
    client.post("/api/machines", json=_new())
    again = client.post("/api/machines", json=_new())
    assert again.status_code == 409
    assert "already registered" in again.json()["detail"]


def test_a_machine_whose_model_nothing_fits_is_refused(client):
    """Accepting it would create a record that looks fine and cannot be
    ordered parts against — which is exactly how "AXZ120" happened."""
    r = client.post("/api/machines", json=_new(serial="XX-1", model="NOT-A-MODEL"))
    assert r.status_code == 409
    assert "fitting" in r.json()["detail"]


def test_a_machine_needs_a_real_customer_and_dealer(client):
    r = client.post("/api/machines", json=_new(serial="ZX350-9002", customer_id="nobody"))
    assert r.status_code == 404
    r = client.post("/api/machines", json=_new(serial="ZX350-9003", dealer_id="nobody"))
    assert r.status_code == 404


def test_status_can_be_changed_but_identity_cannot(client):
    r = client.patch("/api/machines/" + A_MACHINE, json={"status": "down"})
    assert r.status_code == 200
    assert r.json()["status"] == "down"
    # Serial and model are not accepted fields: identity is not an attribute,
    # and the model is what fitment is validated against — editing it would
    # let somebody edit their way around the rule on requirements already
    # raised.
    client.patch("/api/machines/" + A_MACHINE, json={"model": "ZX210-7"})
    assert client.get("/api/machines/" + A_MACHINE).json()["model"] == "ZX350LC-7"


# ------------------------------------------------------------------ fitment


def test_a_machine_reports_the_parts_that_fit_it(client):
    """Twenty-eight fitment rows, read as an answer for the first time."""
    parts = client.get("/api/machines/" + A_MACHINE + "/parts").json()
    assert parts
    ids = {p["id"] for p in parts}
    assert "swing-bearing" in ids
    assert "hydraulic-cylinder" in ids
    for p in parts:
        assert p["assembly"], "every fitting part says where it sits on the machine"


def test_a_smaller_machine_fits_fewer_parts(client):
    """The rule is real, not decorative: the ZX210 has no swing bearing listed
    against it."""
    big = {p["id"] for p in client.get("/api/machines/" + A_MACHINE + "/parts").json()}
    small = {
        p["id"] for p in client.get("/api/machines/" + A_SMALL_MACHINE + "/parts").json()
    }
    assert small < big
    assert "swing-bearing" not in small
    assert "filters" in small


def test_a_superseded_part_is_not_offered_for_a_machine(client):
    """Same rule the catalogue uses — an old number resolves, but is never
    offered."""
    ids = {p["id"] for p in client.get("/api/machines/" + A_MACHINE + "/parts").json()}
    assert "hydraulic-pump-911118002" not in ids


# ------------------------------------------ the rule, on raising a requirement


def test_a_part_that_fits_is_accepted(client):
    r = client.post(
        "/api/requirements",
        json={
            "machine_id": A_MACHINE,
            "part_id": "swing-bearing",
            "quantity": 1,
            "reason": "Wear check",
        },
    )
    assert r.status_code == 201
    assert r.json()["machine_model"] == "ZX350LC-7"


def test_a_part_that_does_not_fit_is_rejected(client):
    """Rejected, and never quietly substituted: fitting a different component
    to somebody's machine is the one mistake a parts system must not make on
    its own initiative. The message names both halves so the person raising it
    can see which one they got wrong."""
    r = client.post(
        "/api/requirements",
        json={
            "machine_id": A_SMALL_MACHINE,
            "part_id": "swing-bearing",
            "quantity": 1,
            "reason": "Wear check",
        },
    )
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "ZX210-7" in detail
    assert "ZX350LC-7" in detail


def test_a_requirement_cannot_name_a_machine_that_does_not_exist(client):
    """The free-text era, ended."""
    r = client.post(
        "/api/requirements",
        json={"machine_id": "AXZ999", "part_id": "filters", "quantity": 1, "reason": "x"},
    )
    assert r.status_code == 404


def test_a_requirement_cannot_be_edited_onto_a_machine_it_does_not_fit(client):
    """No editing around the check that creation enforces."""
    made = client.post(
        "/api/requirements",
        json={
            "machine_id": A_MACHINE,
            "part_id": "swing-bearing",
            "quantity": 1,
            "reason": "Wear check",
        },
    ).json()
    r = client.patch(
        "/api/requirements/" + str(made["id"]), json={"machine_id": A_SMALL_MACHINE}
    )
    assert r.status_code == 409


# ------------------------------------------------------------ parts history


def test_a_machine_reports_the_parts_it_has_needed(client):
    """Derived from requirements. There is deliberately no history table — a
    second record of the same events is a second thing to keep in step."""
    assert client.get("/api/machines/" + A_MACHINE + "/requirements").json() == []
    client.post(
        "/api/requirements",
        json={
            "machine_id": A_MACHINE,
            "part_id": "filters",
            "quantity": 2,
            "reason": "500-hour service",
        },
    )
    history = client.get("/api/machines/" + A_MACHINE + "/requirements").json()
    assert len(history) == 1
    assert history[0]["part"]["part_number"] == "905-012-100"
    assert history[0]["quantity"] == 2
    assert history[0]["stage"] == "identified"


def test_one_machines_history_is_not_anothers(client):
    client.post(
        "/api/requirements",
        json={"machine_id": A_MACHINE, "part_id": "filters", "quantity": 1, "reason": "x"},
    )
    assert client.get("/api/machines/" + A_SMALL_MACHINE + "/requirements").json() == []
