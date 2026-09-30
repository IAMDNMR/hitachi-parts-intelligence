"""
backend/app/modules/analytics/service.py

First-party visitor analytics. Real, recorded browser events only — never fabricated. Everything lives in the same
Neo4j AuraDB as the rest of the app (no second database).

Model:
  (:Visitor {visitor_id, first_seen, last_seen, visit_count})
    -[:HAD_SESSION]-> (:Session {session_id, started_at, last_seen_at, country, region, city, device_type,
                                  browser, os, screen_w, screen_h, language, timezone, referrer, landing_path})
        -[:VIEWED]-> (:PageView {pageview_id, path, entered_at, duration_seconds})

Privacy: the raw IP address is used once to resolve an approximate country/region/city, then discarded — it is
never written to the database. A visitor who has not accepted the cookie banner never reaches this module at all
(the frontend does not call it until consent is given).
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.errors.exceptions import UnauthorizedError, ValidationError

_GEO_CACHE: Dict[str, Dict[str, Optional[str]]] = {}
_GEO_CACHE_TTL_SECONDS = 3600
_geo_cache_at: Dict[str, float] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def geolocate_ip(ip: Optional[str]) -> Dict[str, Optional[str]]:
    """Approximate country/region/city from an IP address, via a free non-commercial lookup (ip-api.com).
    Best-effort: any failure (private/local IP, no network, rate limit) returns all-None, never a guess."""
    empty = {"country": None, "region": None, "city": None}
    if not ip or ip in ("127.0.0.1", "::1") or ip.startswith(("10.", "192.168.", "172.")):
        return empty
    cached_at = _geo_cache_at.get(ip, 0)
    if ip in _GEO_CACHE and time.time() - cached_at < _GEO_CACHE_TTL_SECONDS:
        return _GEO_CACHE[ip]
    try:
        r = httpx.get(f"http://ip-api.com/json/{ip}", params={"fields": "status,country,regionName,city"}, timeout=2.0)
        d = r.json()
        result = ({"country": d.get("country"), "region": d.get("regionName"), "city": d.get("city")}
                  if d.get("status") == "success" else empty)
    except Exception:
        result = empty
    _GEO_CACHE[ip] = result
    _geo_cache_at[ip] = time.time()
    return result


def record_session_start(session, visitor_id: str, session_id: str, client_ip: Optional[str],
                         referrer: Optional[str], landing_path: Optional[str], device: Dict[str, Any],
                         test_run_id: Optional[str] = None) -> None:
    if not visitor_id or not session_id:
        raise ValidationError("visitor_id and session_id are required")
    geo = geolocate_ip(client_ip)
    session.run(
        """
        MERGE (v:Visitor {visitor_id: $visitor_id})
        ON CREATE SET v.first_seen = $now, v.visit_count = 0
        SET v.last_seen = $now, v.visit_count = v.visit_count + 1
        MERGE (s:Session {session_id: $session_id})
        ON CREATE SET s.started_at = $now
        SET s.visitor_id = $visitor_id, s.last_seen_at = $now,
            s.country = $country, s.region = $region, s.city = $city,
            s.device_type = $device_type, s.browser = $browser, s.os = $os,
            s.screen_w = $screen_w, s.screen_h = $screen_h,
            s.language = $language, s.timezone = $tz,
            s.referrer = $referrer, s.landing_path = $landing_path
        MERGE (v)-[:HAD_SESSION]->(s)
        WITH v, s
        FOREACH (_ IN CASE WHEN $test_run_id IS NULL THEN [] ELSE [1] END | SET v.testRunId = $test_run_id, s.testRunId = $test_run_id)
        """,
        visitor_id=visitor_id, session_id=session_id, now=_now_iso(),
        country=geo["country"], region=geo["region"], city=geo["city"],
        device_type=device.get("device_type"), browser=device.get("browser"), os=device.get("os"),
        screen_w=device.get("screen_w"), screen_h=device.get("screen_h"),
        language=device.get("language"), tz=device.get("timezone"),
        referrer=referrer, landing_path=landing_path, test_run_id=test_run_id,
    ).consume()


def record_pageview(session, session_id: str, pageview_id: str, path: str, test_run_id: Optional[str] = None) -> None:
    if not session_id or not pageview_id or not path:
        raise ValidationError("session_id, pageview_id and path are required")
    session.run(
        """
        MATCH (s:Session {session_id: $session_id})
        SET s.last_seen_at = $now
        MERGE (p:PageView {pageview_id: $pageview_id})
        ON CREATE SET p.path = $path, p.entered_at = $now, p.duration_seconds = 0
        MERGE (s)-[:VIEWED]->(p)
        WITH p
        FOREACH (_ IN CASE WHEN $test_run_id IS NULL THEN [] ELSE [1] END | SET p.testRunId = $test_run_id)
        """,
        session_id=session_id, pageview_id=pageview_id, path=path, now=_now_iso(), test_run_id=test_run_id,
    ).consume()


def record_duration(session, pageview_id: str, duration_seconds: float) -> None:
    if not pageview_id:
        raise ValidationError("pageview_id is required")
    session.run(
        "MATCH (p:PageView {pageview_id: $id}) SET p.duration_seconds = $d",
        id=pageview_id, d=max(0.0, min(float(duration_seconds or 0), 3600.0)),
    ).consume()


def check_admin_password(supplied: str, expected: str) -> None:
    import hmac
    if not expected or not hmac.compare_digest(supplied or "", expected):
        raise UnauthorizedError("Incorrect password")


_SUMMARY_Q = """
CALL { MATCH (v:Visitor) RETURN count(v) AS total_visitors }
CALL { MATCH (s:Session) RETURN count(s) AS total_sessions }
CALL { MATCH (v:Visitor) WHERE v.last_seen >= $today RETURN count(v) AS visitors_today }
CALL { MATCH (s:Session) WHERE s.started_at >= $today RETURN count(s) AS sessions_today }
CALL { MATCH (v:Visitor) RETURN sum(CASE WHEN v.visit_count = 1 THEN 1 ELSE 0 END) AS new_visitors,
                                sum(CASE WHEN v.visit_count > 1 THEN 1 ELSE 0 END) AS returning_visitors }
