"""
backend/tests/test_parts_store_migration.py

Tests for the FastAPI routes that replaced the retired Node/Vercel-style
layer (frontend/api/part-enrichment.js, frontend/api/quote-request.js):

  - GET  /api/v1/part-enrichment
  - POST /api/v1/quote-request

Database: Neo4j AuraDB (real instance, isolated per test via testRunId).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/v1/part-enrichment
# ---------------------------------------------------------------------------

def test_part_enrichment_returns_compatible_machines_for_fitted_part(neo4j_session, test_run_id):
    part_number = f"PN-{test_run_id}"
    machine_id = f"M-{test_run_id}"

    neo4j_session.run(
        """
        CREATE (p:Part {part_id: $part_id, part_number: $part_number, testRunId: $run})
        CREATE (m:Machine {machine_id: $machine_id, model: 'Test Model X', testRunId: $run})
        CREATE (m)-[:HAS_PART_FITMENT {evidence: 'EXACT_MODEL'}]->(p)
        """,
        {
            "part_id": f"part-{test_run_id}",
            "part_number": part_number,
            "machine_id": machine_id,
            "run": test_run_id,
        },
    ).consume()

    res = client.get("/api/v1/part-enrichment")
    assert res.status_code == 200
    body = res.json()
    assert "enrichment" in body
    entry = body["enrichment"].get(part_number)
    assert entry is not None
    assert entry["partId"] == f"part-{test_run_id}"
    assert any(
        m["machineId"] == machine_id and m["model"] == "Test Model X" and m["level"] == "EXACT MODEL"
        for m in entry["compatibleMachines"]
    )


def test_part_enrichment_omits_parts_without_fitment(neo4j_session, test_run_id):
    part_number = f"PN-NOFIT-{test_run_id}"
    neo4j_session.run(
        "CREATE (p:Part {part_id: $part_id, part_number: $part_number, testRunId: $run})",
        {"part_id": f"part-{test_run_id}", "part_number": part_number, "run": test_run_id},
    ).consume()

    res = client.get("/api/v1/part-enrichment")
    assert res.status_code == 200
    assert part_number not in res.json()["enrichment"]


# ---------------------------------------------------------------------------
# POST /api/v1/quote-request
# ---------------------------------------------------------------------------

def test_quote_request_writes_expected_graph_shape(neo4j_session, test_run_id):
    part_number = f"PN-{test_run_id}"
    neo4j_session.run(
        "CREATE (p:Part {part_id: $part_id, part_number: $part_number, testRunId: $run})",
        {"part_id": f"part-{test_run_id}", "part_number": part_number, "run": test_run_id},
    ).consume()

    email = f"{test_run_id}@example.com"
    payload = {
        "name": "Test Customer",
        "email": email,
        "phone": "+31 6 1234 5678",
        "note": "Please call before shipping",
        "items": [
            {"id": "cart-1", "name": "Test Part", "qty": 2, "machine": "Test Model X", "partNumber": part_number},
        ],
    }

    res = client.post("/api/v1/quote-request", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["requestedPartCount"] == 1
    assert body["projectionStatus"] == "SUCCESS"
    inquiry_id = body["inquiryId"]

    # Tag the created nodes for cleanup, and verify the exact write shape:
    # (:Customer)-[:SUBMITTED]->(:PartsInquiry)-[:REQUESTS]->(:RequestedPart)-[:FOR_PART]->(:Part)
    verify = neo4j_session.run(
        """
        MATCH (c:Customer {email: $email})-[:SUBMITTED]->(i:PartsInquiry {id: $inquiry_id})
              -[:REQUESTS]->(rp:RequestedPart)-[:FOR_PART]->(p:Part {part_number: $part_number})
        SET c.testRunId = $run, i.testRunId = $run, rp.testRunId = $run
        RETURN c.name AS customerName, i.note AS note, rp.quantity AS qty, rp.part_name AS partName
        """,
        {"email": email, "inquiry_id": inquiry_id, "part_number": part_number, "run": test_run_id},
    ).single()

    assert verify is not None
    assert verify["customerName"] == "Test Customer"
    assert verify["note"] == "Please call before shipping"
    assert verify["qty"] == 2
    assert verify["partName"] == "Test Part"


def test_quote_request_requires_name_email_phone(neo4j_session, test_run_id):
    res = client.post(
        "/api/v1/quote-request",
        json={"name": "", "email": "", "phone": "", "items": [{"name": "X", "qty": 1}]},
    )
    assert res.status_code == 400


def test_quote_request_requires_valid_email(neo4j_session, test_run_id):
    res = client.post(
        "/api/v1/quote-request",
        json={
            "name": "Test Customer",
            "email": "not-an-email",
            "phone": "123",
            "items": [{"name": "X", "qty": 1}],
        },
    )
    assert res.status_code == 400


def test_quote_request_requires_at_least_one_item(neo4j_session, test_run_id):
    email = f"{test_run_id}@example.com"
    res = client.post(
        "/api/v1/quote-request",
        json={"name": "Test Customer", "email": email, "phone": "123", "items": []},
    )
    assert res.status_code == 400
