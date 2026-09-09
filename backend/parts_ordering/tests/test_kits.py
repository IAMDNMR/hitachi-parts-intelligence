"""Service kits — the planned half of a parts operation.

The kit is a way of RAISING requirements, not a second workflow. So most of
what these tests protect is that raising one produces perfectly ordinary
requirements which then behave like every other requirement in the system.
"""


def test_the_catalogue_of_kits_reports_what_a_planner_needs(client):
    kits = {k["code"]: k for k in client.get("/api/kits").json()}
    assert "SVC-500" in kits

    svc = kits["SVC-500"]
    assert svc["interval_hours"] == 500, "the scheduled kit recurs on machine hours"
    assert svc["line_count"] >= 1
    assert svc["ready"] is True, "filters are well stocked, so this one can go today"


def test_a_repair_kit_has_no_interval(client):
    """A repair kit is the parts a job needs, not something that recurs."""
    kits = {k["code"]: k for k in client.get("/api/kits").json()}
    assert kits["KIT-913-507"]["interval_hours"] is None


def test_readiness_is_judged_against_the_quantity_the_kit_calls_for(client):
    """Not against whether the part exists at all.

    The swing bearing kit calls for a bearing seeded at zero on hand, so the
    kit is not ready even though every other line is — which is the whole
    point of asking about a kit rather than about its parts.
    """
    kit = client.get("/api/kits/kit-swing-bearing").json()
    assert kit["ready"] is False
    by_part = {l["part"]["id"]: l for l in kit["lines"]}
    assert by_part["swing-bearing"]["covered"] is False
    assert by_part["filters"]["covered"] is True


def test_lead_time_is_the_slowest_line_not_the_average(client):
    """A service is not available until its slowest part is. An average would
    say the swing bearing kit lands in 22 days; it lands in 42."""
    kit = client.get("/api/kits/kit-swing-bearing").json()
    assert kit["longest_lead_days"] == max(l["lead_time_days"] for l in kit["lines"])
    assert kit["longest_lead_days"] == 42


def test_raising_a_kit_creates_one_requirement_per_line(client):
    before = len(client.get("/api/requirements").json())
    r = client.post(
        "/api/kits/kit-hydraulic-pump/raise", json={"machine_serial": "ZX350LC-7-0099"}
    )
    assert r.status_code == 201
    raised = r.json()
    assert len(raised) == 2
    assert {x["part"]["id"] for x in raised} == {"hydraulic-pump", "filters"}
    assert len(client.get("/api/requirements").json()) == before + 2


def test_the_kit_sets_the_quantities(client):
    """Two filters for a pump replacement, because the system is drained and
    bled on refit — the person raising it should not have to know that."""
    raised = client.post(
        "/api/kits/kit-hydraulic-pump/raise", json={"machine_serial": "ZX350LC-7-0100"}
    ).json()
    qty = {x["part"]["id"]: x["quantity"] for x in raised}
    assert qty == {"hydraulic-pump": 1, "filters": 2}


def test_what_a_kit_raises_is_an_ordinary_requirement(client):
    """The point of the design. A kit line goes through the same seven stages
    under the same rules as anything raised by hand."""
    raised = client.post(
        "/api/kits/svc-500h/raise", json={"machine_serial": "ZX210-7-0042"}
    ).json()
    rid = raised[0]["id"]

    assert client.post(f"/api/requirements/{rid}/check-availability").status_code == 200
    assert client.post(f"/api/requirements/{rid}/order", json={}).status_code == 200
    assert client.post(f"/api/requirements/{rid}/allocate").status_code == 200
    # And the rules still bite: receiving before shipping is refused.
    assert client.post(f"/api/requirements/{rid}/receive").status_code == 409


def test_a_kit_can_be_raised_even_when_the_shelf_is_short(client):
    """The case where ordering ahead matters most is the one where the parts
    are not there. Refusing would make the feature useless exactly then."""
    r = client.post(
        "/api/kits/kit-swing-bearing/raise", json={"machine_serial": "ZX490LCH-7-0007"}
    )
    assert r.status_code == 201
    assert len(r.json()) == 2


def test_the_reason_names_the_service_that_raised_it(client):
    raised = client.post(
        "/api/kits/svc-500h/raise", json={"machine_serial": "ZX250LC-7-0011"}
    ).json()
    assert "500-hour service" in raised[0]["reason"]
    assert "SVC-500" in raised[0]["reason"]


def test_an_unknown_kit_is_404(client):
    r = client.post("/api/kits/no-such-kit/raise", json={"machine_serial": "ZX210-7-1"})
    assert r.status_code == 404
    assert client.get("/api/kits/no-such-kit").status_code == 404


def test_every_kit_only_calls_for_parts_the_catalogue_holds(client):
    """A kit naming a part nobody stocks cannot be ordered, and nothing else
    in the system would catch it."""
    parts = {p["id"] for p in client.get("/api/parts").json()}
    for row in client.get("/api/kits").json():
        kit = client.get(f"/api/kits/{row['id']}").json()
        for line in kit["lines"]:
            assert line["part"]["id"] in parts, f"{row['code']} calls for a part not sold"
