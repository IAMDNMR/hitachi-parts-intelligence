"""
backend/tests/test_phase11_hcme_intelligence.py

Phase 11b - HCME Parts Intelligence, corrected for the real HCME use case. Runs against the live Aura graph (read-only).

Covers: supporting search (typos, specs, relevance floor), the interchangeability gate (part type / family / fitment),
"Candidate for Engineering Review" wording, RFQ (stock/price/lead time NOT_CONNECTED, never compared with demo stock),
compliance verdicts (a demo certificate never yields PASS), disruption scenarios (no severity/score, provenance shown),
supplier risk NOT_CONNECTED, and the KPI set.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.db.neo4j.connection import get_neo4j_driver
from app.main import app
from app.modules.intelligence import assistant, disruption, embeddings, interchangeability as ic
from app.modules.intelligence.providers import DeterministicLLMProvider, EmbeddingProvider

client = TestClient(app)
API = "/api/v1/intelligence"


@pytest.fixture(autouse=True)
def _deterministic(monkeypatch):
    monkeypatch.setattr(assistant, "get_llm_provider", lambda: DeterministicLLMProvider())


@pytest.fixture()
def session():
    with get_neo4j_driver().session() as s:
        yield s


def _walk(obj):
    """Every key in a nested response."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


# ---------------------------------------------------------------- embeddings (local, no neural model)

def test_local_embedding_provider_follows_the_abstraction_and_is_deterministic():
    p = embeddings.LocalEmbeddingProvider()
    assert isinstance(p, EmbeddingProvider) and p.is_available() and p.dimensions == 256
    assert p.embed("Hydraulic pump") == p.embed("Hydraulic pump")


def test_embedding_failure_degrades_to_none(monkeypatch):
    monkeypatch.setattr(embeddings, "_embed_cached", lambda t: (_ for _ in ()).throw(RuntimeError("boom")))
    assert embeddings.LocalEmbeddingProvider().embed("x") is None


# ---------------------------------------------------------------- part search

def test_standard_search_stays_primary_for_plain_queries():
    r = client.post(f"{API}/query", json={"query": "hydraulic pump"}).json()
    assert r["intent"] == "part_search" and r["data"]["candidates"][0]["part_id"] == "PT-045"


def test_exact_part_number_and_id_are_100_percent():
    r = client.get(f"{API}/search/hybrid", params={"q": "4658321"}).json()["results"]
    assert r[0]["part_id"] == "PT-045" and r[0]["similarity_pct"] == 100 and r[0]["factors"]["exact"]
    assert client.get(f"{API}/search/hybrid", params={"q": "PT-031"}).json()["results"][0]["part_id"] == "PT-031"


def test_typo_search_finds_the_pump_and_hides_weak_matches():
    r = client.get(f"{API}/search/hybrid", params={"q": "hydralic pmp"}).json()
    assert [c["part_id"] for c in r["results"]] == ["PT-045"] and r["min_relevance_pct"] == 30


def test_weak_matches_are_not_shown_next_to_a_strong_one():
    r = client.get(f"{API}/search/hybrid", params={"q": "24V starter motor"}).json()
    assert [c["part_id"] for c in r["results"]] == ["PT-055"]
    assert r["weak_matches_hidden"] > 0


def test_spec_search_uses_electrical_values_stated_in_real_part_names():
    r = client.get(f"{API}/search/hybrid", params={"q": "24V alternator with 100A"}).json()
    assert r["requested_specs"] == {"voltage_v": 24.0, "current_a": 100.0}
    top = r["results"][0]
    assert top["part_id"] == "PT-056" and top["spec_match"]["matched"] and not top["spec_match"]["mismatched"]


def test_semantic_search_is_ranked_scored_and_thresholded():
    r = client.get(f"{API}/search/semantic", params={"q": "accumulator for starting the engine"}).json()
    res = r["results"]
    assert res and all(c["similarity_pct"] >= r["min_relevance_pct"] for c in res)
    assert res == sorted(res, key=lambda c: (-c["similarity"], c["part_id"]))


def test_similarity_is_stable_between_calls():
    assert client.get(f"{API}/parts/PT-007/similar").json() == client.get(f"{API}/parts/PT-007/similar").json()


# ---------------------------------------------------------------- interchangeability gate

