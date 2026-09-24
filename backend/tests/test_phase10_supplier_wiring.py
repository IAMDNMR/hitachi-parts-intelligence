"""
backend/tests/test_phase10_supplier_wiring.py

Phase 10 — Supplier Graph Wiring and Graph Insights Supplier Risk Correction Test Suite.

Verifies:
1. Real supplier lookup
2. Supplier number lookup
3. Supplier country lookup
4. Supplier city lookup
5. Dealer + supplier network
6. Supplier + dealer shared city
7. Supplier + depot shared city
8. Supplier risk with no Supplier -> Part mapping (State B: NOT_CONNECTED)
9. No synthetic supplier leakage into real Supplier Risk
10. No fabricated Supplier -> Part relationship
11. No fabricated Supplier -> Dealer relationship
12. Critical multi-entity machine/part/supplier query (no generic Netherlands fallback)
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.intelligence import assistant
from app.modules.intelligence.providers import DeterministicLLMProvider

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_gemini(monkeypatch):
    monkeypatch.setattr(assistant, "get_llm_provider", lambda: DeterministicLLMProvider())


def ask(q, **kw):
    r = client.post("/api/v1/intelligence/query", json={"query": q, **kw})
    assert r.status_code == 200
    return r.json()


def test_01_real_supplier_master_record_count(neo4j_session):
    """1,720 real source-derived HCME SAP supplier records exist in Neo4j."""
    total = neo4j_session.run(
        "MATCH (s:Supplier {data_source: 'HCME_SAP_SUPPLIER_MASTER'}) RETURN count(s) AS n"
    ).single()["n"]
    assert total == 1720


def test_02_supplier_number_lookup():
    """Supplier number 0000100026 returns Thorburn Geiger SA in Lausanne, Switzerland."""
    r = ask("Show me supplier 0000100026.")
    assert r["intent"] == "supplier_lookup"
    suppliers = r["data"]["suppliers"]
    assert len(suppliers) == 1
    assert suppliers[0]["supplier_number"] == "0000100026"
    assert "THORBURN GEIGER" in suppliers[0]["name"].upper()
    assert suppliers[0]["city"] == "Lausanne"
    assert suppliers[0]["country"] == "CH"


def test_03_supplier_country_lookup():
    """Country lookup returns exact source-derived counts (NL=1131, DE=117)."""
    r_nl = ask("Which suppliers are in Netherlands?")
    assert r_nl["intent"] == "supplier_lookup"
    assert r_nl["evidence"]["total"] == 1131
    assert all(s["country"] == "NL" for s in r_nl["data"]["suppliers"])

    r_de = ask("Which suppliers are in Germany?")
    assert r_de["intent"] == "supplier_lookup"
    assert r_de["evidence"]["total"] == 117
    assert all(s["country"] == "DE" for s in r_de["data"]["suppliers"])


def test_04_supplier_city_lookup():
    """City lookup returns exact source-derived counts (Eindhoven=12, Oosterhout=34)."""
    r_eind = ask("Which suppliers are in Eindhoven?")
    assert r_eind["intent"] == "supplier_lookup"
    assert r_eind["evidence"]["total"] == 12

    r_oost = ask("Which suppliers are in Oosterhout?")
    assert r_oost["intent"] == "supplier_lookup"
    assert r_oost["evidence"]["total"] == 34


def test_05_dealer_supplier_network_derived_relationship():
    """Dealers and suppliers in Netherlands shows geographic colocation (SAME CITY - DERIVED)."""
    r = ask("Show me the dealers and suppliers in Netherlands.")
    assert r["intent"] == "dealer_supplier_network"
    assert r["evidence"]["dealer_count"] == 19
    assert r["evidence"]["supplier_count"] == 1131
    assert r["evidence"]["relationship"] == "SAME CITY — DERIVED"
    assert len(r["evidence"]["shared_cities"]) >= 9
    assert "SAME CITY — DERIVED" in r["answer"] or "geographic" in r["answer"].lower()


def test_06_supplier_dealer_shared_city_pellen_machines():
    """Pellen Machines in Veldhoven has 2 colocated suppliers (SAME CITY - DERIVED)."""
    r = ask("Which suppliers are in the same city as Pellen Machines?")
    assert r["intent"] == "supplier_lookup"
    assert r["evidence"]["city"] == "Veldhoven"
    assert r["evidence"]["suppliers_in_city"] == 2
    assert r["evidence"]["relationship"] == "SAME CITY — DERIVED"
    assert "SAME CITY — DERIVED" in r["answer"]
    assert "Pellen Machines" in r["answer"]


def test_07_supplier_depot_shared_city_oosterhout():
    """Oosterhout depot shares city with 34 suppliers (SAME CITY AS DEPOT - DERIVED)."""
    r = ask("Which suppliers are in the same city as the Oosterhout depot?")
    assert r["intent"] == "supplier_lookup"
    assert r["evidence"]["city"] == "Oosterhout"
    assert r["evidence"]["suppliers_in_city"] == 34
    assert r["evidence"]["relationship"] == "SAME CITY AS DEPOT — DERIVED"
    assert r["evidence"]["anchor_is_depot"] is True
    assert "SAME CITY AS DEPOT — DERIVED" in r["answer"]
    assert "depot" in r["answer"].lower()
    assert r["graph_path"] == ["Depot", "City", "Supplier"]


def test_08_supplier_risk_shows_labelled_demo_links():
    """Graph Insights shows the demo supplier links, clearly labelled SYNTHETIC_DEMO."""
    res = client.get("/api/v1/intelligence/parts/PT-045/graph-insights")
    assert res.status_code == 200
    risk = res.json()["supplier_risk"]
    assert risk["status"] == "CONNECTED" and risk["connected"] is True
    assert risk["supplier_master_count"] == 1720
    assert risk["part_suppliers"] and risk["provenance"] == "SYNTHETIC_DEMO"
    assert "SYNTHETIC DEMO" in risk["data_basis"]


def test_09_demo_supplier_links_are_flagged_synthetic():
    res = client.get("/api/v1/intelligence/parts/PT-045/graph-insights")
    risk = res.json()["supplier_risk"]
    assert all(s["synthetic"] for s in risk["part_suppliers"])


def test_10_no_fabricated_supplier_part_relationship(neo4j_session):
    """Authoritative HCME supplier master records have zero fabricated SUPPLIED_BY edges."""
    bad_edges = neo4j_session.run(
        """
        MATCH (s:Supplier {data_source: 'HCME_SAP_SUPPLIER_MASTER'})-[r:SUPPLIED_BY|SUPPLIES]-()
        RETURN count(r) AS n
        """
    ).single()["n"]
    assert bad_edges == 0


def test_11_no_fabricated_supplier_dealer_relationship(neo4j_session):
    """No direct commercial relationship edge exists between Supplier and DealerBranch."""
    bad_edges = neo4j_session.run(
        """
        MATCH (s:Supplier)-[r:PARTNER|SERVES|SUPPLIES]->(d:DealerBranch)
        RETURN count(r) AS n
        """
    ).single()["n"]
    assert bad_edges == 0


def test_12_critical_multi_entity_machine_part_supplier_query():
    """Query 'buckets suppliers for my medium excavator in Netherlands' must NOT dump 1,131 NL suppliers."""
    r = ask("buckets suppliers for my medium excavator in Netherlands")
    assert r["intent"] == "machine_supplier_by_part_category"
    assert r["evidence"]["supplier_part_mapping"]["status"] == "NOT_CONNECTED"
    assert "Supplier-to-part mapping is not recorded" in r["answer"] or "not recorded" in r["answer"]
    # Data suppliers must be empty — no generic fallback
    assert len(r["data"]["suppliers"]) == 0
    assert "country_suppliers" not in r["data"]
