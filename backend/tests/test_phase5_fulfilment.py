"""
backend/tests/test_phase5_fulfilment.py

Phase 5 Fulfilment domain + API integration tests — Neo4j backend.

Database: Neo4j AuraDB (real instance, isolated per test via testRunId).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.availability.service import check_availability
from app.modules.fulfilment.service import (
    generate_fulfilment_options,
    get_fulfilment_options,
    select_fulfilment_option,
    proceed_to_allocation_pending,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Phase 5 Fulfilment Domain & Transition Tests
# ---------------------------------------------------------------------------

def test_generate_fulfilment_options_available_source(neo4j_session, test_run_id):
    # 1. Availability check → AVAILABILITY_CHECKED
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="4656429",
        quantity=2,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]

    # 2. Generate options
    options = generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)
    assert len(options) > 0, "Should generate at least one candidate option"

    # BR-03: Candidate set presented without auto-selection
    for opt in options:
        assert opt["is_selected"] is False
        assert opt["fulfilment_request_id"] == req_id
        assert opt["confidence"] == "CONFIRMED"

    # Phase 10: Candidate options carry deterministic European transport data
    # (Road Standard/Express, Rail, Air) labelled synthetic=true and currency EUR.
    assert len(options) >= 1
    for opt in options:
        assert opt["transport_data_status"] == "CONFIRMED"
        assert opt["transport_cost"] > 0
        assert opt["currency"] == "EUR"
        assert opt["transit_days"] >= 0
        assert opt["eta"] is not None
        assert opt["carrier_code"] is not None
        assert opt["transport_mode"] in ["ROAD", "RAIL", "AIR", "INTERNAL_TRANSFER"]
        assert opt["synthetic"] is True


def test_generate_fulfilment_options_unknown_source_low_confidence(neo4j_session, test_run_id):
    """BR-01: UNKNOWN inventory source → UNCONFIRMED confidence."""
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="TEST-STALE",
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]

    options = generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)
    assert len(options) > 0
    unknown_opts = [o for o in options if o["source_id"] == "DEALER-DEPOT-MUNICH"]
    assert len(unknown_opts) > 0
    assert unknown_opts[0]["confidence"] == "UNCONFIRMED"


def test_generate_fulfilment_options_multi_source_split(neo4j_session, test_run_id):
    """Multi-source candidate when single sources only partially fulfill quantity."""
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="TEST-MULTI-SPLIT",
        quantity=6,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]

    options = generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)
    split_opts = [o for o in options if o.get("is_split") is True]
    assert len(split_opts) > 0, "Should offer a multi-source split option"
    assert split_opts[0]["source_id"] == "MULTI_SOURCE_SPLIT"


def test_select_fulfilment_option_valid_transition(neo4j_session, test_run_id):
    """AVAILABILITY_CHECKED → OPTION_SELECTED."""
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="4656429",
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    options = generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)
    chosen_option_id = options[0]["id"]

    res = select_fulfilment_option(
        session=neo4j_session,
        fulfilment_request_id=req_id,
        option_id=chosen_option_id,
        test_run_id=test_run_id,
    )
    assert res["status"] == "OPTION_SELECTED"
    assert res["selected_option_id"] == chosen_option_id

    # Verify Neo4j state
    req_row = neo4j_session.run(
        "MATCH (r:FulfilmentRequest {id: $id}) RETURN r.status, r.selectedOptionId",
        {"id": req_id},
    ).single()
    assert req_row["r.status"] == "OPTION_SELECTED"
    assert req_row["r.selectedOptionId"] == chosen_option_id

    audit_row = neo4j_session.run(
        """
        MATCH (a:AuditRecord {entityId: $id, action: 'FULFILMENT_OPTION_SELECTED'})
        RETURN a.newState
        """,
        {"id": req_id},
    ).single()
    assert audit_row is not None
    assert audit_row["a.newState"] == "OPTION_SELECTED"


def test_select_fulfilment_option_invalid_option(neo4j_session, test_run_id):
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="4656429",
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)

    with pytest.raises(Exception):
        select_fulfilment_option(
            session=neo4j_session,
            fulfilment_request_id=req_id,
            option_id="non-existent-option-999",
            test_run_id=test_run_id,
        )


def test_proceed_to_allocation_pending_valid(neo4j_session, test_run_id):
    """AVAILABILITY_CHECKED → OPTION_SELECTED → ALLOCATION_PENDING."""
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="4656429",
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    options = generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)
    chosen_opt_id = options[0]["id"]
    select_fulfilment_option(
        neo4j_session, req_id, chosen_opt_id, test_run_id=test_run_id
    )

    res = proceed_to_allocation_pending(
        neo4j_session, req_id, test_run_id=test_run_id
    )
    assert res["status"] == "ALLOCATION_PENDING"
    assert res["selected_option_id"] == chosen_opt_id

    # Verify DB persistence
    req_row = neo4j_session.run(
        "MATCH (r:FulfilmentRequest {id: $id}) RETURN r.status",
        {"id": req_id},
    ).single()
    assert req_row["r.status"] == "ALLOCATION_PENDING"

    audit_row = neo4j_session.run(
        """
        MATCH (a:AuditRecord {entityId: $id, action: 'ADVANCED_TO_ALLOCATION_PENDING'})
        RETURN a.newState
        """,
        {"id": req_id},
    ).single()
    assert audit_row is not None
    assert audit_row["a.newState"] == "ALLOCATION_PENDING"


def test_invalid_state_transitions_rejected(neo4j_session, test_run_id):
    """Cannot skip steps in the state machine."""
    # 1. Cannot go ALLOCATION_PENDING from AVAILABILITY_CHECKED (must select first)
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="4656429",
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]

    with pytest.raises(Exception):
        proceed_to_allocation_pending(
            neo4j_session, req_id, test_run_id=test_run_id
        )

    # 2. Cannot select option when in REQUESTED state (no availability check)
    raw_req_id = f"freq-requested-only-{test_run_id}"
    neo4j_session.run(
        """
        CREATE (r:FulfilmentRequest {
            id: $id, partNumber: '4656429', quantity: 1,
            customerId: 'CUST', destinationBranchId: 'BRANCH',
            status: 'REQUESTED', testRunId: $run,
            createdAt: datetime(), updatedAt: datetime()
        })
        """,
        {"id": raw_req_id, "run": test_run_id},
    ).consume()

    with pytest.raises(Exception):
        select_fulfilment_option(
            neo4j_session, raw_req_id, "opt-fake", test_run_id=test_run_id
        )


# ---------------------------------------------------------------------------
# End-to-End API Router Integration Tests
# ---------------------------------------------------------------------------

def test_fulfilment_journey_api_e2e():
    """Full REQUESTED → ALLOCATION_PENDING journey via HTTP API."""
    # 1. Create Request
    create_resp = client.post(
        "/api/v1/fulfilment-requests",
        json={
            "part_number": "4656429",
            "quantity": 2,
            "destination_branch_id": "DEALER-BRANCH-NL-01",
        },
    )
    assert create_resp.status_code == 200
    req_id = create_resp.json()["id"]

    # 2. Trigger Availability Check
    avail_resp = client.post(
        f"/api/v1/fulfilment-requests/{req_id}/availability",
        json={
            "part_number": "4656429",
            "quantity": 2,
            "destination_branch_id": "DEALER-BRANCH-NL-01",
        },
    )
    assert avail_resp.status_code == 200

    # 3. Compute Fulfilment Options
    opts_resp = client.post(f"/api/v1/fulfilment-requests/{req_id}/options")
    assert opts_resp.status_code == 200
    opts_data = opts_resp.json()
    assert opts_data["total_options"] > 0
    selected_option_id = opts_data["options"][0]["id"]

    # 4. Select an Option
    select_resp = client.post(
        f"/api/v1/fulfilment-requests/{req_id}/select-option",
        json={"option_id": selected_option_id},
    )
    assert select_resp.status_code == 200
    assert select_resp.json()["status"] == "OPTION_SELECTED"

    # 5. Advance to Allocation Pending
    pending_resp = client.post(
        f"/api/v1/fulfilment-requests/{req_id}/proceed-to-allocation"
    )
    assert pending_resp.status_code == 200
    assert pending_resp.json()["status"] == "ALLOCATION_PENDING"

    # 6. Verify GET endpoint reflects ALLOCATION_PENDING
    get_resp = client.get(f"/api/v1/fulfilment-requests/{req_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["status"] == "ALLOCATION_PENDING"
    assert data["selected_option_id"] == selected_option_id


def test_catalogue_part_uses_labelled_synthetic_depot_stock(neo4j_session, test_run_id):
    """Phase 10: a real catalogue part (PT-001, 4663907) reads SYNTHETIC_DEMO
    stock at the real Oosterhout depot — never the mock's invented depots —
    and every record built on it is labelled synthetic."""
    avail = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number="4663907",
        quantity=1,
        test_run_id=test_run_id,
    )
    sources = avail["sources"]
    assert sources, "catalogue part must have seeded demo stock"
    assert {s["source_id"] for s in sources} <= {"DEPOT-OOSTERHOUT"} | {
        r["id"] for r in neo4j_session.run("MATCH (d:DealerBranch) RETURN d.dealer_id AS id")
    }
    assert all(s["provenance"] == "SYNTHETIC_DEMO" for s in sources)

    cache = neo4j_session.run(
        "MATCH (c:InventoryCache {partNumber:'4663907', testRunId:$run}) RETURN c.synthetic AS syn, c.data_source AS ds",
        run=test_run_id,
    ).data()
    assert cache and all(c["syn"] is True and c["ds"] == "SYNTHETIC_DEMO" for c in cache)

    options = generate_fulfilment_options(neo4j_session, avail["fulfilment_request_id"], test_run_id=test_run_id)
    assert options and all(o["synthetic"] is True for o in options)
    assert all(o["transport_cost"] > 0 for o in options)
    assert all(o["currency"] == "EUR" for o in options)