def test_oil_filter_is_not_offered_as_a_fuel_filter_alternative():
    assert ic.type_key({"part_subcategory": "Filter", "part_name": "Hitachi Genuine Oil Filter"}) == "oil filter"
    assert ic.type_key({"part_subcategory": "Filter", "part_name": "Hitachi Genuine Fuel Filter"}) == "fuel filter"
    r = client.get(f"{API}/parts/PT-026/similar").json()
    assert r["alternatives"] == []                       # PT-026 is a family record anyway, and oil filter != fuel filter
    ok, why = ic.gate({"part_subcategory": "Filter", "part_name": "Oil Filter", "record_class": "ORDERABLE_OEM_PART"},
                      {"part_subcategory": "Filter", "part_name": "Fuel Filter", "record_class": "ORDERABLE_OEM_PART"}, {"M1"}, {"M1"})
    assert not ok and "different part type" in why


def test_starter_and_traction_batteries_are_different_types():
    assert ic.type_key({"part_subcategory": "Battery", "part_name": "Battery - Starter, Lighting & Ignition"}) == "battery/starter"
    assert ic.type_key({"part_subcategory": "Battery", "part_name": "Battery - Traction (Industrial)"}) == "battery/traction"
    r = client.get(f"{API}/parts/PT-008/similar").json()  # traction battery: its only fitment-sharing peer PT-007 is a starter battery
    assert "PT-007" not in [a["part_id"] for a in r["alternatives"]]


def test_family_records_are_excluded_as_target_and_as_candidate():
    r = client.get(f"{API}/parts/PT-021/similar").json()
    assert r["alternatives"] == [] and "family record" in r["note"]
    ids = {a["part_id"] for a in client.get(f"{API}/parts/PT-007/similar").json()["alternatives"]}
    assert not any(int(i[3:]) in range(21, 44) for i in ids)


def test_fitment_is_a_hard_filter():
    r = client.get(f"{API}/parts/PT-004/similar").json()
    assert r["alternatives"] == []
    assert all("no shared machine fitment" in x["reasons"][0] for x in r["rejected"] if "type" not in x["reasons"][0])


def test_candidate_wording_and_similarity_is_only_a_supporting_signal():
    r = client.get(f"{API}/parts/PT-007/similar").json()
    a = r["alternatives"][0]
    assert a["part_id"] == "PT-015" and a["status"] == "Candidate for Engineering Review"
    assert "supporting signal" in a["similarity_role"] and r["authoritative_data"].startswith("none loaded")
    assert not any("replacement" in k or "recommend" in k for k in _walk(r))


def test_no_candidate_answer_is_honest():
    r = client.post(f"{API}/query", json={"query": "Are there alternatives for PT-045?"}).json()
    assert "No candidate" in r["answer"] or "no candidate" in r["answer"].lower()
    r = client.post(f"{API}/query", json={"query": "Are there alternatives for PT-007?"}).json()
    assert "Engineering Review" in r["answer"] and "PT-015" in r["answer"]


def test_unknown_part_similarity_is_not_found():
    assert client.get(f"{API}/parts/PT-999/similar").json()["found"] is False


# ---------------------------------------------------------------- RFQ

def test_rfq_parses_request_and_never_compares_quantity_with_demo_stock():
    r = client.post(f"{API}/rfq", json={"text": "Need 20 units of a 24V starter motor for ZX210LC-7 within 2 weeks"}).json()
    assert r["parsed"]["quantity"] == 20 and r["parsed"]["specs"] == {"voltage_v": 24.0}
    assert r["parsed"]["machine_model"] == "ZX210LC-7" and r["parsed"]["deadline_days"] == 14
    top = r["matches"][0]
    assert top["part_id"] == "PT-055" and top["selected_because"]
    for k in ("availability", "price", "lead_time"):
        assert top[k]["status"] == "NOT_CONNECTED"
    assert top["availability"]["requested_quantity"] == 20
    text = " ".join(top["risks"] + r["notes"]).lower()
    assert "demo stock" not in text and "insufficient" not in text and "sufficient" not in text
    assert any("not connected" in n for n in r["notes"]) and any("Deadline" in n for n in r["notes"])
    assert any("fitment" in x.lower() for x in top["risks"])


def test_rfq_routes_from_natural_language():
    r = client.post(f"{API}/query", json={"query": "Need 20 units of a 24V starter motor for ZX210LC-7"}).json()
    assert r["intent"] == "rfq_search" and r["data"]["candidates"][0]["part_id"] == "PT-055"
    assert r["data"]["candidates"][0]["commercial"]["availability"]["status"] == "NOT_CONNECTED"


# ---------------------------------------------------------------- impact (real fitment, demo BOM labelled)

