"""
backend/tests/test_phase10_graph_insights.py

Phase 10 — the four-tab Graph Insights response is built from the live graph
and every section names its data basis.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_graph_insights_four_tabs_for_main_hydraulic_pump():
    d = client.get("/api/v1/intelligence/parts/PT-045/graph-insights").json()
    assert set(d) == {"part", "impact", "compliance", "supplier_risk", "mitigation"}

    impact = d["impact"]
    assert impact["affected_machines"] == len(impact["machines"]) > 0
    assert impact["total_bom_qty"] == sum(a["qty"] for a in impact["assemblies"])
    assert all(a["criticality"] == "high" for a in impact["critical_paths"])

    risk = d["supplier_risk"]
    assert risk["status"] == "NOT_CONNECTED"
    assert risk["connected"] is False
    assert risk["part_suppliers"] == [], "No synthetic demo suppliers appear in real supplier risk"
    assert risk["concentration"] == [], "No fake concentration numbers in real supplier risk"
    assert risk["supplier_master_count"] == 1720
    assert "no supplier-to-part" in risk["data_basis"]
    assert risk["spof"]["is_spof"] is False
    assert len(risk["geographic_distribution"]) > 0
    assert not any("Demo" in s["name"] for s in risk["sample_suppliers"])

    held = {r["name"] for r in d["compliance"]["requirements"] if r["held"]}
    assert not any(g["requirement"] in held and g["required_by"] == "this part" for g in d["compliance"]["gaps"])

    m = d["mitigation"]
    assert m["steps"][0] == "Analyse impact" and len(m["steps"]) == 5
    assert all(o["part_id"] != "PT-045" for o in m["alternatives"])
    assert m["alternatives"] == sorted(m["alternatives"], key=lambda o: (-o["mitigation_score"], -o["similarity_pct"]))

    for section in ("impact", "compliance"):
        assert "SYNTHETIC DEMO" in d[section]["data_basis"]
    assert "HCME supplier master" in d["supplier_risk"]["data_basis"]
    assert "no supplier-to-part" in d["supplier_risk"]["data_basis"]


def test_graph_insights_unknown_part_is_404():
    assert client.get("/api/v1/intelligence/parts/PT-999/graph-insights").status_code == 404
