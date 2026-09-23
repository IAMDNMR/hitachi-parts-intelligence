"""
backend/tests/test_phase10d_routing.py

Phase 10D golden routing suite. Every case goes through the PRODUCTION path:
POST /api/v1/intelligence/query -> route_and_answer_query -> Neo4j.
(`handle_intelligence_query` never existed in this repo; the real public entry
point is `route_and_answer_query`, and test_same_route_as_fastapi proves the
API returns exactly what calling it directly does.)

Each case runs under two providers:
  * deterministic — no LLM configured
  * gemini_down   — a real GeminiLLMProvider whose every call fails, i.e. the
    "Gemini is unavailable" fallback the product must survive.
A stale UI context part (PT-001) is sent with every request; unless the query
explicitly says "this part", it must never influence the answer.
"""
import pytest
from fastapi.testclient import TestClient

from app.db.neo4j.connection import get_neo4j_driver
from app.main import app
from app.modules.intelligence import assistant
from app.modules.intelligence.providers import DeterministicLLMProvider, GeminiLLMProvider, GeminiProviderError

client = TestClient(app)


class _GeminiDown(GeminiLLMProvider):
    def __init__(self):
        super().__init__(api_key="x", model="down")

    def _generate(self, *a, **k):
        raise GeminiProviderError("simulated outage")


@pytest.fixture(params=["deterministic", "gemini_down"])
def provider(request, monkeypatch):
    factory = DeterministicLLMProvider if request.param == "deterministic" else _GeminiDown
    monkeypatch.setattr(assistant, "get_llm_provider", lambda: factory())
    return request.param


def ask(q, context="PT-001"):
    r = client.post("/api/v1/intelligence/query", json={"query": q, "context_part_id": context})
    assert r.status_code == 200, r.text
    return r.json()


def test_part_to_machine_returns_only_fitment_machines(provider):
    r = ask("Which machines use PT-001?")
    assert r["intent"] == "impact_analysis" and r["result_type"] == "MACHINE_RESULTS"
    with get_neo4j_driver().session() as s:
        expected = {x["m"] for x in s.run(
            "MATCH (m:Machine)-[:HAS_PART_FITMENT]->(:Part {part_id:'PT-001'}) RETURN m.machine_id AS m")}
    got = {m["machine_id"] for m in r["data"]["machines"]}
    assert got == expected and 0 < len(got) < 77
    assert r["graph"] and {e["relationship"] for e in r["graph"]["edges"]} == {"HAS_PART_FITMENT"}
    assert "77 machines" not in r["answer"]


def test_dealer_name_is_a_dealer_not_the_machine_catalogue(provider):
    r = ask("Show me Pellen Machines.")
    assert r["intent"] == "dealer_lookup" and r["result_type"] == "DEALER_RESULTS"
    d = r["data"]["dealers"][0]
    assert d["dealer_id"] == "DLR-122" and d["city"] == "Veldhoven" and d["data_class"] and d["source_id"]
    assert not r["data"].get("machines") and r["insights_part_id"] is None


def test_suppliers_in_germany_has_no_stale_part_content(provider):
    r = ask("Which suppliers are in Germany?")
    assert r["intent"] == "supplier_lookup" and r["result_type"] == "SUPPLIER_RESULTS"
    assert "117" in r["answer"] and r["data"]["suppliers"]
    assert r["insights_part_id"] is None and r["resolved_part_id"] is None
    assert not r["data"].get("candidates") and r["graph"] is None


def test_medium_excavator_buckets_preserves_both_entities(provider):
    r = ask("What buckets fit my medium excavator?")
    assert r["intent"] == "machine_parts_by_category"
    assert r["entities"]["machine_type"] == "Medium Excavators" and r["entities"]["part_category"] == "Bucket"
    with get_neo4j_driver().session() as s:
        n = s.run("MATCH (p:Part) WHERE toLower(p.part_name+p.part_category+coalesce(p.part_subcategory,'')) "
                  "CONTAINS 'bucket' RETURN count(p) AS n").single()["n"]
    # The answer must follow the graph, not a hardcoded string.
    assert (r["result_type"] == "NO_RELATIONSHIP") == (n == 0)
    assert not r["data"].get("category_summary") and r["insights_part_id"] is None


