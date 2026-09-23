"""
backend/tests/test_phase10b_wiring.py

Phase 10B — HCME Europe graph wiring + Parts Store business-flow
consolidation. Covers the two "must fix" items:

1. FulfilmentRequest reaches COMPLETED via the real Shipment->ServiceJob
   traversal even when the ServiceJob is only linked through Shipment
   (the hand-seeded demo-data shape), not just through the direct
   Order/FulfilmentRequest edges create_service_job() also writes.
2. API-level (HTTP) calls to order/fulfilment/availability/allocation now
   accept x-test-run-id and tag every node they create, so they no longer
   leak untagged Order/FulfilmentRequest/Allocation/FulfilmentOption/
   InventoryCache nodes into the live database.
"""
from fastapi.testclient import TestClient

from app.db.neo4j.connection import get_neo4j_driver
from app.main import app
from app.modules.service.service import complete_service, install_part, receive_part, start_service

client = TestClient(app)


def _seed_minimal_journey(session, test_run_id, part_number):
    """A FulfilmentRequest -> Order -> Shipment(DELIVERED) chain with a
    ServiceJob linked ONLY via Shipment-[:HAS_SERVICE_JOB]->ServiceJob
    (no direct Order/FulfilmentRequest edge) — the shape hand-seeded demo
    data actually has, and the shape the pre-fix closing query missed."""
    fr_id = f"freq-p10b-{test_run_id}"
    order_id = f"order-p10b-{test_run_id}"
    shipment_id = f"ship-p10b-{test_run_id}"
    sj_id = f"SJ-P10B-{test_run_id}"
    session.run(
        """
        CREATE (fr:FulfilmentRequest {id: $fr_id, status: 'FULFILMENT', partNumber: $pn,
                                       quantity: 1, testRunId: $run, synthetic: true})
        CREATE (o:Order {id: $order_id, status: 'ACCEPTED', partNumber: $pn, quantity: 1,
                          testRunId: $run, synthetic: true})
        CREATE (sh:Shipment {shipment_id: $shipment_id, status: 'DELIVERED', order_id: $order_id,
                              testRunId: $run, synthetic: true})
        CREATE (sj:ServiceJob {service_job_id: $sj_id, status: 'PART_INSTALLED', order_id: $order_id,
                                shipment_id: $shipment_id, dealer_id: 'DLR-TEST', service_type: 'PARTS_INSTALLATION',
                                testRunId: $run, synthetic: true})
        MERGE (fr)-[:HAS_ORDER]->(o)
        MERGE (o)-[:HAS_SHIPMENT]->(sh)
        MERGE (sh)-[:HAS_SERVICE_JOB]->(sj)
        """,
        {"fr_id": fr_id, "order_id": order_id, "shipment_id": shipment_id, "sj_id": sj_id,
         "pn": part_number, "run": test_run_id},
    ).consume()
    return fr_id, sj_id


def test_fulfilment_request_completes_via_shipment_only_service_link(neo4j_session, test_run_id):
    fr_id, sj_id = _seed_minimal_journey(neo4j_session, test_run_id, "4663907")

    result = complete_service(neo4j_session, sj_id, signoff_notes="Verified", test_run_id=test_run_id)
    assert result["status"] == "COMPLETED"

    fr_row = neo4j_session.run(
        "MATCH (fr:FulfilmentRequest {id: $id}) RETURN fr.status AS status", {"id": fr_id}
    ).single()
    assert fr_row["status"] == "COMPLETED"


