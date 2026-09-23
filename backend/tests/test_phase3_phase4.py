"""
backend/tests/test_phase3_phase4.py

Phase 3 Backend Foundation + Phase 4 Availability Engine tests.

Database: Neo4j AuraDB (real instance, isolated per test via testRunId).
"""

import concurrent.futures
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.allocation.ledger import attempt_inventory_allocation
from app.modules.availability.service import check_availability
from app.integrations.contracts.inventory import SourceAvailabilityQuery, InventoryStatus
from app.integrations.mocks.inventory_mock import TestInventoryProvider
from app.db.neo4j.connection import get_neo4j_driver

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Phase 3 Backend Foundation Tests
# ---------------------------------------------------------------------------

def test_health_liveness():
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_health_readiness():
    response = client.get("/api/v1/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "database" in data
    assert "neo4j" in data


def test_correlation_id_propagation():
    custom_corr_id = "test-corr-12345"
    response = client.get(
        "/api/v1/health/liveness",
        headers={"X-Correlation-ID": custom_corr_id},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_corr_id


def test_quote_request_reconciliation(neo4j_session, test_run_id):
    # Migrated from the retired Node layer (frontend/api/quote-request.js) to
    # backend/app/api/v1/quote_request.py — see tests/test_parts_store_migration.py
    # for full coverage of this route's request/response and graph write shape.
    email = f"jan_{test_run_id}@example.nl"
    payload = {
        "name": "Jan de Vries",
        "email": email,
        "phone": "+31612345678",
        "note": "Urgent request for EX1200-7",
        "items": [
            {"partNumber": "4656429", "name": "Hydraulic Filter Element", "qty": 2}
        ],
    }
    response = client.post("/api/v1/quote-request", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "inquiryId" in data
    assert data["projectionStatus"] == "SUCCESS"

    # Tag the created nodes for cleanup (customer uses email as id)
    neo4j_session.run(
        """
        MATCH (n) WHERE n.email = $email OR n.id STARTS WITH 'inq-'
        SET n.testRunId = $run
        """,
        {"email": email, "run": test_run_id},
    ).consume()


def test_allocation_concurrency_lock(neo4j_session, test_run_id):
    """
    Exactly 1 item in ledger. 10 concurrent threads → 1 SUCCESS, 9 CONFLICTS.
    """
    part_num = f"CONCURRENCY-TEST-{test_run_id}"
    source_id = f"DEPOT-LOCK-{test_run_id}"
    ledger_id = f"{part_num}:{source_id}"

    # Pre-seed the ledger in one committed write
    neo4j_session.run(
        """
        MERGE (l:InventoryLedger {id: $ledger_id})
        ON CREATE SET
            l.partNumber        = $part_number,
            l.sourceId          = $source_id,
            l.totalAvailableQty = 1,
            l.totalAllocatedQty = 0,
            l.version           = 1,
            l.updatedAt         = datetime(),
            l.testRunId         = $run
        """,
        {
            "ledger_id": ledger_id,
            "part_number": part_num,
            "source_id": source_id,
            "run": test_run_id,
        },
    ).consume()

    driver = get_neo4j_driver()
    db = None
    from app.config import settings
    if settings.NEO4J_DATABASE:
        db = settings.NEO4J_DATABASE

    def run_allocation(index):
        session_kwargs = {}
        if db:
            session_kwargs["database"] = db
        with driver.session(**session_kwargs) as session:
            success, code, details = attempt_inventory_allocation(
                session=session,
                part_number=part_num,
                source_id=source_id,
                requested_qty=1,
                fulfilment_request_id=f"freq-conc-{test_run_id}-{index}",
                idempotency_key=f"idemp-conc-{test_run_id}-{index}",
                initial_stock_for_test=1,
                test_run_id=test_run_id,
            )
            return success

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_allocation, i) for i in range(10)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    success_count = results.count(True)
    fail_count = results.count(False)

    assert success_count == 1, f"Expected exactly 1 successful allocation, got {success_count}"
    assert fail_count == 9, f"Expected 9 failed allocations due to lock, got {fail_count}"


# ---------------------------------------------------------------------------
# 2. Phase 4 Availability Engine & BR-01 Discipline Tests
# ---------------------------------------------------------------------------

def test_availability_scenario_exact_stock(neo4j_session, test_run_id):
    res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="4656429",
        quantity=5,
        test_run_id=test_run_id,
    )
    assert res["overall_status"] == "AVAILABLE"
    assert res["total_available_qty"] >= 5
    assert len(res["sources"]) > 0


def test_availability_scenario_stale_inventory_br01(neo4j_session, test_run_id):
    """BR-01: Stale inventory (>3600s) → status UNKNOWN, never 0 or UNAVAILABLE."""
    res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="TEST-STALE",
        quantity=2,
        test_run_id=test_run_id,
    )
    assert res["overall_status"] == "UNKNOWN"
    stale_source = res["sources"][0]
    assert stale_source["status"] == "UNKNOWN"
    assert stale_source["is_stale"] is True


def test_availability_scenario_exceeds_quantity_partial(neo4j_session, test_run_id):
    res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="TEST-PARTIAL",
        quantity=10,
        test_run_id=test_run_id,
    )
    assert res["overall_status"] == "PARTIAL"
    assert res["total_available_qty"] == 3


def test_availability_scenario_reman_alternative(neo4j_session, test_run_id):
    res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="TEST-REMAN",
        quantity=2,
        test_run_id=test_run_id,
    )
    assert res["reman_alternative_available"] is True
    assert res["sources"][0]["source_type"] == "REMAN_FACILITY"


def test_availability_api_endpoint():
    payload = {
        "part_number": "4656429",
        "quantity": 1,
        "destination_branch_id": "DEALER-BRANCH-NL-01",
    }
    response = client.post("/api/v1/fulfilment-requests/new/availability", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "fulfilment_request_id" in data
    assert data["overall_status"] in ["AVAILABLE", "UNKNOWN"]
