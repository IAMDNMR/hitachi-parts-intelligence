"""
backend/app/db/neo4j/connection.py

Neo4j driver singleton and session factory.

This replaces the old SQLAlchemy session.py.  Neo4j is the sole runtime
database — there is no SQLite fallback.

Usage (FastAPI dependency injection):
    from app.db.neo4j.connection import get_neo4j_session

    @router.get("/foo")
    def my_route(session = Depends(get_neo4j_session)):
        result = session.run("RETURN 1 AS val")
        ...
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional, Any, Dict

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.config import settings
from app.logging_config.logger import logger

# ---------------------------------------------------------------------------
# Driver singleton
# ---------------------------------------------------------------------------

_driver: Optional[Driver] = None


def _build_driver() -> Driver:
    """Create and return a verified Neo4j driver."""
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        # Explicit pool tuning (was left at library defaults). Bounding pool
        # size avoids unbounded connection growth under concurrent load, and
        # a finite acquisition timeout fails fast instead of hanging forever
        # if the pool is exhausted. max_connection_lifetime recycles
        # connections periodically so a long-lived process (e.g. a full
        # pytest session sharing one driver across ~70 tests) doesn't keep
        # handing out a connection that AuraDB has quietly gone stale on.
        max_connection_pool_size=50,
        connection_acquisition_timeout=60,
        max_connection_lifetime=3600,
    )
    # Verify connectivity immediately — fail fast rather than degrade silently.
    driver.verify_connectivity()
    return driver


def get_neo4j_driver() -> Driver:
    """Return the process-level Neo4j driver, initialising it on first call."""
    global _driver
    if _driver is None:
        logger.info(f"Initialising Neo4j driver → {settings.NEO4J_URI}")
        _driver = _build_driver()
        logger.info("Neo4j driver initialised and connectivity verified.")
    return _driver


# Convenience alias used by the singleton import pattern
neo4j_driver_instance = get_neo4j_driver


def close_driver() -> None:
    """Close the driver (called on application shutdown)."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed.")


# ---------------------------------------------------------------------------
# Session factory — FastAPI dependency
# ---------------------------------------------------------------------------

def get_neo4j_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency: yields a Neo4j driver session.

    Each request gets its own session.  The session is closed automatically
    after the request completes (success or exception).
    """
    driver = get_neo4j_driver()
    db = getattr(settings, "NEO4J_DATABASE", None) or None
    session_kwargs: Dict[str, Any] = {}
    if db:
        session_kwargs["database"] = db
    with driver.session(**session_kwargs) as session:
        yield session


# ---------------------------------------------------------------------------
# Context-manager helper (for non-FastAPI callers, e.g. tests, services)
# ---------------------------------------------------------------------------

@contextmanager
def neo4j_transaction() -> Generator[Session, None, None]:
    """
    Context manager that wraps a Neo4j session.

    Equivalent to the old SQLAlchemy ``with_db_transaction()`` pattern.
    Callers use ``session.execute_write(...)`` or ``session.run(...)`` inside.

    Example::

        with neo4j_transaction() as session:
            session.run("CREATE (n:Foo {id: $id})", id="x")
    """
    driver = get_neo4j_driver()
    db = getattr(settings, "NEO4J_DATABASE", None) or None
    session_kwargs: Dict[str, Any] = {}
    if db:
        session_kwargs["database"] = db
    with driver.session(**session_kwargs) as session:
        yield session


# ---------------------------------------------------------------------------
# Health check helper
# ---------------------------------------------------------------------------

def check_neo4j_health() -> Dict[str, Any]:
    """Return a health dict for the /readiness endpoint."""
    try:
        driver = get_neo4j_driver()
        db = getattr(settings, "NEO4J_DATABASE", None) or None
        session_kwargs: Dict[str, Any] = {}
        if db:
            session_kwargs["database"] = db
        with driver.session(**session_kwargs) as session:
            session.run("RETURN 1").consume()
        return {"status": "CONNECTED", "connected": True}
    except (ServiceUnavailable, AuthError, Exception) as e:
        logger.warning(f"Neo4j health check failed: {e}")
        return {"status": f"DISCONNECTED: {e}", "connected": False}
