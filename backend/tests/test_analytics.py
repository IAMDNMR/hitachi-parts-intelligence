"""
Visitor analytics: session/pageview/duration events persist to Neo4j, the summary and recent-sessions endpoints
require a valid admin login, and the login endpoint rejects a wrong password.
"""
import uuid

from fastapi.testclient import TestClient

from app.config import settings
from app.db.neo4j.connection import get_neo4j_driver
from app.main import app

client = TestClient(app)
API = "/api/v1/analytics"


def _db(cypher, **params):
    with get_neo4j_driver().session() as s:
        return s.run(cypher, **params).data()


def test_session_start_pageview_and_duration_are_persisted(test_run_id):
    visitor_id = f"vis-{uuid.uuid4()}"
    session_id = f"sess-{uuid.uuid4()}"
    pageview_id = f"pv-{uuid.uuid4()}"

    r = client.post(f"{API}/event", json={
        "type": "session_start", "visitor_id": visitor_id, "session_id": session_id,
        "referrer": "https://example.com", "landing_path": "#/parts-store",
        "device": {"device_type": "desktop", "browser": "Chrome", "os": "Windows", "screen_w": 1920,
                   "screen_h": 1080, "language": "en-GB", "timezone": "Europe/Amsterdam"},
    })
    assert r.status_code == 200 and r.json() == {"ok": True}

    r = client.post(f"{API}/event", json={"type": "pageview", "visitor_id": visitor_id, "session_id": session_id,
                                          "pageview_id": pageview_id, "path": "#/parts-store"})
    assert r.status_code == 200

    r = client.post(f"{API}/event", json={"type": "duration", "visitor_id": visitor_id, "session_id": session_id,
                                          "pageview_id": pageview_id, "duration_seconds": 42.5})
    assert r.status_code == 200

    v = _db("MATCH (v:Visitor {visitor_id: $id}) RETURN v", id=visitor_id)[0]["v"]
    assert v["visit_count"] == 1 and v["first_seen"] and v["last_seen"]

    s = _db("MATCH (:Visitor {visitor_id: $vid})-[:HAD_SESSION]->(s:Session {session_id: $sid}) RETURN s",
            vid=visitor_id, sid=session_id)[0]["s"]
    assert s["referrer"] == "https://example.com" and s["landing_path"] == "#/parts-store"
    assert s["device_type"] == "desktop" and s["browser"] == "Chrome" and s["timezone"] == "Europe/Amsterdam"
    assert s["ip"]  # stored at the user's explicit instruction, disclosed in the cookie banner

    p = _db("MATCH (:Session {session_id: $sid})-[:VIEWED]->(p:PageView {pageview_id: $pid}) RETURN p",
            sid=session_id, pid=pageview_id)[0]["p"]
    assert p["path"] == "#/parts-store" and p["duration_seconds"] == 42.5


def test_pageview_is_recorded_even_if_it_arrives_before_session_start(test_run_id):
    """The browser fires session_start and pageview as two independent beacons with no ordering guarantee —
    this reproduces pageview genuinely landing first, which must not silently drop the page view."""
    visitor_id = f"vis-{uuid.uuid4()}"
    session_id = f"sess-{uuid.uuid4()}"
    pageview_id = f"pv-{uuid.uuid4()}"

    r = client.post(f"{API}/event", json={"type": "pageview", "visitor_id": visitor_id, "session_id": session_id,
                                          "pageview_id": pageview_id, "path": "#/parts-store"})
    assert r.status_code == 200

    p = _db("MATCH (:Session {session_id: $sid})-[:VIEWED]->(p:PageView {pageview_id: $pid}) RETURN p",
            sid=session_id, pid=pageview_id)
    assert len(p) == 1 and p[0]["p"]["path"] == "#/parts-store"

    # session_start arrives afterwards and fills in the device/geo fields on the same Session node
    r = client.post(f"{API}/event", json={
        "type": "session_start", "visitor_id": visitor_id, "session_id": session_id,
        "device": {"browser": "Chrome"},
    })
    assert r.status_code == 200
    sessions = _db("MATCH (:Visitor {visitor_id: $vid})-[:HAD_SESSION]->(s:Session {session_id: $sid}) RETURN s",
                   vid=visitor_id, sid=session_id)
    assert len(sessions) == 1 and sessions[0]["s"]["browser"] == "Chrome"

    pages = _db("MATCH (:Session {session_id: $sid})-[:VIEWED]->(p:PageView) RETURN count(p) AS n", sid=session_id)[0]["n"]
    assert pages == 1  # no duplicate Session or PageView was created by the second event


