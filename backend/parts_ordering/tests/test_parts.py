def test_list_parts_returns_the_seeded_catalogue(client):
    r = client.get("/api/parts")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert ids == {
        "hydraulic-cylinder", "hydraulic-pump", "diesel-engine", "reduction-gear",
        "swing-bearing", "bucket", "track-assembly", "filters", "controller",
        "fuel-injection-pump",
    }


def test_stock_for_a_real_part(client):
    r = client.get("/api/parts/filters/stock")
    assert r.status_code == 200
    body = r.json()
    assert body["qty_on_hand"] > 0
    assert body["warehouse"]


def test_stock_for_a_missing_part_is_404(client):
    r = client.get("/api/parts/does-not-exist/stock")
    assert r.status_code == 404