def test_fulfilment_request_not_completed_if_shipment_not_delivered(neo4j_session, test_run_id):
    fr_id = f"freq-p10b-nd-{test_run_id}"
    order_id = f"order-p10b-nd-{test_run_id}"
    shipment_id = f"ship-p10b-nd-{test_run_id}"
    sj_id = f"SJ-P10B-ND-{test_run_id}"
    neo4j_session.run(
        """
        CREATE (fr:FulfilmentRequest {id: $fr_id, status: 'FULFILMENT', partNumber: '4663907',
                                       quantity: 1, testRunId: $run, synthetic: true})
        CREATE (o:Order {id: $order_id, status: 'ACCEPTED', partNumber: '4663907', quantity: 1,
                          testRunId: $run, synthetic: true})
        CREATE (sh:Shipment {shipment_id: $shipment_id, status: 'DISPATCHED', order_id: $order_id,
                              testRunId: $run, synthetic: true})
        CREATE (sj:ServiceJob {service_job_id: $sj_id, status: 'PART_INSTALLED', order_id: $order_id,
                                shipment_id: $shipment_id, dealer_id: 'DLR-TEST', service_type: 'PARTS_INSTALLATION',
                                testRunId: $run, synthetic: true})
        MERGE (fr)-[:HAS_ORDER]->(o)
        MERGE (o)-[:HAS_SHIPMENT]->(sh)
        MERGE (sh)-[:HAS_SERVICE_JOB]->(sj)
        """,
        {"fr_id": fr_id, "order_id": order_id, "shipment_id": shipment_id, "sj_id": sj_id, "run": test_run_id},
    ).consume()

    complete_service(neo4j_session, sj_id, test_run_id=test_run_id)

    fr_row = neo4j_session.run(
        "MATCH (fr:FulfilmentRequest {id: $id}) RETURN fr.status AS status", {"id": fr_id}
    ).single()
    # Defence in depth: even though receive_part() already refuses to progress
    # a ServiceJob whose shipment isn't DELIVERED, the closing query itself
    # must not mark the journey COMPLETED against an undelivered shipment.
    assert fr_row["status"] != "COMPLETED"


def test_api_level_order_flow_leaves_no_untagged_nodes(neo4j_session, test_run_id):
    """Reproduces the exact leak found in Phase 10B: driving the waterfall
    entirely through HTTP (as the browser does), with x-test-run-id set,
    must leave zero untagged Order/FulfilmentRequest/Allocation/
    FulfilmentOption nodes behind."""
    driver = get_neo4j_driver()
    headers = {"x-test-run-id": test_run_id}

    part_number = f"PN10B-{test_run_id[:8]}"
    with driver.session() as setup:
        setup.run(
            "MERGE (p:Part {part_number: $pn}) ON CREATE SET p.part_id = $pn, p.testRunId = $run",
            {"pn": part_number, "run": test_run_id},
        ).consume()

    resp = client.post(
        "/api/v1/fulfilment-requests",
        json={"partNumber": part_number, "quantity": 1, "destinationBranchId": "DEALER-BR-101"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    req_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/fulfilment-requests/{req_id}/availability",
        json={"partNumber": part_number, "quantity": 1},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    resp = client.post(f"/api/v1/fulfilment-requests/{req_id}/options", headers=headers)
    assert resp.status_code == 200, resp.text
    option_id = resp.json()["options"][0]["id"]

    resp = client.post(
        f"/api/v1/fulfilment-requests/{req_id}/select-option", json={"optionId": option_id}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    resp = client.post(f"/api/v1/fulfilment-requests/{req_id}/proceed-to-allocation", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = client.post(f"/api/v1/fulfilment-requests/{req_id}/allocation", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = client.post(f"/api/v1/fulfilment-requests/{req_id}/order", headers=headers)
    assert resp.status_code == 200, resp.text
    order_id = resp.json()["id"]

    with driver.session() as check:
        for label, key, value in [
            ("FulfilmentRequest", "id", req_id),
            ("Order", "id", order_id),
        ]:
            row = check.run(
                f"MATCH (n:{label} {{{key}: $v}}) RETURN n.testRunId AS run", v=value
            ).single()
            assert row is not None, f"{label} {value} not found"
            assert row["run"] == test_run_id, f"{label} {value} was created without testRunId — will leak"

        untagged = check.run(
            """
            MATCH (n) WHERE any(l IN labels(n) WHERE l IN
                ['Order', 'FulfilmentRequest', 'Allocation', 'FulfilmentOption', 'InventoryCache'])
              AND n.partNumber = $pn AND n.testRunId IS NULL
            RETURN count(n) AS n
            """,
            pn=part_number,
        ).single()["n"]
        assert untagged == 0, "API-level flow created node(s) with no testRunId — these will leak into the live DB"