def test_impact_uses_real_fitment_and_labels_the_demo_bom(session):
    r = disruption.analyse(session, "part_unavailable", part_id="PT-045")
    assert len(r["affected"]["machines"]) == 7
    assert r["provenance"]["machines_and_fitment"].startswith("SOURCE_DERIVED")
    assert r["provenance"]["assemblies_bom_criticality"] == "SYNTHETIC_DEMO"
    assert all(a["basis"] == "SYNTHETIC_DEMO" for a in r["affected"]["assemblies"])
    assert r["affected"]["customers"] == [] and "installed-base" in r["affected"]["customers_note"]


# ---------------------------------------------------------------- compliance

def test_demo_certificates_never_produce_pass(session):
    for cand in ("PT-015", "PT-003", "PT-045", "PT-055"):
        v = disruption.compliance_verdict(session, "PT-007", cand)
        assert v["status"] != "PASS" and v["verified"] is False
    v = disruption.compliance_verdict(session, "PT-031", "PT-032")
    assert v["status"] in ("UNVERIFIED", "WARNING", "FAIL") and v["satisfied_real_evidence"] == []


def test_real_evidence_would_pass_and_expiry_and_missing_fail(session):
    """The engine is ready for real evidence: a throw-away part holding REAL (synthetic=false) valid certificates yields PASS;
    an expired one yields FAIL; none yields FAIL. Uses its own temporary Part node - no existing data is touched."""
    tmp = "TEST-P11B-SUB"
    req_ids = [r["compliance_id"] for r in disruption.requirements_of(session, "PT-031")]
    assert req_ids
    try:
        session.run("MERGE (p:Part {part_id:$id}) SET p.testRunId = 'P11B', p.part_name = 'temp'", id=tmp).consume()
        assert disruption.compliance_verdict(session, "PT-031", tmp)["status"] == "FAIL"           # nothing held
        session.run("""MATCH (p:Part {part_id:$id}) UNWIND $ids AS cid MATCH (c:ComplianceRequirement {compliance_id:cid})
                       MERGE (p)-[r:HAS_CERTIFICATION]->(c) SET r.synthetic = false, r.valid_until = date('2099-01-01')""",
                    id=tmp, ids=req_ids).consume()
        v = disruption.compliance_verdict(session, "PT-031", tmp)
        assert v["status"] == "PASS" and v["verified"] and len(v["satisfied_real_evidence"]) == len(req_ids)
        assert disruption.compliance_verdict(session, "PT-031", tmp, today=date(2100, 1, 1))["status"] == "FAIL"   # expired
        session.run("MATCH (:Part {part_id:$id})-[r:HAS_CERTIFICATION]->() SET r.synthetic = true", id=tmp).consume()
        assert disruption.compliance_verdict(session, "PT-031", tmp)["status"] == "UNVERIFIED"                     # demo evidence only
    finally:
        session.run("MATCH (p:Part {part_id:$id}) DETACH DELETE p", id=tmp).consume()


def test_compliance_check_endpoint_reports_basis():
    r = client.get(f"{API}/parts/PT-031/compliance-check", params={"substitute": "PT-032"}).json()
    assert r["status"] in ("UNVERIFIED", "WARNING", "FAIL", "PASS", "NO_REQUIREMENT_RECORDED") and "SYNTHETIC_DEMO" in r["basis"]


# ---------------------------------------------------------------- supplier risk

def test_supplier_part_links_stay_demo_only_and_real_coverage_is_zero(session):
    assert session.run("MATCH (:Part)-[l:SUPPLIED_BY]->(:Supplier) WHERE coalesce(l.synthetic,false) = false RETURN count(l) AS n").single()["n"] == 0
    r = client.get(f"{API}/parts/PT-045/graph-insights").json()["supplier_risk"]
    assert r["status"] == "NOT_CONNECTED" or "NOT" in str(r.get("status", "")).upper() or r.get("connected") is False


def test_real_sap_supplier_has_no_part_links_and_says_so(session):
    r = disruption.analyse(session, "supplier_unavailable", supplier="THORBURN GEIGER")
    assert r["affected"]["parts"] == [] and any("NOT_CONNECTED" in n for n in r["notes"])
    assert r["provenance"]["supplier_links"] == "NOT_CONNECTED"


# ---------------------------------------------------------------- disruption

def test_disruption_has_no_severity_score_or_weights_anywhere(session):
    for args in (("part_unavailable", "PT-007"), ("compliance_failure", "PT-007"), ("stock_shortage", "PT-007")):
        r = disruption.analyse(session, args[0], part_id=args[1])
        keys = set(_walk(r))
        assert not ({"severity", "score", "weights", "mitigation_score"} & keys)
        assert not any("GOOD_CANDIDATE" in str(v) for v in [r["summary"]])