def test_duration_is_recorded_even_if_it_arrives_before_pageview(test_run_id):
    session_id = f"sess-{uuid.uuid4()}"
    pageview_id = f"pv-{uuid.uuid4()}"
    r = client.post(f"{API}/event", json={"type": "duration", "visitor_id": "v", "session_id": session_id,
                                          "pageview_id": pageview_id, "duration_seconds": 5})
    assert r.status_code == 200
    r = client.post(f"{API}/event", json={"type": "pageview", "visitor_id": "v", "session_id": session_id,
                                          "pageview_id": pageview_id, "path": "#/orders"})
    assert r.status_code == 200
    p = _db("MATCH (p:PageView {pageview_id: $id}) RETURN p", id=pageview_id)[0]["p"]
    assert p["path"] == "#/orders" and p["duration_seconds"] == 5.0


def test_a_returning_visitor_increments_visit_count(test_run_id):
    visitor_id = f"vis-{uuid.uuid4()}"
    for _ in range(3):
        client.post(f"{API}/event", json={"type": "session_start", "visitor_id": visitor_id,
                                          "session_id": f"sess-{uuid.uuid4()}"})
    v = _db("MATCH (v:Visitor {visitor_id: $id}) RETURN v.visit_count AS c", id=visitor_id)[0]["c"]
    assert v == 3


def test_login_rejects_wrong_password_and_accepts_the_configured_one():
    assert client.post(f"{API}/login", json={"password": "definitely-wrong"}).status_code == 401
    r = client.post(f"{API}/login", json={"password": settings.ANALYTICS_ADMIN_PASSWORD})
    assert r.status_code == 200 and r.json()["token"]


