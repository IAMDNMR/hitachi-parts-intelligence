"""
backend/app/modules/analytics/service.py

First-party visitor analytics. Real, recorded browser events only — never fabricated. Everything lives in the same
Neo4j AuraDB as the rest of the app (no second database).

Model:
  (:Visitor {visitor_id, first_seen, last_seen, visit_count})
    -[:HAD_SESSION]-> (:Session {session_id, started_at, last_seen_at, country, region, city, device_type,
                                  browser, os, screen_w, screen_h, language, timezone, referrer, landing_path})
        -[:VIEWED]-> (:PageView {pageview_id, path, entered_at, duration_seconds})
        -[:DID]->    (:Interaction {interaction_id, name, label, path, at})
                     name = 'click' | 'scroll_depth' | 'pi_query' | 'order_placed'

Privacy: the IP address is used to resolve an approximate country/region/city and is also stored on the Session
node, at the user's explicit instruction (disclosed in the cookie banner). A visitor who has not accepted the
cookie banner never reaches this module at all (the frontend does not call it until consent is given).
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
        SET s.visitor_id = $visitor_id, s.last_seen_at = $now, s.ip = $ip,
            s.country = $country, s.region = $region, s.city = $city,
            s.device_type = $device_type, s.browser = $browser, s.os = $os,
            s.screen_w = $screen_w, s.screen_h = $screen_h,
            s.language = $language, s.timezone = $tz,
            s.referrer = $referrer, s.landing_path = $landing_path
        MERGE (v)-[:HAD_SESSION]->(s)
        WITH v, s
        FOREACH (_ IN CASE WHEN $test_run_id IS NULL THEN [] ELSE [1] END | SET v.testRunId = $test_run_id, s.testRunId = $test_run_id)
        """,
        visitor_id=visitor_id, session_id=session_id, now=_now_iso(), ip=client_ip,
        country=geo["country"], region=geo["region"], city=geo["city"],
        device_type=device.get("device_type"), browser=device.get("browser"), os=device.get("os"),
        screen_w=device.get("screen_w"), screen_h=device.get("screen_h"),
        language=device.get("language"), tz=device.get("timezone"),
        referrer=referrer, landing_path=landing_path, test_run_id=test_run_id,
    ).consume()


def record_pageview(session, session_id: str, pageview_id: str, path: str, test_run_id: Optional[str] = None) -> None:
    """MERGE, not MATCH, on the Session: the browser fires 'session_start' and 'pageview' as two independent
    beacon requests back to back with no ordering guarantee, so 'pageview' can genuinely reach the database
    first. A plain MATCH against a not-yet-created Session would find nothing and silently drop the whole write
    (every clause after a zero-row MATCH is skipped) — the page view would just vanish. MERGE self-heals: if
    'session_start' lands after this, its own MERGE fills in the device/geo fields on the same node."""
    if not session_id or not pageview_id or not path:
        raise ValidationError("session_id, pageview_id and path are required")
    session.run(
        """
        MERGE (s:Session {session_id: $session_id})
        ON CREATE SET s.started_at = $now
        SET s.last_seen_at = $now
        MERGE (p:PageView {pageview_id: $pageview_id})
        ON CREATE SET p.duration_seconds = 0
        SET p.path = $path, p.entered_at = coalesce(p.entered_at, $now)
        MERGE (s)-[:VIEWED]->(p)
        WITH p
        FOREACH (_ IN CASE WHEN $test_run_id IS NULL THEN [] ELSE [1] END | SET p.testRunId = $test_run_id)
        """,
        session_id=session_id, pageview_id=pageview_id, path=path, now=_now_iso(), test_run_id=test_run_id,
    ).consume()


def record_duration(session, pageview_id: str, duration_seconds: float) -> None:
    """MERGE for the same race-safety reason as record_pageview: the 'duration' beacon (sent on navigating away)
    can in principle reach the database before the 'pageview' beacon it belongs to. Whichever arrives second just
    fills in the fields the first one didn't set."""
    if not pageview_id:
        raise ValidationError("pageview_id is required")
    session.run(
        "MERGE (p:PageView {pageview_id: $id}) ON CREATE SET p.entered_at = $now SET p.duration_seconds = $d",
        id=pageview_id, now=_now_iso(), d=max(0.0, min(float(duration_seconds or 0), 3600.0)),
    ).consume()


