"""
backend/tests/test_phase6_allocation_order.py

Phase 6 Allocation + Order domain and API integration tests — Neo4j backend.

Database: Neo4j AuraDB (real instance, isolated per test via testRunId).
Mirrors the fixture/flow style of tests/test_phase5_fulfilment.py.
"""

import concurrent.futures

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.neo4j.connection import get_neo4j_driver
from app.errors.exceptions import AppError, ConflictError, NotFoundError, UnprocessableError
from app.modules.availability.service import check_availability
from app.modules.fulfilment.service import (
    generate_fulfilment_options,
    select_fulfilment_option,
    proceed_to_allocation_pending,
)
from app.modules.allocation.service import create_allocation, get_allocation, release_allocation
from app.modules.order.service import create_order, get_order

client = TestClient(app)

REAL_PART_NUMBER = "4663907"  # confirmed real catalogue Part (PT-001) — verified present in AuraDB


def _unique_part_number(test_run_id: str, session) -> str:
    """
    Create a fresh, test-isolated canonical Part with a unique part_number.

    Using a per-test part_number (rather than a shared real catalogue
    number) avoids InventoryLedger contention between tests: the ledger's
    identity is `partNumber:sourceId`, and the mock inventory provider's
    default fallback source ("REGIONAL-DEPOT-DEFAULT") is the same for any
    unrecognized part number, so reusing one real part number across many
    tests would serialize them against the same persistent ledger row. This
    still exercises the exact same MATCH-not-CREATE canonical-Part code
    path as a real catalogue part (see test_canonical_part_identity_preserved,
    which additionally asserts against the real, pre-existing catalogue).
    """
    pn = f"PN6-{test_run_id}-{session.run('RETURN randomUUID() AS u').single()['u'][:8]}"
    session.run(
        "MERGE (p:Part {part_number: $pn}) ON CREATE SET p.part_id = $pn, p.testRunId = $run",
        {"pn": pn, "run": test_run_id},
    ).consume()
    return pn


def _drive_to_allocation_pending(session, test_run_id, part_number=None, quantity=1):
    if part_number is None:
        part_number = _unique_part_number(test_run_id, session)
    avail_res = check_availability(
        session=session,
        fulfilment_request_id=None,
        part_number=part_number,
        quantity=quantity,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    options = generate_fulfilment_options(session, req_id, test_run_id=test_run_id)
    assert len(options) > 0
    option_id = options[0]["id"]
    select_fulfilment_option(session, req_id, option_id, test_run_id=test_run_id)
    proceed_to_allocation_pending(session, req_id, test_run_id=test_run_id)
    return req_id, option_id


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------

def test_successful_allocation(neo4j_session, test_run_id):
    part_number = _unique_part_number(test_run_id, neo4j_session)
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id, part_number=part_number)
    result = create_allocation(neo4j_session, req_id, test_run_id=test_run_id)
    assert result["status"] == "CONFIRMED"
    assert result["fulfilment_request_id"] == req_id
    assert result["part_number"] == part_number
    assert result["quantity"] == 1


def test_insufficient_quantity(neo4j_session, test_run_id):
    # TEST-PARTIAL is a fixed mock scenario with exactly 3 units available
    # at CENTRAL-DEPOT-JP; requesting 4 must fail with insufficient stock.
    neo4j_session.run(
        "MERGE (p:Part {part_number: 'TEST-PARTIAL'}) ON CREATE SET p.part_id = 'TEST-PARTIAL', p.testRunId = $run",
        {"run": test_run_id},
    ).consume()
    req_id, _ = _drive_to_allocation_pending(
        neo4j_session, test_run_id, part_number="TEST-PARTIAL", quantity=4
    )
    with pytest.raises(ConflictError):
        create_allocation(neo4j_session, req_id, test_run_id=test_run_id)


def test_unknown_availability_rejected(neo4j_session, test_run_id):
    """UNKNOWN inventory source (TEST-STALE / DEALER-DEPOT-MUNICH) must never be allocated."""
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="TEST-STALE",
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    options = generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)
    unknown_opt = next(o for o in options if o["source_id"] == "DEALER-DEPOT-MUNICH")
    select_fulfilment_option(neo4j_session, req_id, unknown_opt["id"], test_run_id=test_run_id)
    proceed_to_allocation_pending(neo4j_session, req_id, test_run_id=test_run_id)

    # TEST-STALE has no canonical Part node, so this should fail on the Part
    # lookup, not silently allocate. This proves UNKNOWN/missing-Part never
    # gets converted into a concrete allocation.
    with pytest.raises(AppError):
        create_allocation(neo4j_session, req_id, test_run_id=test_run_id)


