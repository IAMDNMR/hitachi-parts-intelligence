"""
backend/tests/test_phase10e_catalog.py

Phase 10E/10F: the question catalogue served from Aura, its routing, and the fitment gap fill.
"""
import pytest
from fastapi.testclient import TestClient

from app.db.neo4j.connection import get_neo4j_driver
from app.main import app
from app.modules.intelligence import assistant
from app.modules.intelligence.providers import DeterministicLLMProvider

client = TestClient(app)


@pytest.fixture(autouse=True)
def _deterministic(monkeypatch):
    monkeypatch.setattr(assistant, "get_llm_provider", lambda: DeterministicLLMProvider())


def _catalog():
    r = client.get("/api/v1/intelligence/catalog")
    assert r.status_code == 200
    return r.json()


def test_catalog_endpoint_lists_only_verified_categories_and_questions():
    cats = _catalog()["categories"]
    names = {c["name"] for c in cats}
    assert {"Parts Search", "Dealers", "Relationships", "Suppliers", "Machines & Fleet", "Orders & Service"} <= names
    questions = [q for c in cats for q in c["questions"]]
    assert len(questions) >= 30
    assert len({q["question_id"] for q in questions}) == len(questions)
    assert all(q["text"] and q["intent"] for q in questions)


def test_every_catalogue_question_routes_to_its_stored_intent():
    for c in _catalog()["categories"]:
        for q in c["questions"]:
            r = client.post("/api/v1/intelligence/query", json={"query": q["text"]}).json()
            assert r["catalog_question_id"] == q["question_id"], q["text"]
            assert r["intent"] == q["intent"], f"{q['question_id']}: {r['intent']} != {q['intent']}"


def test_catalogue_is_wired_to_real_nodes():
    with get_neo4j_driver().session() as s:
        row = s.run("""MATCH (t:QuestionTemplate {question_id:'R05'})-[:ABOUT_PART]->(p:Part {part_id:'PT-001'})
                       RETURN count(*) AS n""").single()
        assert row["n"] == 1
        sup = s.run("MATCH (r:RelationshipType {name:'SUPPLIED_BY'}) RETURN r.real_edges AS real").single()
        assert sup["real"] == 0  # supplier-to-part links are synthetic demo only


def test_no_enabled_template_is_unverified():
    with get_neo4j_driver().session() as s:
        n = s.run("MATCH (q:QuestionTemplate) WHERE q.enabled = true AND coalesce(q.verified,false) = false RETURN count(q) AS n").single()["n"]
    assert n == 0


def test_every_catalogue_part_has_fitment():
    """Phase 10F: no catalogue part may be left without a fitment edge."""
    with get_neo4j_driver().session() as s:
        missing = s.run("""MATCH (p:Part) WHERE p.part_id STARTS WITH 'PT-' AND p.testRunId IS NULL AND NOT (:Machine)-[:HAS_PART_FITMENT]->(p)
                           RETURN p.part_id AS id ORDER BY id""").value()
    assert missing == [], missing


def test_alternatives_are_the_same_kind_of_component():
    r = client.post("/api/v1/intelligence/query", json={"query": "Are there alternatives for PT-045?"}).json()
    assert "PT-044" not in r["answer"]  # a control valve is not an alternative to a pump


def test_match_label_is_exact_only_at_100_percent():
    r = client.post("/api/v1/intelligence/query", json={"query": "What hydraulic parts fit ZX210LC-7?"}).json()
    for c in r["data"]["candidates"]:
        if c["match_pct"] < 100:
            assert not c["assessment"].startswith("Exact match")
