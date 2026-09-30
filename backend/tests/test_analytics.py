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
    # no raw IP address is ever persisted
    assert "ip" not in s and "client_ip" not in s

    p = _db("MATCH (:Session {session_id: $sid})-[:VIEWED]->(p:PageView {pageview_id: $pid}) RETURN p",
            sid=session_id, pid=pageview_id)[0]["p"]
    assert p["path"] == "#/parts-store" and p["duration_seconds"] == 42.5


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