def test_part_unavailable_shows_parts_assemblies_machines_orders_candidates_and_dependency(session):
    r = disruption.analyse(session, "part_unavailable", part_id="PT-007")
    assert r["affected"]["parts"] and r["affected"]["assemblies"] and len(r["affected"]["machines"]) == 4 and "orders" in r["affected"]
    assert r["supplier_dependency"]["basis"] == "SYNTHETIC_DEMO" and r["supplier_dependency"]["sole_source"]
    cand = r["mitigation"][0]["candidates"][0]
    assert cand["part_id"] == "PT-015" and cand["compliance"]["status"] and cand["supplier_dependency"]["risk"] and cand["stock"]["status"]
    assert cand["status"] in ("Candidate for Engineering Review", "Not Suitable", "Insufficient Data")
    assert cand["why_shown"] and r["mitigation"][0]["explanation"]


def test_graph_disqualifies_a_candidate_that_passes_the_fitment_filters(session):
    r = disruption.analyse(session, "part_unavailable", part_id="PT-007")
    cand = r["mitigation"][0]["candidates"][0]
    assert cand["status"] == "Not Suitable" and cand["not_suitable_because"]
    assert cand["machine_coverage_pct"] > 0


def test_supplier_unavailable_lists_dependency_and_uses_demo_labels(session):
    r = disruption.analyse(session, "supplier_unavailable", supplier="Demo Battery Supplier")
    assert len(r["affected"]["parts"]) == 20 and all(p["sole_source"] for p in r["affected"]["parts"])
    assert r["provenance"]["supplier_links"] == "SYNTHETIC_DEMO" and any("SYNTHETIC_DEMO" in n for n in r["notes"])
    for m in r["mitigation"]:
        assert all(c["status"] in ("Candidate for Engineering Review", "Not Suitable", "Insufficient Data") for c in m["candidates"])
    assert any(c["supplier_dependency"]["risk"] == "BLOCKED" for m in r["mitigation"] for c in m["candidates"])


def test_family_record_disruption_assesses_no_substitute(session):
    r = disruption.analyse(session, "part_unavailable", part_id="PT-031")
    assert r["trigger"]["family_record"] and r["mitigation"][0]["candidates"] == []
    assert "family record" in r["summary"]


def test_stock_shortage_stock_is_labelled_demo(session):
    r = disruption.analyse(session, "stock_shortage", part_id="PT-001")
    assert r["stock"]["shortfall"] is not None or r["stock"]["total"] is None
    assert "SYNTHETIC_DEMO" in r["stock"]["note"] and r["provenance"]["stock"] == "SYNTHETIC_DEMO"


def test_disruption_endpoint_errors():
    assert client.post(f"{API}/disruption", json={"scenario": "bogus"}).status_code == 400
    assert client.post(f"{API}/disruption", json={"scenario": "part_unavailable", "part_id": "PT-999"}).status_code == 404


def test_nl_disruption_routing_has_no_severity():
    r = client.post(f"{API}/query", json={"query": "What happens if Demo Battery Supplier becomes unavailable?"}).json()
    assert r["intent"] == "disruption" and r["result_type"] == "DISRUPTION_ANALYSIS"
    assert "severity" not in r["data"]["disruption"] and r["data"]["disruption"]["provenance"]["supplier_links"] == "SYNTHETIC_DEMO"
    r = client.post(f"{API}/query", json={"query": "What if PT-007 is out of stock?"}).json()
    assert r["data"]["disruption"]["scenario"] == "stock_shortage"


def test_existing_routing_is_unchanged():
    assert client.post(f"{API}/query", json={"query": "Which machines use PT-001?"}).json()["intent"] == "impact_analysis"
    assert client.post(f"{API}/query", json={"query": "What is the status of order-demo-001?"}).json()["intent"] == "order_status"


# ---------------------------------------------------------------- existing Graph Insights / mitigation paths use the same gate

def test_graph_insights_and_mitigation_paths_use_the_gate():
    gi = client.get(f"{API}/parts/PT-026/graph-insights").json()["mitigation"]
    assert gi["alternatives"] == [] and "candidate" in gi["executive_summary"].lower() or "No candidate" in gi["executive_summary"]
    gi = client.get(f"{API}/parts/PT-007/graph-insights").json()["mitigation"]
    assert [a["part_id"] for a in gi["alternatives"]] == ["PT-015"] and "engineering review" in gi["executive_summary"]
    m = client.get(f"{API}/parts/PT-026/mitigation").json()
    assert "PT-027" not in str(m)


# ---------------------------------------------------------------- KPIs