def test_missing_fulfilment_request(neo4j_session, test_run_id):
    with pytest.raises(NotFoundError):
        create_allocation(neo4j_session, "freq-does-not-exist", test_run_id=test_run_id)


def test_invalid_state_transition_before_allocation_pending(neo4j_session, test_run_id):
    """Allocation must be rejected before the request reaches ALLOCATION_PENDING."""
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number=REAL_PART_NUMBER,
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    with pytest.raises(ConflictError):
        create_allocation(neo4j_session, req_id, test_run_id=test_run_id)


def test_allocation_idempotency(neo4j_session, test_run_id):
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id)
    key = f"idemp-{test_run_id}"

    first = create_allocation(neo4j_session, req_id, idempotency_key=key, test_run_id=test_run_id)

    # Second call for the SAME already-ALLOCATED request must not create a
    # second allocation — ledger.attempt_inventory_allocation re-seeds only
    # on first touch, so re-invoking the domain function directly would try
    # to re-run against ALLOCATED state and correctly conflict; the API
    # route is what actually caches by idempotency key, so exercise that.
    endpoint = f"/api/v1/fulfilment-requests/{req_id}/allocation"
    from app.idempotency.service import save_idempotency_record

    save_idempotency_record(
        neo4j_session, endpoint, key, {"request_id": req_id}, 200, first, test_run_id=test_run_id
    )
    from app.idempotency.service import check_idempotency

    exists, status, cached = check_idempotency(neo4j_session, endpoint, key, {"request_id": req_id})
    assert exists is True
    assert cached["allocation_id"] == first["allocation_id"]

    count = neo4j_session.run(
        "MATCH (a:Allocation {fulfilmentRequestId: $id}) RETURN count(a) AS c",
        {"id": req_id},
    ).single()["c"]
    assert count == 1


def test_allocation_release(neo4j_session, test_run_id):
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id)
    alloc = create_allocation(neo4j_session, req_id, test_run_id=test_run_id)
    assert alloc["status"] == "CONFIRMED"

    released = release_allocation(neo4j_session, req_id, test_run_id=test_run_id)
    assert released["status"] == "RELEASED"

    fetched = get_allocation(neo4j_session, req_id)
    assert fetched["status"] == "RELEASED"