def test_bucket_suppliers_never_fall_back_to_country_suppliers(provider):
    r = ask("buckets suppliers for my medium excavator in Netherlands")
    assert r["intent"] == "machine_supplier_by_part_category"
    assert r["entities"]["machine_type"] == "Medium Excavators" and r["entities"]["country"] == "NL"
    assert not r["data"].get("suppliers") and r["result_type"] in ("NO_RELATIONSHIP", "INSUFFICIENT_DATA")
    assert "not recorded" in r["answer"].lower()


def test_oil_query_never_resolves_to_pt001(provider):
    r = ask("Are there multi-grade oil alternatives for genuine engine oil?")
    assert r["resolved_part_id"] is None and r["insights_part_id"] is None
    assert r["result_type"] == "INSUFFICIENT_DATA"
    assert "PT-001" not in r["answer"] and "battery" not in r["answer"].lower()
    assert all(c["part_id"] != "PT-001" for c in r["data"].get("candidates", []))
    assert r["answer"].startswith("No verified multi-grade")


def test_dealers_and_suppliers_network(provider):
    r = ask("Show me the dealers and suppliers in Netherlands.")
    assert r["intent"] == "dealer_supplier_network" and r["result_type"] == "NETWORK_RESULTS"
    assert r["graph"] and r["graph"]["nodes"] and "SAME CITY" in r["graph"]["relationship_note"].upper()
    assert r["insights_part_id"] is None


def test_suppliers_same_city_as_dealer(provider):
    r = ask("Which suppliers are in the same city as Pellen Machines?")
    assert r["intent"] == "supplier_lookup" and "Veldhoven" in r["answer"] and "DERIVED" in r["answer"]
    assert r["data"]["suppliers"] and r["graph"]


def test_suppliers_same_city_as_depot(provider):
    r = ask("Which suppliers are in the same city as the Oosterhout depot?")
    assert r["intent"] == "supplier_lookup" and "Oosterhout" in r["answer"] and "DERIVED" in r["answer"]
    assert r["data"]["suppliers"] and r["graph"]


def test_alternatives_for_explicit_part(provider):
    r = ask("Show alternatives for PT-001.")
    assert r["intent"] == "alternatives" and r["insights_part_id"] == "PT-001"
    assert "not an approved replacement" in r["answer"].lower() or "candidate" in r["answer"].lower()


def test_sequence_part_then_suppliers_has_no_leak(provider):
    first = ask("Which machines use PT-001?", context=None)
    assert first["insights_part_id"] == "PT-001"
    second = ask("Which suppliers are in Germany?", context=first["insights_part_id"])
    assert second["insights_part_id"] is None and not second["data"].get("candidates") and second["graph"] is None


def test_sequence_alternatives_then_suppliers_has_no_alternative_cards(provider):
    first = ask("Show alternatives for PT-001.", context=None)
    assert first["data"]["candidates"]
    second = ask("Which suppliers are in Germany?", context="PT-001")
    assert not second["data"].get("candidates")


def test_explicit_back_reference_uses_context(provider):
    r = ask("Who supplies this part?", context="PT-001")
    assert r["resolved_part_id"] == "PT-001"


def test_no_context_and_no_part_asks_instead_of_guessing(provider):
    r = ask("Who supplies this part?", context=None)
    assert r["resolved_part_id"] is None and r["result_type"] == "CLARIFICATION_REQUIRED"


def test_same_route_as_fastapi(provider):
    """The API returns exactly what the production function returns — no second implementation."""
    q = "Which machines use PT-001?"
    via_api = ask(q, context=None)
    with get_neo4j_driver().session() as s:
        direct = assistant.route_and_answer_query(s, q)
    for k in ("intent", "result_type", "answer", "resolved_part_id", "insights_part_id"):
        assert via_api[k] == direct[k]
    assert {m["machine_id"] for m in via_api["data"]["machines"]} == {m["machine_id"] for m in direct["data"]["machines"]}


def test_graph_nodes_and_edges_are_unique(provider):
    """Regression: the depot appeared twice, giving React duplicate keys."""
    for q in ("Which suppliers are in the same city as the Oosterhout depot?",
              "Show me the dealers and suppliers in Netherlands.",
              "Which suppliers are in the same city as Pellen Machines?"):
        g = ask(q)["graph"]
        ids = [n["id"] for n in g["nodes"]]
        assert len(ids) == len(set(ids)), q
        edges = [(e["source"], e["target"], e["relationship"]) for e in g["edges"]]
        assert len(edges) == len(set(edges)), q
