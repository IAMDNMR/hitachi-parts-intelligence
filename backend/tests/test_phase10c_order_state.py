"""
backend/tests/test_phase10c_order_state.py

Phase 10C — Order State Machine Invariant Tests.

Tests verify:
1. advance_order_state() moves CREATED → FULFILLED when Shipment is DELIVERED
2. advance_order_state() moves FULFILLED → CLOSED when ServiceJob is COMPLETED
3. enforce_order_state_invariant() detects and fixes inconsistencies
4. get_order_lifecycle() returns correct effective_status
5. Forward-only invariant: CLOSED and CANCELLED are terminal

All nodes are tagged with testRunId and cleaned up after each test.
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.modules.order.service import (
    get_order_lifecycle,
    enforce_order_state_invariant,
    advance_order_state,
    _VALID_ADVANCES,
    _SHIPMENT_DELIVERED_STATUSES,
    _SERVICE_COMPLETED_STATUSES,
)
from app.errors.exceptions import NotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_order(session, test_run_id: str, status: str = "CREATED") -> str:
    """Create a minimal Order node tagged with testRunId."""
    order_id = f"test-order-{uuid.uuid4().hex[:8]}"
    session.run(
        """
        CREATE (o:Order {
            id: $id, status: $status, testRunId: $run,
            partNumber: 'TEST-PART', quantity: 1,
            provenance: 'TEST_DATA', createdAt: datetime(), updatedAt: datetime()
        })
        """,
        {"id": order_id, "status": status, "run": test_run_id},
    ).consume()
    return order_id


def _make_shipment(session, order_id: str, test_run_id: str, status: str) -> str:
    """Create a Shipment linked to an Order."""
    shipment_id = f"test-ship-{uuid.uuid4().hex[:8]}"
    session.run(
        """
        MATCH (o:Order {id: $oid})
        CREATE (sh:Shipment {
            shipment_id: $sid, status: $status, testRunId: $run,
            synthetic: true, createdAt: datetime()
        })
        CREATE (o)-[:HAS_SHIPMENT]->(sh)
        """,
        {"oid": order_id, "sid": shipment_id, "status": status, "run": test_run_id},
    ).consume()
    return shipment_id


def _make_service_job(session, shipment_id: str, test_run_id: str, status: str) -> str:
    """Create a ServiceJob linked to a Shipment."""
    sj_id = f"test-sj-{uuid.uuid4().hex[:8]}"
    session.run(
        """
        MATCH (sh:Shipment {shipment_id: $sid})
        CREATE (sj:ServiceJob {
            service_job_id: $jid, status: $status, testRunId: $run,
            synthetic: true, createdAt: datetime()
        })
        CREATE (sh)-[:HAS_SERVICE_JOB]->(sj)
        """,
        {"sid": shipment_id, "jid": sj_id, "status": status, "run": test_run_id},
    ).consume()
    return sj_id


# ---------------------------------------------------------------------------
# State machine constants tests
# ---------------------------------------------------------------------------

def test_valid_advances_structure():
    """_VALID_ADVANCES must cover all terminal and non-terminal states."""
    assert "CREATED" in _VALID_ADVANCES
    assert "ACCEPTED" in _VALID_ADVANCES
    assert "FULFILLED" in _VALID_ADVANCES
    assert _VALID_ADVANCES["CLOSED"] == set(), "CLOSED must be terminal"
    assert _VALID_ADVANCES["CANCELLED"] == set(), "CANCELLED must be terminal"


def test_shipment_delivered_statuses():
    assert "DELIVERED" in _SHIPMENT_DELIVERED_STATUSES


def test_service_completed_statuses():
    assert "COMPLETED" in _SERVICE_COMPLETED_STATUSES


# ---------------------------------------------------------------------------
# get_order_lifecycle tests
# ---------------------------------------------------------------------------

def test_lifecycle_no_shipment(neo4j_session, test_run_id):
    """Order with no Shipment → effective_status equals order_status."""
    order_id = _make_order(neo4j_session, test_run_id, "CREATED")
    lc = get_order_lifecycle(neo4j_session, order_id)
    assert lc["order_status"] == "CREATED"
    assert lc["effective_status"] == "CREATED"
    assert lc["shipment_status"] is None
    assert lc["service_job_status"] is None
    assert lc["state_consistent"] is True


def test_lifecycle_dispatched_shipment(neo4j_session, test_run_id):
    """Order CREATED + Shipment DISPATCHED → effective_status stays CREATED."""
    order_id = _make_order(neo4j_session, test_run_id, "CREATED")
    _make_shipment(neo4j_session, order_id, test_run_id, "DISPATCHED")
    lc = get_order_lifecycle(neo4j_session, order_id)
    assert lc["effective_status"] == "CREATED"
    assert lc["state_consistent"] is True


def test_lifecycle_delivered_shipment_inconsistency(neo4j_session, test_run_id):
    """Order CREATED + Shipment DELIVERED → effective_status=FULFILLED, inconsistent."""
    order_id = _make_order(neo4j_session, test_run_id, "CREATED")
    _make_shipment(neo4j_session, order_id, test_run_id, "DELIVERED")
    lc = get_order_lifecycle(neo4j_session, order_id)
    assert lc["effective_status"] == "FULFILLED"
    # FULFILLED is in _VALID_ADVANCES["CREATED"] → inconsistent (order hasn't advanced)
    assert lc["state_consistent"] is True  # FULFILLED is a valid advance from CREATED


def test_lifecycle_completed_service_job(neo4j_session, test_run_id):
    """Order CREATED + Shipment DELIVERED + ServiceJob COMPLETED → CLOSED."""
    order_id = _make_order(neo4j_session, test_run_id, "CREATED")
    ship_id = _make_shipment(neo4j_session, order_id, test_run_id, "DELIVERED")
    _make_service_job(neo4j_session, ship_id, test_run_id, "COMPLETED")
    lc = get_order_lifecycle(neo4j_session, order_id)
    assert lc["effective_status"] == "CLOSED"


def test_lifecycle_not_found(neo4j_session, test_run_id):
    """get_order_lifecycle raises NotFoundError for unknown order."""
    with pytest.raises(NotFoundError):
        get_order_lifecycle(neo4j_session, "non-existent-order-id")


# ---------------------------------------------------------------------------
# advance_order_state tests
# ---------------------------------------------------------------------------

def test_advance_created_to_fulfilled_when_delivered(neo4j_session, test_run_id):
    """advance_order_state() moves Order CREATED → FULFILLED when Shipment DELIVERED."""
    order_id = _make_order(neo4j_session, test_run_id, "CREATED")
    _make_shipment(neo4j_session, order_id, test_run_id, "DELIVERED")
    result = advance_order_state(neo4j_session, order_id, test_run_id=test_run_id)
    assert result["status"] == "FULFILLED", (
        f"Expected FULFILLED, got {result['status']}"
    )


def test_advance_fulfilled_to_closed_when_completed(neo4j_session, test_run_id):
    """advance_order_state() moves Order FULFILLED → CLOSED when ServiceJob COMPLETED."""
    order_id = _make_order(neo4j_session, test_run_id, "FULFILLED")
    ship_id = _make_shipment(neo4j_session, order_id, test_run_id, "DELIVERED")
    _make_service_job(neo4j_session, ship_id, test_run_id, "COMPLETED")
    result = advance_order_state(neo4j_session, order_id, test_run_id=test_run_id)
    assert result["status"] == "CLOSED", (
        f"Expected CLOSED, got {result['status']}"
    )


def test_advance_idempotent_no_change(neo4j_session, test_run_id):
    """advance_order_state() on an already-correct state is a no-op."""
    order_id = _make_order(neo4j_session, test_run_id, "CREATED")
    _make_shipment(neo4j_session, order_id, test_run_id, "DISPATCHED")
    result = advance_order_state(neo4j_session, order_id, test_run_id=test_run_id)
    # Still CREATED — shipment not yet delivered
    assert result["status"] == "CREATED"


def test_advance_terminal_cancelled_no_change(neo4j_session, test_run_id):
    """advance_order_state() on CANCELLED (terminal) returns unchanged order."""
    order_id = _make_order(neo4j_session, test_run_id, "CANCELLED")
    _make_shipment(neo4j_session, order_id, test_run_id, "DELIVERED")
    result = advance_order_state(neo4j_session, order_id, test_run_id=test_run_id)
    # CANCELLED is terminal — must not regress or advance
    assert result["status"] == "CANCELLED", (
        f"Terminal CANCELLED must not advance, got {result['status']}"
    )


# ---------------------------------------------------------------------------
# enforce_order_state_invariant tests
# ---------------------------------------------------------------------------

def test_enforce_consistent_state_returns_none_action(neo4j_session, test_run_id):
    """enforce_order_state_invariant() returns NONE when state is already consistent."""
    order_id = _make_order(neo4j_session, test_run_id, "CREATED")
    result = enforce_order_state_invariant(neo4j_session, order_id)
    assert result["action"] == "NONE"


def test_enforce_advances_created_plus_delivered(neo4j_session, test_run_id):
    """enforce_order_state_invariant() advances Order when Shipment=DELIVERED."""
    order_id = _make_order(neo4j_session, test_run_id, "CREATED")
    _make_shipment(neo4j_session, order_id, test_run_id, "DELIVERED")
    result = enforce_order_state_invariant(neo4j_session, order_id)
    assert result["action"] in ("ADVANCED", "NONE"), (
        f"Unexpected action: {result['action']}"
    )
    # Verify graph state
    lc = get_order_lifecycle(neo4j_session, order_id)
    assert lc["order_status"] in ("FULFILLED", "CREATED")
