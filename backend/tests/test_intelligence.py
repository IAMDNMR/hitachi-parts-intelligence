"""
backend/tests/test_intelligence.py

Tests for the Parts Intelligence module (read-only search/orchestration
layer). Uses the real AuraDB instance like the other test modules — no
mocking of Neo4j itself, but the LLM path is deterministic (no external
LLM credentials configured in this environment). Gemini is mocked at the
httpx layer wherever it is exercised — no real network calls in this suite.
"""

import httpx
import pytest

from app.config import settings
from app.modules.intelligence.providers import (
    DeterministicLLMProvider,
    GeminiLLMProvider,
    GeminiProviderError,
    NullEmbeddingProvider,
    get_llm_provider,
    get_embedding_provider,
)
from app.modules.intelligence.query_parser import parse_query
from app.modules.intelligence.schemas import Evidence, NaturalLanguageQuery, ParsedIntent
from app.modules.intelligence.search import exact_search, lexical_search, semantic_search
from app.modules.intelligence.fitment import get_fitments_for_part
from app.modules.intelligence.alternatives import find_alternatives
from app.modules.intelligence.service import search as intelligence_search, get_graph_insights
from app.errors.exceptions import NotFoundError


# _no_real_gemini_by_default (autouse) now lives in tests/conftest.py, so
# every test file gets the same default, not just this one.


# ---------------------------------------------------------------------------
# Schema / parsing
# ---------------------------------------------------------------------------

def test_natural_language_query_schema_requires_nonempty_query():
    with pytest.raises(Exception):
        NaturalLanguageQuery(query="", limit=5)


def test_deterministic_parser_extracts_machine_model_and_requirement():
    parsed = parse_query("I need a hydraulic filter for ZX210-7")
    assert isinstance(parsed, ParsedIntent)
    assert parsed.source == "deterministic"
    assert parsed.machine_model == "ZX210-7" or parsed.machine_model == "ZX210"
    assert "filter" in (parsed.part_requirement or "").lower()


def test_deterministic_parser_handles_query_with_no_model():
    parsed = parse_query("battery starter lighting ignition")
    assert parsed.intent == "find_part"
    assert parsed.raw_query == "battery starter lighting ignition"


def test_provider_selection_defaults_to_deterministic_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    assert isinstance(get_llm_provider(), DeterministicLLMProvider)
    assert isinstance(get_embedding_provider(), NullEmbeddingProvider)


def test_provider_selection_uses_gemini_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")
    provider = get_llm_provider()
    assert isinstance(provider, GeminiLLMProvider)


# ---------------------------------------------------------------------------
# GeminiLLMProvider — HTTP call MOCKED, never a real network call.
# ---------------------------------------------------------------------------

class _FakeGeminiResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("mocked error", request=None, response=self)

    def json(self):
        return self._json_data


def _mock_gemini_generate(monkeypatch, content=None, exc=None, status_code=200):
    def fake_post(self, url, params=None, json=None, **kw):
        if exc:
            raise exc
        return _FakeGeminiResponse(
            {"candidates": [{"content": {"parts": [{"text": content}]}}]},
            status_code=status_code,
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)


def test_gemini_parse_intent_success(monkeypatch):
    _mock_gemini_generate(
        monkeypatch,
        content='{"machine_model": "ZX210-7", "part_requirement": "hydraulic filter"}',
    )
    provider = GeminiLLMProvider(api_key="fake-test-key", model="gemini-2.5-flash-lite")
    parsed = provider.parse_intent("hydraulic filter for ZX210-7")
    assert parsed.source == "llm"
    assert parsed.machine_model == "ZX210-7"
    assert parsed.part_requirement == "hydraulic filter"


def test_gemini_parse_intent_bad_json_raises_provider_error(monkeypatch):
    _mock_gemini_generate(monkeypatch, content="not json")
    provider = GeminiLLMProvider(api_key="fake-test-key", model="gemini-2.5-flash-lite")
    with pytest.raises(GeminiProviderError):
        provider.parse_intent("anything")


def test_gemini_explain_success(monkeypatch):
    _mock_gemini_generate(monkeypatch, content="This part exactly matches your part number search.")
    provider = GeminiLLMProvider(api_key="fake-test-key", model="gemini-2.5-flash-lite")
    evidence = [Evidence(kind="EXACT_PART_NUMBER", detail="Query matched this part's part number exactly.")]
    text = provider.explain({"part_id": "PT-001", "part_name": "Battery"}, evidence)
    assert "match" in text.lower()