def test_summary_reports_bounce_landing_exit_referrers_and_time_patterns(test_run_id):
    token = client.post(f"{API}/login", json={"password": settings.ANALYTICS_ADMIN_PASSWORD}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    before = client.get(f"{API}/summary", headers=headers).json()

    visitor_id = f"vis-{uuid.uuid4()}"
    # Session A: lands on the store, views 2 pages, leaves from parts-intelligence (not a bounce)
    sid_a = f"sess-{uuid.uuid4()}"
    client.post(f"{API}/event", json={"type": "session_start", "visitor_id": visitor_id, "session_id": sid_a,
                                      "landing_path": "#/parts-store", "referrer": "https://news.example.org/a"})
    for pid, path, secs in ((f"pv-{uuid.uuid4()}", "#/parts-store", 10), (f"pv-{uuid.uuid4()}", "#/parts-intelligence", 4)):
        client.post(f"{API}/event", json={"type": "pageview", "visitor_id": visitor_id, "session_id": sid_a, "pageview_id": pid, "path": path})
        client.post(f"{API}/event", json={"type": "duration", "visitor_id": visitor_id, "session_id": sid_a, "pageview_id": pid, "duration_seconds": secs})
    # Session B: direct visit, one page only (a bounce)
    sid_b = f"sess-{uuid.uuid4()}"
    client.post(f"{API}/event", json={"type": "session_start", "visitor_id": f"vis-{uuid.uuid4()}", "session_id": sid_b, "landing_path": "#/orders"})
    client.post(f"{API}/event", json={"type": "pageview", "visitor_id": "x", "session_id": sid_b, "pageview_id": f"pv-{uuid.uuid4()}", "path": "#/orders"})

    after = client.get(f"{API}/summary", headers=headers).json()
    assert after["bounce_total_sessions"] == before["bounce_total_sessions"] + 2
    assert after["bounced_sessions"] == before["bounced_sessions"] + 1
    assert 0 <= after["bounce_rate_pct"] <= 100

    def count(rows, key, value):
        return next((r["sessions"] for r in rows if r[key] == value), 0)

    assert count(after["top_landing_pages"], "path", "#/parts-store") >= count(before["top_landing_pages"], "path", "#/parts-store") + 1
    assert count(after["top_exit_pages"], "path", "#/parts-intelligence") >= count(before["top_exit_pages"], "path", "#/parts-intelligence") + 1
    assert count(after["top_referrers"], "referrer", "https://news.example.org/a") >= 1
    assert count(after["top_referrers"], "referrer", "Direct") >= count(before["top_referrers"], "referrer", "Direct") + 1

    page = next(p for p in after["top_pages"] if p["path"] == "#/parts-store")
    assert page["views"] >= 1 and page["avg_seconds"] > 0
    assert any(h["sessions"] > 0 for h in after["by_hour"]) and all(0 <= h["hour"] <= 23 for h in after["by_hour"])
    assert any(w["sessions"] > 0 for w in after["by_weekday"]) and all(1 <= w["weekday"] <= 7 for w in after["by_weekday"])
    today = after["visits_by_day"][-1]
    assert today["sessions"] == today["new_sessions"] + today["returning_sessions"]


def test_interactions_click_scroll_question_and_order_feed_the_summary(test_run_id):
    token = client.post(f"{API}/login", json={"password": settings.ANALYTICS_ADMIN_PASSWORD}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    before = client.get(f"{API}/summary", headers=headers).json()

    visitor_id, sid = f"vis-{uuid.uuid4()}", f"sess-{uuid.uuid4()}"
    marker = f"test question {uuid.uuid4()}"
    client.post(f"{API}/event", json={"type": "session_start", "visitor_id": visitor_id, "session_id": sid})
    client.post(f"{API}/event", json={"type": "pageview", "visitor_id": visitor_id, "session_id": sid,
                                      "pageview_id": f"pv-{uuid.uuid4()}", "path": "#/"})

    def interact(name, label):
        r = client.post(f"{API}/event", json={"type": "interaction", "visitor_id": visitor_id, "session_id": sid,
                                              "interaction_id": f"int-{uuid.uuid4()}", "name": name, "label": label,
                                              "path": "#/"})
        assert r.status_code == 200 and r.json() == {"ok": True}

    interact("click", "Add to Cart")
    interact("click", "Add to Cart")
    for depth in ("25", "50"):
        interact("scroll_depth", depth)
    interact("pi_query", marker)
    interact("order_placed", "HCME-ORD-TEST")

    after = client.get(f"{API}/summary", headers=headers).json()

    def n(rows, key, value, field):
        return next((r[field] for r in rows if r[key] == value), 0)

    assert n(after["top_clicks"], "label", "Add to Cart", "clicks") == n(before["top_clicks"], "label", "Add to Cart", "clicks") + 2
    assert n(after["scroll_depth"], "depth", 25, "sessions") == n(before["scroll_depth"], "depth", 25, "sessions") + 1
    assert n(after["scroll_depth"], "depth", 50, "sessions") == n(before["scroll_depth"], "depth", 50, "sessions") + 1
    assert after["home_sessions"] == before["home_sessions"] + 1
    assert any(q["question"] == marker for q in after["recent_questions"])
    assert n(after["top_questions"], "question", marker.lower(), "asked") == 1
    assert after["converting_sessions"] == before["converting_sessions"] + 1
    assert after["orders_from_sessions"] == before["orders_from_sessions"] + 1
    assert 0 < after["conversion_rate_pct"] <= 100


def test_unknown_interaction_names_are_rejected(test_run_id):
    r = client.post(f"{API}/event", json={"type": "interaction", "visitor_id": "v", "session_id": "s",
                                          "interaction_id": "i", "name": "keylogger", "label": "x"})
    assert r.status_code == 400


def test_recent_sessions_include_the_ip_address(test_run_id):
    token = client.post(f"{API}/login", json={"password": settings.ANALYTICS_ADMIN_PASSWORD}).json()["token"]
    sid = f"sess-{uuid.uuid4()}"
    client.post(f"{API}/event", json={"type": "session_start", "visitor_id": f"vis-{uuid.uuid4()}", "session_id": sid})
    rows = client.get(f"{API}/sessions?limit=200", headers={"Authorization": f"Bearer {token}"}).json()["sessions"]
    mine = next(r for r in rows if r["session_id"] == sid)
    assert "ip" in mine and mine["ip"]


def test_summary_and_sessions_require_a_valid_admin_token():
    assert client.get(f"{API}/summary").status_code == 401
    assert client.get(f"{API}/sessions").status_code == 401
    assert client.get(f"{API}/summary", headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401

    token = client.post(f"{API}/login", json={"password": settings.ANALYTICS_ADMIN_PASSWORD}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    s = client.get(f"{API}/summary", headers=headers)
    assert s.status_code == 200
    body = s.json()
    assert set(body) >= {"total_visitors", "total_sessions", "avg_session_seconds", "top_pages", "top_countries",
                         "device_breakdown", "visits_by_day", "new_visitors", "returning_visitors"}

    sess = client.get(f"{API}/sessions", headers=headers)
    assert sess.status_code == 200 and "sessions" in sess.json()