_INTERACTION_NAMES = {"click", "scroll_depth", "pi_query", "order_placed"}


def record_interaction(session, session_id: str, interaction_id: str, name: str, label: Optional[str],
                       path: Optional[str], test_run_id: Optional[str] = None) -> None:
    """A single named thing a visitor did (a click, a scroll milestone, a Parts Intelligence question, an order).
    MERGE on the Session for the same race-safety reason as record_pageview. Free text is length-capped."""
    if not session_id or not interaction_id or name not in _INTERACTION_NAMES:
        raise ValidationError("session_id, interaction_id and a known interaction name are required")
    session.run(
        """
        MERGE (s:Session {session_id: $session_id})
        ON CREATE SET s.started_at = $now
        SET s.last_seen_at = $now
        MERGE (i:Interaction {interaction_id: $interaction_id})
        ON CREATE SET i.at = $now
        SET i.name = $name, i.label = $label, i.path = $path
        MERGE (s)-[:DID]->(i)
        WITH i
        FOREACH (_ IN CASE WHEN $test_run_id IS NULL THEN [] ELSE [1] END | SET i.testRunId = $test_run_id)
        """,
        session_id=session_id, interaction_id=interaction_id, name=name,
        label=(label or "")[:300] or None, path=(path or "")[:200] or None,
        now=_now_iso(), test_run_id=test_run_id,
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
CALL {
  MATCH (s:Session)
  OPTIONAL MATCH (s)-[:VIEWED]->(p:PageView)
  WITH s, count(p) AS pages
  RETURN count(CASE WHEN pages <= 1 THEN 1 END) AS bounced_sessions, count(s) AS bounce_total_sessions,
         CASE WHEN count(s) = 0 THEN 0.0 ELSE round(100.0 * count(CASE WHEN pages <= 1 THEN 1 END) / count(s), 1) END AS bounce_rate_pct
}
// Each of the following always returns exactly one row (collect() inside the subquery), even with zero matches —
// a bare CALL{} that can return zero rows would drop the whole pipeline to nothing (Neo4j's per-row flatMap semantics).
CALL {
  MATCH (:Session)-[:VIEWED]->(p:PageView)
  WITH p.path AS path, count(p) AS views, sum(p.duration_seconds) AS total_seconds
  ORDER BY total_seconds DESC LIMIT 10
  RETURN collect({path: path, views: views, total_seconds: total_seconds,
                  avg_seconds: CASE WHEN views = 0 THEN 0.0 ELSE round(total_seconds * 1.0 / views, 1) END}) AS top_pages
}
CALL {
  MATCH (s:Session) WHERE s.landing_path IS NOT NULL
  WITH s.landing_path AS path, count(s) AS sessions
  ORDER BY sessions DESC LIMIT 10
  RETURN collect({path: path, sessions: sessions}) AS top_landing_pages
}
CALL {
  MATCH (s:Session)-[:VIEWED]->(p:PageView)
  WITH s, p ORDER BY p.entered_at DESC
  WITH s, collect(p)[0] AS last_view
  WITH last_view.path AS path, count(*) AS sessions
  ORDER BY sessions DESC LIMIT 10
  RETURN collect({path: path, sessions: sessions}) AS top_exit_pages
}
CALL {
  MATCH (s:Session)
  WITH (CASE WHEN s.referrer IS NULL OR s.referrer = '' THEN 'Direct' ELSE s.referrer END) AS referrer
  WITH referrer, count(*) AS sessions
  ORDER BY sessions DESC LIMIT 10
  RETURN collect({referrer: referrer, sessions: sessions}) AS top_referrers
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
  MATCH (v:Visitor)-[:HAD_SESSION]->(s:Session) WHERE s.started_at >= $range_start
  WITH substring(s.started_at, 0, 10) AS day, (substring(v.first_seen, 0, 10) = substring(s.started_at, 0, 10)) AS is_new
  WITH day, sum(CASE WHEN is_new THEN 1 ELSE 0 END) AS new_sessions,
            sum(CASE WHEN NOT is_new THEN 1 ELSE 0 END) AS returning_sessions, count(*) AS sessions
  ORDER BY day
  RETURN collect({date: day, new_sessions: new_sessions, returning_sessions: returning_sessions, sessions: sessions}) AS visits_by_day
}
CALL {
  MATCH (s:Session) WHERE s.started_at >= $range_start
  WITH datetime(s.started_at).hour AS hour, count(s) AS sessions
  ORDER BY hour
  RETURN collect({hour: hour, sessions: sessions}) AS by_hour
}
CALL {
  MATCH (s:Session) WHERE s.started_at >= $range_start
  WITH datetime(s.started_at).dayOfWeek AS weekday, count(s) AS sessions
  ORDER BY weekday
  RETURN collect({weekday: weekday, sessions: sessions}) AS by_weekday
}
CALL {
  MATCH (:Session)-[:DID]->(i:Interaction {name: 'click'}) WHERE i.label IS NOT NULL
  WITH i.label AS label, count(i) AS clicks
  ORDER BY clicks DESC LIMIT 15
  RETURN collect({label: label, clicks: clicks}) AS top_clicks
}
CALL {
  MATCH (s:Session)-[:VIEWED]->(:PageView {path: '#/'})
  RETURN count(DISTINCT s) AS home_sessions
}
CALL {
  MATCH (s:Session)-[:DID]->(i:Interaction {name: 'scroll_depth'})
  WITH i.label AS depth, count(DISTINCT s) AS sessions
  ORDER BY toInteger(depth)
  RETURN collect({depth: toInteger(depth), sessions: sessions}) AS scroll_depth
}
CALL {
  MATCH (:Session)-[:DID]->(i:Interaction {name: 'pi_query'}) WHERE i.label IS NOT NULL
  WITH toLower(trim(i.label)) AS question, count(i) AS asked
  ORDER BY asked DESC LIMIT 10
  RETURN collect({question: question, asked: asked}) AS top_questions
}
CALL {
  MATCH (s:Session)-[:DID]->(i:Interaction {name: 'pi_query'}) WHERE i.label IS NOT NULL
  WITH i, s ORDER BY i.at DESC LIMIT 15
  RETURN collect({question: i.label, at: i.at, country: s.country, city: s.city}) AS recent_questions
}
CALL {
  MATCH (s:Session)-[:DID]->(:Interaction {name: 'order_placed'})
  RETURN count(DISTINCT s) AS converting_sessions
}
CALL { MATCH (:Session)-[:DID]->(i:Interaction {name: 'order_placed'}) RETURN count(i) AS orders_from_sessions }
RETURN total_visitors, total_sessions, visitors_today, sessions_today, new_visitors, returning_visitors,
       avg_session_seconds, bounced_sessions, bounce_total_sessions, bounce_rate_pct,
       top_pages, top_landing_pages, top_exit_pages, top_referrers, top_countries, device_breakdown,
       visits_by_day, by_hour, by_weekday,
       top_clicks, home_sessions, scroll_depth, top_questions, recent_questions,
       converting_sessions, orders_from_sessions
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
    total = d["total_sessions"]
    d["conversion_rate_pct"] = round(100.0 * d["converting_sessions"] / total, 1) if total else 0.0
    return d


def get_recent_sessions(session, limit: int = 50) -> List[Dict[str, Any]]:
    rows = session.run(
        """
        MATCH (v:Visitor)-[:HAD_SESSION]->(s:Session)
        OPTIONAL MATCH (s)-[:VIEWED]->(p:PageView)
        WITH v, s, count(p) AS pages, sum(p.duration_seconds) AS total_seconds
        RETURN s.session_id AS session_id, v.visitor_id AS visitor_id, s.started_at AS started_at,
               s.ip AS ip, s.country AS country, s.region AS region, s.city AS city,
               s.device_type AS device_type, s.browser AS browser, s.os AS os,
               s.referrer AS referrer, s.landing_path AS landing_path,
               v.visit_count AS visitor_visit_count, pages, coalesce(total_seconds, 0) AS total_seconds
        ORDER BY s.started_at DESC LIMIT $limit
        """,
        limit=limit,
    ).data()
    return rows
