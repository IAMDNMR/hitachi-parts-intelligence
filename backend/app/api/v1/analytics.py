"""
backend/app/api/v1/analytics.py

- POST /analytics/event  — public. The frontend calls this only after the visitor accepts the cookie banner.
- POST /analytics/login  — public. One shared admin password (ANALYTICS_ADMIN_PASSWORD); issues a JWT.
- GET  /analytics/summary, /analytics/sessions — protected (role ANALYTICS_ADMIN).
"""

from typing import Any, Dict, Optional

import jwt
from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel

from app.config import settings
from app.db.neo4j.connection import get_neo4j_session
from app.errors.exceptions import ForbiddenError, UnauthorizedError
from app.modules.analytics import service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _client_ip(request: Request) -> Optional[str]:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


class DeviceInfo(BaseModel):
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    screen_w: Optional[int] = None
    screen_h: Optional[int] = None
    language: Optional[str] = None
    timezone: Optional[str] = None


class TrackEvent(BaseModel):
    type: str  # "session_start" | "pageview" | "duration"
    visitor_id: str
    session_id: str
    pageview_id: Optional[str] = None
    path: Optional[str] = None
    referrer: Optional[str] = None
    landing_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    device: Optional[DeviceInfo] = None


@router.post("/event")
def track_event(dto: TrackEvent, request: Request, test_run_id: Optional[str] = Query(None),
                session=Depends(get_neo4j_session)) -> Dict[str, bool]:
    if dto.type == "session_start":
        service.record_session_start(
            session, dto.visitor_id, dto.session_id, _client_ip(request),
            dto.referrer, dto.landing_path, (dto.device or DeviceInfo()).model_dump(),
            test_run_id=test_run_id,
        )
    elif dto.type == "pageview":
        service.record_pageview(session, dto.session_id, dto.pageview_id, dto.path, test_run_id=test_run_id)
    elif dto.type == "duration":
        service.record_duration(session, dto.pageview_id, dto.duration_seconds or 0)
    else:
        return {"ok": False}
    return {"ok": True}


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login(dto: LoginRequest) -> Dict[str, str]:
    service.check_admin_password(dto.password, settings.ANALYTICS_ADMIN_PASSWORD)
    token = jwt.encode({"sub": "analytics-admin", "role": "ANALYTICS_ADMIN"}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"token": token}


def _require_analytics_admin(authorization: Optional[str] = Header(None)) -> None:
    if not authorization:
        raise UnauthorizedError("Sign in to view analytics")
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except Exception as e:
        raise UnauthorizedError(f"Invalid or expired session: {e}")
    if payload.get("role") != "ANALYTICS_ADMIN":
        raise ForbiddenError("Not authorised to view analytics")


@router.get("/summary")
def summary(days: int = 30, session=Depends(get_neo4j_session), _=Depends(_require_analytics_admin)) -> Dict[str, Any]:
    return service.get_summary(session, days=days)


@router.get("/sessions")
def sessions(limit: int = 50, session=Depends(get_neo4j_session), _=Depends(_require_analytics_admin)) -> Dict[str, Any]:
    return {"sessions": service.get_recent_sessions(session, limit=limit)}
