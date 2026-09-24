"""
backend/tests/test_phase10_assistant.py

Phase 10 — Parts Intelligence question answering over the live graph, with
Gemini disabled (deterministic understanding + answers) so the suite never
depends on, or spends, the external LLM quota. The live Gemini run is the
matrix in docs/data/neo4j/scripts/phase10_nl_test_matrix.py.
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


def test_nearest_dealer_to_eindhoven_is_ranked_by_distance():
    r = ask("Who is the nearest Hitachi dealer to Eindhoven?")
    assert r["intent"] == "nearest_dealer"
    km = [d["distance_km"] for d in r["data"]["dealers"]]
    assert km == sorted(km)
    assert r["data"]["dealers"][0]["dealer_id"] == "DLR-122"  # Pellen Machines, Veldhoven


def test_nearest_dealer_without_location_asks_for_one():
    r = ask("Which is the nearest dealer to me in the Netherlands?")
    assert r["needs_clarification"] and "postcode" in r["answer"].lower()
    assert not r["data"].get("dealers")


def test_netherlands_dealers_come_from_the_graph():
    r = ask("Which Hitachi dealers are in the Netherlands?")
    assert r["intent"] == "dealer_list"
    assert len(r["data"]["dealers"]) == 13  # 19 feed entries minus 6 account managers
    assert all(d["country"] == "NL" for d in r["data"]["dealers"])


def test_supplier_risk_reports_not_connected_honestly():
    r = ask("Is PT-045 single-source?")
    assert r["intent"] == "supplier_risk"
    assert r["evidence"]["status"] == "NOT_CONNECTED"
    assert "not connected" in r["answer"].lower()
    assert "demo" not in r["answer"].lower()


def test_order_journey_is_multi_hop():
    r = ask("Where is my order order-demo-001 and which dealer receives it?")
    assert r["intent"] == "order_status"
    assert r["evidence"]["dealer"]["dealer_id"] == "DLR-019"
    assert r["evidence"]["service_job"]["status"] == "COMPLETED"
    assert "synthetic" in r["answer"].lower()


def test_pricing_is_reported_not_connected():
    r = ask("What does PT-001 cost?")
    assert r["intent"] == "unsupported"
    assert "not" in r["answer"].lower()


def test_follow_up_uses_context_part():
    r = ask("Is this part single-source?", context_part_id="PT-001")
    assert r["resolved_part_id"] == "PT-001"


def test_keyword_search_returns_cards_without_llm():
    r = ask("track roller")
    assert r["intent"] == "part_search"
    assert r["data"]["candidates"][0]["part_id"] in {"PT-051", "PT-059"}
    assert r["pipeline"]["extraction"] == "deterministic"


def test_what_machines_do_we_have_returns_catalogue_summary():
    r = ask("What machines do we have?")
    assert r["intent"] == "machine_list"
    assert r["evidence"]["total_machines"] == 77
    assert "77" in r["answer"]


def test_medium_excavators_returns_exact_models():
    r = ask("Show me the medium excavators.")
    assert r["intent"] == "machine_list"
    assert r["evidence"]["count"] == 16
    assert "16" in r["answer"]

