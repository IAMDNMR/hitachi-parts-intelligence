"""The part record — the after-sales answers to "what is this part": its
number, what it fits, what it replaced, what documents cover it, and which
machines have actually needed it."""

from .conftest import A_MACHINE


def test_part_detail_carries_number_lead_time_and_stock(client):
    r = client.get("/api/parts/swing-bearing")
    assert r.status_code == 200
    body = r.json()
    assert body["part_number"] == "913-507-006"
    assert body["lead_time_days"] == 42
    assert body["stock"]["warehouse"]
    assert body["stock"]["qty_on_hand"] == 0  # seeded on backorder


def test_part_detail_lists_the_machines_it_fits(client):
    body = client.get("/api/parts/filters").json()
    models = {f["machine_model"] for f in body["fitments"]}
    assert "ZX350LC-7" in models  # the machine the site's own hero identifies
    assert len(models) == 4
    assert all(f["assembly"] for f in body["fitments"])


def test_part_detail_lists_documents_where_they_exist(client):
    body = client.get("/api/parts/swing-bearing").json()
    kinds = {d["doc_type"] for d in body["documents"]}
    assert kinds == {"Fitting instruction", "Service bulletin"}

    # And is simply empty where they do not — not an error.
    body = client.get("/api/parts/bucket").json()
    assert body["documents"] == []


def test_unknown_part_detail_is_404(client):
    assert client.get("/api/parts/not-a-part").status_code == 404


def test_search_matches_name_number_and_category(client):
    by_name = client.get("/api/parts", params={"search": "hydraulic"}).json()
    assert {p["id"] for p in by_name} == {"hydraulic-cylinder", "hydraulic-pump"}

    by_number = client.get("/api/parts", params={"search": "913-507"}).json()
    assert [p["id"] for p in by_number] == ["swing-bearing"]

    by_category = client.get("/api/parts", params={"search": "Undercarriage"}).json()
    assert [p["id"] for p in by_category] == ["track-assembly"]

    assert client.get("/api/parts", params={"search": "zzzz"}).json() == []


def test_usage_reports_the_machines_that_have_needed_the_part(client):
    assert client.get("/api/parts/filters/usage").json() == []

    client.post(
        "/api/requirements",
        json={
            "machine_id": A_MACHINE,
            "part_id": "filters",
            "quantity": 2,
            "reason": "500-hour service",
        },
    )
    usage = client.get("/api/parts/filters/usage").json()
    assert len(usage) == 1
    assert usage[0]["machine_serial"] == "ZX350-4521"
    # The machine as a record, so the part record can link back to Machine 360
    assert usage[0]["machine_id"] == A_MACHINE
    assert usage[0]["machine_model"] == "ZX350LC-7"
    assert usage[0]["quantity"] == 2
    assert usage[0]["stage"] == "identified"


def test_usage_for_unknown_part_is_404(client):
    assert client.get("/api/parts/not-a-part/usage").status_code == 404


def test_a_superseded_number_still_resolves(client):
    """The whole reason the old row is kept: a machine in the field carries
    the old number on its label, someone reads it off, and it has to answer."""
    r = client.get("/api/parts/hydraulic-pump-911118002")
    assert r.status_code == 200
    assert r.json()["part_number"] == "911-118-002"


def test_a_superseded_part_is_not_offered_in_the_catalogue(client):
    """Surviving is not the same as being for sale. Listing it would put two
    parts called "Hydraulic Pump" in the catalogue, one of which cannot be
    had, and would let a requirement be raised against a dead number."""
    ids = {p["id"] for p in client.get("/api/parts").json()}
    assert "hydraulic-pump" in ids
    assert "hydraulic-pump-911118002" not in ids


def test_a_superseded_part_is_not_offered_by_search_either(client):
    """The exclusion is on the query, not on the unsearched listing, so
    searching the old number does not smuggle it back into the catalogue."""
    rows = client.get("/api/parts", params={"search": "Hydraulic Pump"}).json()
    assert [p["id"] for p in rows] == ["hydraulic-pump"]


def test_the_replacement_reports_what_it_replaced(client):
    body = client.get("/api/parts/hydraulic-pump").json()
    assert body["supersedes"]["part_number"] == "911-118-002"
    assert body["supersedes"]["id"] == "hydraulic-pump-911118002"


def test_the_superseded_part_replaces_nothing_itself(client):
    """The chain ends. Without this, a UI following `supersedes` would have
    no way of knowing when to stop."""
    assert client.get("/api/parts/hydraulic-pump-911118002").json()["supersedes"] is None


def test_a_superseded_part_reports_what_replaced_it(client):
    """The question someone holding a dead label actually has is "what do I
    order instead" — which `supersedes` alone can never answer."""
    body = client.get("/api/parts/hydraulic-pump-911118002").json()
    assert body["superseded_by"]["part_number"] == "911-118-004"
    assert body["superseded_by"]["id"] == "hydraulic-pump"


def test_a_current_part_is_superseded_by_nothing(client):
    assert client.get("/api/parts/hydraulic-pump").json()["superseded_by"] is None
    assert client.get("/api/parts/bucket").json()["superseded_by"] is None
