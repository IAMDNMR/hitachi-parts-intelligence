"""
backend/tests/conftest.py

Shared pytest fixtures for Neo4j integration tests.

Strategy:
  - Each test gets a unique testRunId (UUID).
  - All test-created Neo4j nodes are tagged with testRunId.
  - A function-scoped teardown fixture deletes all nodes tagged with that
    testRunId after the test completes.
  - Tests use the real AuraDB — no SQLite fallback.

Session scope:
  - neo4j_driver  — session-scoped (one driver per test run)
  - neo4j_session — function-scoped (fresh session per test)
  - test_run_id   — function-scoped (fresh UUID per test)
"""

import uuid
import os
import pytest

from neo4j import GraphDatabase

# Load backend .env so NEO4J_* variables are available
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(_env_path, override=True)

from app.config import settings


# ---------------------------------------------------------------------------
# Driver — one per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def neo4j_driver():
    """Create and verify one Neo4j driver for the entire test session."""
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    driver.verify_connectivity()
    yield driver
    driver.close()


# ---------------------------------------------------------------------------
# Test-run isolation ID — unique per test function
# ---------------------------------------------------------------------------

@pytest.fixture
def test_run_id():
    """Return a unique string that tags all nodes created by this test."""
    return f"TEST_{uuid.uuid4().hex}"


# ---------------------------------------------------------------------------
# Neo4j session — one per test function, with automatic cleanup
# ---------------------------------------------------------------------------

@pytest.fixture
def neo4j_session(neo4j_driver, test_run_id):
    """
    Yield a Neo4j session for the test.

    After the test (pass or fail), delete all nodes tagged with
    testRunId = test_run_id.
    """
    db = settings.NEO4J_DATABASE or None
    session_kwargs = {}
    if db:
        session_kwargs["database"] = db

    with neo4j_driver.session(**session_kwargs) as session:
        yield session

    # Teardown: clean up test data
    with neo4j_driver.session(**session_kwargs) as cleanup_session:
        cleanup_session.run(
            "MATCH (n) WHERE n.testRunId = $run DETACH DELETE n",
            {"run": test_run_id},
        ).consume()


# ---------------------------------------------------------------------------
# Gemini free-tier budget — reset between tests
# ---------------------------------------------------------------------------
#
# _GeminiBudget is process-wide global state meant to protect the real
# free-tier quota across the lifetime of one running backend process. Inside
# a single pytest run, dozens of tests construct GeminiLLMProvider with a
# fake key; acquire() consumes a budget slot before the (mocked) HTTP call
# even happens, so the shared window fills up and unrelated later tests see
# a spurious fallback to the deterministic path. Reset it before every test
# so each test's assertions depend only on its own mocking, not on test order.

@pytest.fixture(autouse=True)
def _reset_gemini_budget():
    from app.modules.intelligence import providers

    providers._BUDGETS.clear()
    yield
    providers._BUDGETS.clear()


@pytest.fixture(autouse=True)
def _no_real_gemini_by_default(monkeypatch):
    """A real GEMINI_API_KEY may be present in backend/.env for manual
    smoke testing, but the automated suite must never make a real network
    call to Gemini. Default every test to the deterministic path; tests
    that specifically exercise GeminiLLMProvider override this and mock
    the HTTP call."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "", raising=False)


# ---------------------------------------------------------------------------
# API-level test isolation (Phase 10B/10D)
# ---------------------------------------------------------------------------
#
# Tests that drive the FastAPI routes through TestClient used to create
# untagged Orders / FulfilmentRequests / Shipments in the live database
# (only routes with an explicit testRunId argument were cleaned up). This
# autouse fixture tags EVERY TestClient request of a test with that test's
# testRunId — as the `x-test-run-id` header (order/fulfilment/availability/
# allocation routes) and the `test_run_id` query param (shipment/service
# routes) — and deletes everything so tagged when the test ends, whether or
# not the test asked for neo4j_session. Extra query params are ignored by
# routes that do not declare them.

@pytest.fixture(autouse=True)
def _isolate_api_writes(test_run_id, neo4j_driver, monkeypatch):
    from starlette.testclient import TestClient

    original = TestClient.request

    def tagged(self, method, url, *args, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        headers.setdefault("x-test-run-id", test_run_id)
        kwargs["headers"] = headers
        if method.upper() != "GET":
            params = dict(kwargs.get("params") or {})
            params.setdefault("test_run_id", test_run_id)
            kwargs["params"] = params
        return original(self, method, url, *args, **kwargs)

    monkeypatch.setattr(TestClient, "request", tagged)
    yield
    kwargs = {"database": settings.NEO4J_DATABASE} if settings.NEO4J_DATABASE else {}
    with neo4j_driver.session(**kwargs) as s:
        s.run("MATCH (n) WHERE n.testRunId = $run DETACH DELETE n", {"run": test_run_id}).consume()
        # deleted test allocations must give their stock back, or the demo depot stock is used up by test runs
        from app.modules.allocation.ledger import recompute_ledger_totals
        recompute_ledger_totals(s)