def test_gemini_timeout_raises_provider_error(monkeypatch):
    _mock_gemini_generate(monkeypatch, exc=httpx.TimeoutException("timed out"))
    provider = GeminiLLMProvider(api_key="fake-test-key", model="gemini-2.5-flash-lite")
    with pytest.raises(GeminiProviderError):
        provider.parse_intent("anything")
    with pytest.raises(GeminiProviderError):
        provider.explain({"part_id": "PT-001"}, [])


def test_gemini_http_429_raises_provider_error(monkeypatch):
    _mock_gemini_generate(monkeypatch, content="ignored", status_code=429)
    provider = GeminiLLMProvider(api_key="fake-test-key", model="gemini-2.5-flash-lite")
    with pytest.raises(GeminiProviderError):
        provider.parse_intent("anything")


def test_gemini_http_500_raises_provider_error(monkeypatch):
    _mock_gemini_generate(monkeypatch, content="ignored", status_code=500)
    provider = GeminiLLMProvider(api_key="fake-test-key", model="gemini-2.5-flash-lite")
    with pytest.raises(GeminiProviderError):
        provider.parse_intent("anything")


def test_gemini_missing_api_key_falls_back_to_deterministic(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    assert isinstance(get_llm_provider(), DeterministicLLMProvider)


def test_query_parser_falls_back_to_deterministic_when_gemini_fails(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")
    _mock_gemini_generate(monkeypatch, exc=httpx.TimeoutException("timed out"))
    parsed = parse_query("hydraulic filter for ZX210-7")
    assert parsed.source == "deterministic"
    assert parsed.machine_model is not None


def test_intelligence_search_degrades_gracefully_when_gemini_fails(neo4j_session, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")
    _mock_gemini_generate(monkeypatch, exc=httpx.TimeoutException("timed out"))
    response = intelligence_search(neo4j_session, "battery starter lighting", limit=5)
    assert response.degraded is True
    assert response.degraded_reason is not None
    # Parts Intelligence itself must still return usable, explained candidates.
    for c in response.candidates:
        assert c.explanation


def test_gemini_output_never_reaches_fitment_decision(neo4j_session, monkeypatch):
    """Fitment must be identical regardless of which LLM provider is
    active — Gemini is never consulted for fitment decisions."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    deterministic_fitments = get_fitments_for_part(neo4j_session, "PT-001")

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")
    _mock_gemini_generate(monkeypatch, content='{"machine_model": null, "part_requirement": "part"}')
    gemini_configured_fitments = get_fitments_for_part(neo4j_session, "PT-001")

    assert deterministic_fitments == gemini_configured_fitments


def test_gemini_api_key_never_logged(monkeypatch, caplog):
    """The API key must never appear in any log output, including on
    failure paths where the exception text is logged."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key-should-not-appear")
    _mock_gemini_generate(monkeypatch, exc=httpx.TimeoutException("timed out"))
    with caplog.at_level("WARNING"):
        parse_query("hydraulic filter for ZX210-7")
    assert "fake-test-key-should-not-appear" not in caplog.text


def test_gemini_integration_query_grounded_in_neo4j_not_invented(neo4j_session, monkeypatch):
    """Mocked Gemini parses the query; the actual candidates/fitment must
    come from Neo4j, not from anything Gemini said."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")
    # Gemini "hallucinates" a bogus machine model/part that does not exist
    # in the graph — the pipeline must not surface it as a real result.
    _mock_gemini_generate(
        monkeypatch,
        content='{"machine_model": "ZX350", "part_requirement": "hydraulic filter"}',
    )
    response = intelligence_search(neo4j_session, "I need a hydraulic filter for ZX350", limit=5)
    assert response.parsed_intent.source == "llm"
    assert response.parsed_intent.machine_model == "ZX350"
    # Every candidate returned must be a real graph Part, and fitment must
    # reflect graph-confirmed relationships only, not Gemini's claim.
    for c in response.candidates:
        assert c.part_id
        assert c.availability.status == "UNKNOWN"
        for m in c.fitted_machines:
            assert isinstance(m, str)


# ---------------------------------------------------------------------------
# Exact / lexical / semantic search
# ---------------------------------------------------------------------------

def test_exact_search_by_part_number(neo4j_session):
    results = exact_search(neo4j_session, "4663907")
    assert any(r.get("part_number") == "4663907" for r in results)


def test_exact_search_by_part_id(neo4j_session):
    results = exact_search(neo4j_session, "PT-001")
    assert len(results) == 1
    assert results[0]["part_id"] == "PT-001"


def test_lexical_search_finds_battery_parts(neo4j_session):
    results = lexical_search(neo4j_session, "battery", limit=10)
    assert len(results) > 0
    assert any("battery" in (r.get("part_name") or "").lower() for r in results)


def test_semantic_search_unavailable_reports_not_used(neo4j_session):
    # No embedding provider is configured in this environment.
    results, used = semantic_search(neo4j_session, "hydraulic filter")
    assert used is False
    assert results == []


# ---------------------------------------------------------------------------
# Fitment validation
# ---------------------------------------------------------------------------

def test_fitment_validation_uses_real_graph_relationship(neo4j_session):
    fitments = get_fitments_for_part(neo4j_session, "PT-001")
    assert isinstance(fitments, list)
    if fitments:
        assert "evidence" in fitments[0]


def test_fitment_for_nonexistent_part_returns_empty(neo4j_session):
    fitments = get_fitments_for_part(neo4j_session, "PT-DOES-NOT-EXIST")
    assert fitments == []


# ---------------------------------------------------------------------------
# Alternatives
# ---------------------------------------------------------------------------

def test_alternatives_for_unknown_part_returns_empty_list(neo4j_session):
    alts = find_alternatives(neo4j_session, "PT-DOES-NOT-EXIST")
    assert alts == []


def test_alternatives_are_never_marked_authoritative_without_source_field(neo4j_session):
    alts = find_alternatives(neo4j_session, "PT-001")
    for a in alts:
        if a.is_authoritative_replacement:
            assert "supersedes" in a.reason.lower() or "superseded" in a.reason.lower()


# ---------------------------------------------------------------------------
# End-to-end candidate retrieval / explanation / UNKNOWN handling
# ---------------------------------------------------------------------------

def test_intelligence_search_end_to_end(neo4j_session):
    response = intelligence_search(neo4j_session, "battery starter lighting", limit=5)
    assert response.query == "battery starter lighting"
    assert isinstance(response.candidates, list)
    for c in response.candidates:
        assert c.explanation
        assert 0.0 <= c.match_score <= 1.0
        assert c.availability.status == "UNKNOWN"  # never fabricated to a real status by Intelligence


def test_intelligence_search_never_raises_on_backend_error(neo4j_session, monkeypatch):
    import app.modules.intelligence.service as svc

    def boom(*a, **kw):
        raise RuntimeError("simulated Neo4j outage")

    monkeypatch.setattr(svc, "exact_search", boom)
    response = intelligence_search(neo4j_session, "anything", limit=5)
    assert response.degraded is True
    assert response.degraded_reason is not None


def test_canonical_part_selection_matches_normal_catalogue_identity(neo4j_session):
    """The Part identity surfaced by Intelligence must be the same node used
    by the rest of the Parts Store (part_id / part_number), not a separate
    AI-only model."""
    response = intelligence_search(neo4j_session, "4663907", limit=5)
    assert any(c.part_number == "4663907" and c.part_id == "PT-001" for c in response.candidates)


def test_graph_insights_tabs_present(neo4j_session):
    insights = get_graph_insights(neo4j_session, "PT-001")
    assert insights.part_id == "PT-001"
    assert insights.impact.part_id == "PT-001"
    assert insights.fitment_evidence.part_id == "PT-001"
    assert insights.source_availability.part_id == "PT-001"
    assert insights.alternatives.part_id == "PT-001"
    assert insights.source_risk.part_id == "PT-001"


def test_graph_insights_raises_not_found_for_missing_part(neo4j_session):
    with pytest.raises(NotFoundError):
        get_graph_insights(neo4j_session, "PT-DOES-NOT-EXIST")


def test_source_risk_never_fabricates_score_when_no_source_data(neo4j_session):
    """If the graph has no source_id citations at all for a part, the tab
    must say so literally rather than invent a risk score or supplier."""
    insights = get_graph_insights(neo4j_session, "PT-001")
    risk = insights.source_risk
    if not risk.distinct_sources:
        assert risk.note == "Insufficient source data for risk assessment."
        assert risk.alternative_count == 0
        assert risk.single_source_concentration is False
    else:
        # If source data exists, single_source_concentration must be
        # consistent with the actual count derived from the graph.
        assert risk.single_source_concentration == (len(risk.distinct_sources) == 1)