def test_kpi_set_is_short_meaningful_and_labelled(session):
    out = client.get(f"{API}/kpis").json()
    by = {k["kpi"]: k for k in out["kpis"]}
    assert set(by) == {"Order traceability rate", "Master-data consistency rate", "Supplier-to-part coverage"}
    for k in out["kpis"] + out["demo_only"]:
        assert k["method"] and k.get("data_source") and "numerator" in k and "denominator" in k
    cov = by["Supplier-to-part coverage"]
    assert cov["numerator"] == 0 and cov["demo_numerator"] > 0     # real 0 %, demo links shown separately
    assert by["Master-data consistency rate"]["value_pct"] > 90
    assert "excluded_test_orders" in by["Order traceability rate"]
    assert [k["kpi"] for k in out["demo_only"]] == ["Stock-out exposure"] and out["demo_only"][0]["demo_only"] is True
    assert set(out) == {"note", "kpis", "demo_only"}
    assert "Customs" not in str(out) and "known status" not in str(out)


# ---------------------------------------------------------------- Phase 12: unverified store items run the demonstration lifecycle with a labelled DEMO- reference

def _demo_headers(test_run_id):
    return {"x-test-run-id": test_run_id, "x-test-user-id": "u", "x-test-role": "CUSTOMER"}


def test_demo_reference_runs_allocation_order_shipment_and_service_without_a_canonical_part(test_run_id):
    pn = "DEMO-WHEEL-LOADER-BUCKET"
    H = _demo_headers(test_run_id)
    rid = client.post("/api/v1/fulfilment-requests", json={"part_number": pn, "quantity": 1, "destination_branch_id": "DLR-045"}, headers=H).json()["id"]
    client.post(f"/api/v1/fulfilment-requests/{rid}/availability", json={"part_number": pn, "quantity": 1, "destination_branch_id": "DLR-045"}, headers=H)
    opt = client.post(f"/api/v1/fulfilment-requests/{rid}/options", headers=H).json()["options"][0]["id"]
    assert client.post(f"/api/v1/fulfilment-requests/{rid}/select-option", json={"option_id": opt}, headers={**H, "x-idempotency-key": f"k1-{test_run_id}"}).status_code == 200
    assert client.post(f"/api/v1/fulfilment-requests/{rid}/proceed-to-allocation", headers=H).status_code == 200
    assert client.post(f"/api/v1/fulfilment-requests/{rid}/allocation", headers={**H, "x-idempotency-key": f"a1-{test_run_id}"}).status_code == 200
    order = client.post(f"/api/v1/fulfilment-requests/{rid}/order", headers={**H, "x-idempotency-key": f"o1-{test_run_id}"})
    assert order.status_code == 200
    oid = order.json()["id"]
    sh = client.post("/api/v1/shipments", json={"order_id": oid, "service_tier": "STANDARD"}, headers={**H, "x-idempotency-key": f"s1-{test_run_id}"})
    assert sh.status_code == 200
    sid = sh.json()["shipment_id"]
    assert client.post(f"/api/v1/shipments/{sid}/dispatch", headers=H).status_code == 200
    assert client.post(f"/api/v1/shipments/{sid}/deliver", headers=H).status_code == 200
    job = client.post("/api/v1/service-jobs", json={"order_id": oid, "service_type": "PARTS_INSTALLATION"}, headers={**H, "x-idempotency-key": f"j1-{test_run_id}"})
    assert job.status_code == 200
    jid = job.json()["service_job_id"]
    for step in ("receive", "start", "install", "complete"):
        assert client.post(f"/api/v1/service-jobs/{jid}/{step}", headers=H).status_code == 200


def test_a_real_looking_unknown_part_number_is_still_rejected_at_allocation(test_run_id):
    """Only DEMO- references bypass the canonical Part; an unknown real-looking number must still fail."""
    H = _demo_headers(test_run_id)
    pn = "9999999X"
    rid = client.post("/api/v1/fulfilment-requests", json={"part_number": pn, "quantity": 1, "destination_branch_id": "DLR-045"}, headers=H).json()["id"]
    client.post(f"/api/v1/fulfilment-requests/{rid}/availability", json={"part_number": pn, "quantity": 1, "destination_branch_id": "DLR-045"}, headers=H)
    opt = client.post(f"/api/v1/fulfilment-requests/{rid}/options", headers=H).json()["options"][0]["id"]
    client.post(f"/api/v1/fulfilment-requests/{rid}/select-option", json={"option_id": opt}, headers={**H, "x-idempotency-key": f"k9-{test_run_id}"})
    client.post(f"/api/v1/fulfilment-requests/{rid}/proceed-to-allocation", headers=H)
    assert client.post(f"/api/v1/fulfilment-requests/{rid}/allocation", headers={**H, "x-idempotency-key": f"a9-{test_run_id}"}).status_code == 404