CALL {
  MATCH (s:Session)-[:VIEWED]->(p:PageView)
  WITH s, sum(p.duration_seconds) AS secs
  RETURN avg(secs) AS avg_session_seconds
}
// Each of the following always returns exactly one row (collect() inside the subquery), even with zero matches —
// a bare CALL{} that can return zero rows would drop the whole pipeline to nothing (Neo4j's per-row flatMap semantics).
CALL {
  MATCH (:Session)-[:VIEWED]->(p:PageView)
  WITH p.path AS path, count(p) AS views, sum(p.duration_seconds) AS total_seconds
  ORDER BY total_seconds DESC LIMIT 10
  RETURN collect({path: path, views: views, total_seconds: total_seconds}) AS top_pages
}
CALL {
  MATCH (s:Session) WHERE s.country IS NOT NULL
  WITH s.country AS country, count(s) AS sessions
  ORDER BY sessions DESC LIMIT 10
  RETURN collect({country: country, sessions: sessions}) AS top_countries
}
CALL {
  MATCH (s:Session) WHERE s.device_type IS NOT NULL
  WITH s.device_type AS device_type, count(s) AS sessions
  ORDER BY sessions DESC
  RETURN collect({device_type: device_type, sessions: sessions}) AS device_breakdown
}
CALL {
  MATCH (s:Session) WHERE s.started_at >= $range_start
  WITH substring(s.started_at, 0, 10) AS day, count(s) AS sessions
  ORDER BY day
  RETURN collect({date: day, sessions: sessions}) AS visits_by_day
}
RETURN total_visitors, total_sessions, visitors_today, sessions_today, new_visitors, returning_visitors,
       avg_session_seconds, top_pages, top_countries, device_breakdown, visits_by_day
"""


def get_summary(session, days: int = 30) -> Dict[str, Any]:
    from datetime import timedelta
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    range_start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    row = session.run(_SUMMARY_Q, today=today, range_start=range_start).single()
    d = dict(row)
    d["avg_session_seconds"] = round(d["avg_session_seconds"] or 0, 1)
    d["new_visitors"] = d["new_visitors"] or 0
    d["returning_visitors"] = d["returning_visitors"] or 0
    return d


def get_recent_sessions(session, limit: int = 50) -> List[Dict[str, Any]]:
    rows = session.run(
        """
        MATCH (v:Visitor)-[:HAD_SESSION]->(s:Session)
        OPTIONAL MATCH (s)-[:VIEWED]->(p:PageView)
        WITH v, s, count(p) AS pages, sum(p.duration_seconds) AS total_seconds
        RETURN s.session_id AS session_id, v.visitor_id AS visitor_id, s.started_at AS started_at,
               s.country AS country, s.region AS region, s.city AS city,
               s.device_type AS device_type, s.browser AS browser, s.os AS os,
               s.referrer AS referrer, s.landing_path AS landing_path,
               v.visit_count AS visitor_visit_count, pages, coalesce(total_seconds, 0) AS total_seconds
        ORDER BY s.started_at DESC LIMIT $limit
        """,
        limit=limit,
    ).data()
    return rows