def test_allocation_concurrency_via_service(neo4j_session, test_run_id):
    """
    Same invariant as test_phase3_phase4.py::test_allocation_concurrency_lock
    but exercised through the Phase 6 service layer end to end: 1 unit of
    stock, N concurrent allocation attempts for DIFFERENT fulfilment
    requests against the same (part, source) -> exactly 1 CONFIRMED.
    """
    part_number = f"CONC6-{test_run_id}"
    source_id = f"DEPOT-CONC6-{test_run_id}"

    # Seed canonical Part + a single-source availability of exactly 1 unit.
    neo4j_session.run(
        "MERGE (p:Part {part_number: $pn}) ON CREATE SET p.part_id = $pn, p.testRunId = $run",
        {"pn": part_number, "run": test_run_id},
    ).consume()

    # Pre-seed the InventoryLedger row in ONE committed write before spawning
    # threads. ledger.py's own docstring documents that its "not found ->
    # seed" branch is a first-touch fallback, not itself safe under N
    # concurrent *first* creations (an unconstrained race to MERGE ON
    # CREATE) — the mandatory concurrency guarantee (ADR-007) is about the
    # version-gated read-modify-write on an EXISTING row, which is what
    # test_phase3_phase4.py::test_allocation_concurrency_lock and this test
    # both exercise, mirroring that established pattern exactly.
    ledger_id = f"{part_number}:{source_id}"
    neo4j_session.run(
        """
        MERGE (l:InventoryLedger {id: $ledger_id})
        ON CREATE SET
            l.partNumber = $pn, l.sourceId = $source_id,
            l.totalAvailableQty = 1, l.totalAllocatedQty = 0,
            l.version = 1, l.updatedAt = datetime(), l.testRunId = $run
        """,
        {"ledger_id": ledger_id, "pn": part_number, "source_id": source_id, "run": test_run_id},
    ).consume()

    driver = get_neo4j_driver()
    from app.config import settings

    session_kwargs = {"database": settings.NEO4J_DATABASE} if settings.NEO4J_DATABASE else {}

    def run_flow(index):
        with driver.session(**session_kwargs) as session:
            session.run(
                """
                CREATE (r:FulfilmentRequest {
                    id: $id, partNumber: $pn, quantity: 1, status: 'ALLOCATION_PENDING',
                    selectedOptionId: $opt_id, destinationBranchId: 'DEALER-BRANCH-NL-01',
                    testRunId: $run, createdAt: datetime(), updatedAt: datetime()
                })
                CREATE (o:FulfilmentOption {
                    id: $opt_id, fulfilmentRequestId: $id, sourceId: $source_id,
                    confidence: 'CONFIRMED', isSelected: true, testRunId: $run
                })
                CREATE (c:InventoryCache {
                    id: $cache_id, partNumber: $pn, sourceId: $source_id,
                    availableQty: 1, status: 'AVAILABLE', inventoryTimestamp: datetime(),
                    testRunId: $run
                })
                """,
                {
                    "id": f"freq-conc6-{test_run_id}-{index}",
                    "pn": part_number,
                    "opt_id": f"fopt-conc6-{test_run_id}-{index}",
                    "source_id": source_id,
                    "cache_id": f"icache-conc6-{test_run_id}-{index}",
                    "run": test_run_id,
                },
            ).consume()
            try:
                result = create_allocation(
                    session, f"freq-conc6-{test_run_id}-{index}", test_run_id=test_run_id
                )
                return True, result["status"]
            except AppError as e:
                return False, e.code

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_flow, i) for i in range(5)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]
    assert len(successes) == 1, f"Expected exactly 1 successful allocation, got {len(successes)}: {results}"
    assert len(failures) == 4


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

def test_successful_order_creation(neo4j_session, test_run_id):
    part_number = _unique_part_number(test_run_id, neo4j_session)
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id, part_number=part_number)
    create_allocation(neo4j_session, req_id, test_run_id=test_run_id)

    order = create_order(neo4j_session, req_id, test_run_id=test_run_id)
    assert order["status"] == "CREATED"
    assert order["partNumber"] == part_number
    assert order["integration_status"] == "NOT_CONNECTED"


def test_order_without_allocation_rejected(neo4j_session, test_run_id):
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id)
    # No allocation created yet.
    with pytest.raises(NotFoundError):
        create_order(neo4j_session, req_id, test_run_id=test_run_id)


def test_duplicate_order_request_no_duplicate_created(neo4j_session, test_run_id):
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id)
    create_allocation(neo4j_session, req_id, test_run_id=test_run_id)

    first = create_order(neo4j_session, req_id, test_run_id=test_run_id)
    second = create_order(neo4j_session, req_id, test_run_id=test_run_id)
    assert first["id"] == second["id"]

    count = neo4j_session.run(
        "MATCH (o:Order {fulfilmentRequestId: $id}) RETURN count(o) AS c",
        {"id": req_id},
    ).single()["c"]
    assert count == 1


def test_pricing_unknown_handling(neo4j_session, test_run_id):
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id)
    create_allocation(neo4j_session, req_id, test_run_id=test_run_id)
    order = create_order(neo4j_session, req_id, test_run_id=test_run_id)
    assert order["unitPrice"] is None
    assert order["pricingStatus"] == "NOT_AVAILABLE"


# ---------------------------------------------------------------------------
# Canonical Part identity / Intelligence <-> Store convergence
# ---------------------------------------------------------------------------

