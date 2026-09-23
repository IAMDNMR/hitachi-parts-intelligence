"""
backend/tests/test_phase7_graph_intelligence.py

Phase 7 Graph Intelligence Extension tests:
- Impact Intelligence (Machines, Families, Categories, Assemblies)
- Compliance Intelligence (Real vs Synthetic boundaries, Unknown handling)
- Source / Supplier Risk Intelligence (Single source, dependency counts, buffers)
- Deterministic Scoring (Compatibility & Mitigation mathematical formulas)
- Mitigation Intelligence (Workflow, Ranking, AI explanation)
- Part Matching (Technical similarity)
- Assistant Natural Language Query Router
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.intelligence.compliance import get_compliance_analysis
from app.modules.intelligence.impact import get_impact_analysis
from app.modules.intelligence.matching import match_parts
from app.modules.intelligence.mitigation import get_mitigation_analysis
from app.modules.intelligence.scoring import (
    calculate_compatibility_score,
    calculate_mitigation_score,
)
from app.modules.intelligence.source_risk import get_source_risk_analysis

client = TestClient(app)

REAL_PART_ID = "PT-001"  # 4663907 Starter Battery


def test_deterministic_scoring_formulas():
    part_a = {
        "part_category": "Electrical",
        "part_subcategory": "Battery",
        "component_assembly": "Battery (installed in Upperstructure)",
        "genuine_hitachi_part": "Yes",
    }
    part_b = {
        "part_category": "Electrical",
        "part_subcategory": "Battery",
        "component_assembly": "Battery (installed in Upperstructure)",
        "genuine_hitachi_part": "Yes",
    }
    machines_a = {"MC-044", "MC-045", "MC-046"}
    machines_b = {"MC-044", "MC-045", "MC-047"}

    score, breakdown = calculate_compatibility_score(part_a, part_b, machines_a, machines_b)
    assert 0.0 <= score <= 1.0
    assert breakdown["category_match"]["matched"] is True
    assert breakdown["subcategory_match"]["matched"] is True
    assert breakdown["assembly_context"]["status"] == "EXACT_MATCH"
    assert breakdown["machine_overlap"]["common_models_count"] == 2
    # Jaccard = 2/4 = 0.5; points = 0.5 * 0.35 = 0.175
    # Total = 0.25 + 0.15 + 0.15 + 0.175 + 0.10 = 0.825
    assert score == pytest.approx(0.825, 0.01)

    # Mitigation score calculation
    mitig_score, mitig_breakdown = calculate_mitigation_score(
        compatibility_score=score,
        availability_status="CONFIRMED",
        compliance_status="COMPLIANT",
        source_risk_level="LOW",
        confidence="HIGH",
    )
    # Comp: 0.825 * 0.40 = 0.33
    # Avail: 1.0 * 0.30 = 0.30
    # Compl: 1.0 * 0.20 = 0.20
    # Risk: 1.0 * 0.10 = 0.10
    # Total = 0.93
    assert 0.0 <= mitig_score <= 1.0
    assert mitig_score == pytest.approx(0.93, 0.01)


def test_impact_analysis_real_part(neo4j_session):
    impact = get_impact_analysis(neo4j_session, REAL_PART_ID)
    assert impact["part_id"] == REAL_PART_ID
    assert impact["total_affected_machines_count"] > 0
    assert len(impact["product_families"]) > 0
    assert len(impact["affected_machines"]) > 0
    assert impact["insufficient_evidence"] is False


def test_compliance_analysis_real_vs_synthetic(neo4j_session):
    # PT-001 carries real EU battery compliance from SRC-039
    comp_real = get_compliance_analysis(neo4j_session, REAL_PART_ID)
    assert comp_real["part_id"] == REAL_PART_ID
    assert comp_real["has_graph_evidence"] is True
    assert comp_real["overall_status"] == "COMPLIANT"
    assert any(not r.get("synthetic") for r in comp_real["requirements"])

    # PT-046 carries synthetic Stage V NRMM compliance
    comp_synth = get_compliance_analysis(neo4j_session, "PT-046")
    assert comp_synth["has_graph_evidence"] is True
    assert any(r.get("synthetic") is True for r in comp_synth["requirements"])

    # Non-existent or unlinked part returns UNKNOWN
    comp_unk = get_compliance_analysis(neo4j_session, "PT-020")
    assert comp_unk["overall_status"] == "UNKNOWN"
    assert comp_unk["has_graph_evidence"] is False


def test_source_risk_analysis(neo4j_session):
    risk = get_source_risk_analysis(neo4j_session, REAL_PART_ID)
    assert risk["part_id"] == REAL_PART_ID
    assert risk["risk_level"] in ("LOW", "MEDIUM", "HIGH", "UNKNOWN")
    assert len(risk["distinct_sources"]) > 0
    assert risk["confidence"] == "HIGH"


def test_mitigation_workflow_ranking(neo4j_session):
    # Hard filters (orderable part, same specific type, shared fitment): the default test part has no candidate at all...
    none = get_mitigation_analysis(neo4j_session, REAL_PART_ID)
    assert none["part_id"] == REAL_PART_ID and none["options_count"] == 0 and len(none["executive_summary"]) > 0
    # ...whereas PT-007 shares fitment with another starter battery (PT-015), which is a candidate for engineering review.
    mitig = get_mitigation_analysis(neo4j_session, "PT-007")
    assert mitig["part_id"] == "PT-007"
    assert mitig["options_count"] > 0
    options = mitig["mitigation_options"]
    assert [o["candidate_part_id"] for o in options] == ["PT-015"]
    # Ensure options are sorted by mitigation score descending
    scores = [o["mitigation_score"] for o in options]
    assert scores == sorted(scores, reverse=True)
    assert len(mitig["executive_summary"]) > 0


def test_technical_part_matching(neo4j_session):
    matches = match_parts(neo4j_session, REAL_PART_ID, limit=3)
    assert matches["target_part"]["part_id"] == REAL_PART_ID
    assert len(matches["matches"]) > 0
    for m in matches["matches"]:
        assert "similarity_score" in m
        assert "similarity_percentage" in m
        assert 0.0 <= m["similarity_score"] <= 1.0


def test_intelligence_query_router_api(neo4j_session):
    # 1. Order status query
    res_order = client.post("/api/v1/intelligence/query", json={"query": "What is the status of order-demo-001?"})
    assert res_order.status_code == 200
    assert res_order.json()["intent"] == "order_status"

    # 2. Impact query
    res_impact = client.post("/api/v1/intelligence/query", json={"query": "Which machines use PT-001?"})
    assert res_impact.status_code == 200
    assert res_impact.json()["intent"] == "impact_analysis"

    # 3. Compliance query
    res_comp = client.post("/api/v1/intelligence/query", json={"query": "What compliance information is available for PT-001?"})
    assert res_comp.status_code == 200
    assert res_comp.json()["intent"] == "compliance_analysis"

    # 4. Mitigation query
    res_mitig = client.post("/api/v1/intelligence/query", json={"query": "What mitigation options do we have for PT-001?"})
    assert res_mitig.status_code == 200
    assert res_mitig.json()["intent"] == "mitigation_analysis"


def test_all_new_intelligence_get_endpoints(neo4j_session):
    for endpoint in ("impact", "compliance", "source-risk", "mitigation"):
        res = client.get(f"/api/v1/intelligence/parts/{REAL_PART_ID}/{endpoint}")
        assert res.status_code == 200, f"Endpoint {endpoint} failed with {res.status_code}"
        assert res.json()["part_id"] == REAL_PART_ID