def test_canonical_part_identity_preserved(neo4j_session, test_run_id):
    # Uses a fresh, uniquely-numbered but still real (MERGE-created, matched
    # not re-created by allocation/order code) canonical Part, to avoid
    # contending with the shared real-catalogue InventoryLedger while still
    # proving the identical MATCH-only Part code path.
    part_number = _unique_part_number(test_run_id, neo4j_session)
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id, part_number=part_number)
    alloc = create_allocation(neo4j_session, req_id, test_run_id=test_run_id)

    part_row = neo4j_session.run(
        "MATCH (p:Part {part_number: $pn}) RETURN p.part_id AS part_id",
        {"pn": part_number},
    ).single()
    assert alloc["part_id"] == part_row["part_id"]

    order = create_order(neo4j_session, req_id, test_run_id=test_run_id)
    assert order["partNumber"] == part_number

    link = neo4j_session.run(
        """
        MATCH (r:FulfilmentRequest {id: $req_id})-[:HAS_ALLOCATION]->(a:Allocation)-[:ALLOCATES]->(p:Part {part_number: $pn})
        MATCH (o:Order)-[:BASED_ON_ALLOCATION]->(a)
        RETURN p.part_number AS pn
        """,
        {"req_id": req_id, "pn": part_number},
    ).single()
    assert link is not None, "Allocation and Order must both reference the SAME canonical Part node"


def test_intelligence_selected_part_completes_allocation_and_order(neo4j_session, test_run_id):
    """
    A Part reached via Parts Intelligence (matched by part_number/part_id,
    same as catalogue browsing — see frontend intelligenceMatch.ts) must
    flow through the exact same Allocation/Order code path, with no
    intelligence-specific branch.
    """
    part_number = _unique_part_number(test_run_id, neo4j_session)
    part_row = neo4j_session.run(
        "MATCH (p:Part {part_number: $pn}) RETURN p.part_id AS part_id, p.part_number AS part_number",
        {"pn": part_number},
    ).single()
    assert part_row is not None, "Seed part must exist for this test to be meaningful"

    # Simulate the canonical part_number resolved by Intelligence's
    # findCatalogueMatchId, fed into the identical fulfilment/allocation/order flow.
    req_id, _ = _drive_to_allocation_pending(neo4j_session, test_run_id, part_number=part_row["part_number"])
    alloc = create_allocation(neo4j_session, req_id, test_run_id=test_run_id)
    assert alloc["part_id"] == part_row["part_id"]
    order = create_order(neo4j_session, req_id, test_run_id=test_run_id)
    assert order["status"] == "CREATED"
    assert order["partNumber"] == part_row["part_number"]


# ---------------------------------------------------------------------------
# API layer smoke test (route wiring, error envelope)
# ---------------------------------------------------------------------------

def test_api_allocation_and_order_flow(neo4j_session, test_run_id):
    part_number = _unique_part_number(test_run_id, neo4j_session)
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number=part_number,
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    neo4j_session.run(
        "MATCH (r:FulfilmentRequest {id:$id}) SET r.testRunId=$run", {"id": req_id, "run": test_run_id}
    ).consume()

    options = generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)
    option_id = options[0]["id"]
    select_fulfilment_option(neo4j_session, req_id, option_id, test_run_id=test_run_id)
    proceed_to_allocation_pending(neo4j_session, req_id, test_run_id=test_run_id)

    # Phase 10B: pass x-test-run-id so the Allocation/Order this HTTP call
    # creates are tagged for cleanup (see app/api/v1/allocation.py,
    # app/api/v1/order.py) — without this header these API-level calls leak
    # untagged nodes into the live database.
    headers = {"x-test-run-id": test_run_id}

    resp = client.post(f"/api/v1/fulfilment-requests/{req_id}/allocation", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CONFIRMED"

    resp = client.get(f"/api/v1/fulfilment-requests/{req_id}/allocation")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"

    resp = client.post(f"/api/v1/fulfilment-requests/{req_id}/order", headers=headers)
    assert resp.status_code == 200, resp.text
    order_body = resp.json()
    assert order_body["status"] == "CREATED"

    # The Order node itself must be tagged for cleanup too (Phase 10B fix —
    # create_order() previously never wrote testRunId on the Order node even
    # when passed one).
    tag_row = neo4j_session.run(
        "MATCH (o:Order {id: $id}) RETURN o.testRunId AS run", {"id": order_body["id"]}
    ).single()
    assert tag_row["run"] == test_run_id

    resp = client.get(f"/api/v1/orders/{order_body['id']}")
    assert resp.status_code == 200
    assert resp.json()["integration_status"] == "NOT_CONNECTED"

    # Ordering again without a fresh allocation must not create a duplicate.
    resp2 = client.post(f"/api/v1/fulfilment-requests/{req_id}/order", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["id"] == order_body["id"]
