"""
backend/app/modules/intelligence/service.py

Orchestration for Parts Intelligence. Read-only: never allocates, orders,
ships, or mutates inventory/fulfilment state.

Pipeline: query -> parsed intent -> lexical + exact (+ semantic if
available) search -> candidate Parts -> graph fitment validation ->
business rules (UNKNOWN discipline) -> explainable ranked results.

Failure isolation: any exception raised while querying Neo4j for search is
caught here and surfaces as a degraded response rather than propagating —
Parts Intelligence must never be a single point of failure for the Parts
Store. Callers should check `degraded` on the response.
"""

from typing import Any, Dict, List

from app.logging_config.logger import logger
from app.modules.intelligence.providers import DeterministicLLMProvider, LLMProvider, get_llm_provider
from app.modules.intelligence.query_parser import parse_query
from app.modules.intelligence.search import exact_search, lexical_search, semantic_search, machine_fitted_part_ids
from app.modules.intelligence.fitment import get_fitments_for_part, fitted_machine_models
from app.modules.intelligence.alternatives import find_alternatives
from app.modules.intelligence.explanation import build_evidence, build_explanation_text
from app.modules.intelligence.ranking import score_candidate
from app.modules.intelligence.schemas import (
    PartCandidate,
    IntelligenceSearchResponse,
    SourceAvailabilitySummary,
    GraphInsights,
    ImpactTab,
    FitmentEvidenceTab,
    SourceAvailabilityTab,
    AlternativesTab,
    AlternativeCandidate,
    SourceRiskTab,
)


def _explain(provider: LLMProvider, part: Dict[str, Any], evidence) -> tuple[str, bool, str]:
    """Generate the candidate's explanation text from already-verified
    evidence. Tries the configured provider; on any failure (e.g. Gemini
    unavailable) falls back to the deterministic, non-LLM explanation
    builder so a candidate is never dropped for lack of AI phrasing."""
    if isinstance(provider, DeterministicLLMProvider):
        return build_explanation_text(part, evidence), False, None
    try:
        return provider.explain(part, evidence), False, None
    except Exception as e:
        logger.warning(f"Parts Intelligence LLM explanation degraded, falling back to deterministic text: {e}")
        return build_explanation_text(part, evidence), True, f"LLM explanation generation failed: {e}"


def _to_candidate(provider: LLMProvider, part: Dict[str, Any], match_methods: List[str], fitted_machines: List[str], machine_model_requested: str, score: float):
    evidence = build_evidence(part, match_methods, fitted_machines, machine_model_requested)
    explanation, degraded, degraded_reason = _explain(provider, part, evidence)
    return PartCandidate(
        part_id=part["part_id"],
        part_number=part.get("part_number"),
        part_name=part.get("part_name"),
        part_category=part.get("part_category"),
        part_subcategory=part.get("part_subcategory"),
        description=part.get("description"),
        record_class=part.get("record_class"),
        genuine_hitachi_part=part.get("genuine_hitachi_part"),
        source_id=part.get("source_id"),
        confidence=part.get("confidence"),
        match_score=score,
        match_methods=match_methods,
        evidence=evidence,
        fitted_machines=fitted_machines,
        availability=SourceAvailabilitySummary(),
        explanation=explanation,
    ), degraded, degraded_reason


def search(session, query: str, limit: int = 10) -> IntelligenceSearchResponse:
    provider = get_llm_provider()
    parsed = parse_query(query)
    search_modes_used: List[str] = []
    degraded = False
    degraded_reason = None

    if not isinstance(provider, DeterministicLLMProvider) and parsed.source == "deterministic":
        # An LLM provider is configured but query understanding fell back
        # to the deterministic parser (see query_parser.parse_query).
        degraded = True
        degraded_reason = "LLM query understanding unavailable; used deterministic parsing instead."

    candidates_by_id: Dict[str, Dict[str, Any]] = {}
    methods_by_id: Dict[str, List[str]] = {}

    def register(parts: List[Dict[str, Any]], method: str):
        for p in parts:
            pid = p.get("part_id")
            if not pid:
                continue
            candidates_by_id.setdefault(pid, p)
            methods_by_id.setdefault(pid, [])
            if method not in methods_by_id[pid]:
                methods_by_id[pid].append(method)

    search_term = parsed.part_requirement or parsed.raw_query

    try:
        exact = exact_search(session, parsed.raw_query.strip())
        register(exact, "EXACT_PART_NUMBER")
        if exact:
            search_modes_used.append("exact")

        lex = lexical_search(session, search_term, limit=limit * 2)
        register(lex, "LEXICAL_NAME")
        if lex:
            search_modes_used.append("lexical")

        sem_results, sem_used = semantic_search(session, search_term, limit=limit)
        if sem_used:
            register(sem_results, "SEMANTIC")
            search_modes_used.append("semantic")
        else:
            degraded = True
            degraded_reason = "No embedding provider configured in this environment; semantic search skipped. Lexical and exact search results are unaffected."
    except Exception as e:
        logger.warning(f"Parts Intelligence search degraded: {e}")
        degraded = True
        degraded_reason = f"Search backend error: {e}"

    fitted_ids = set()
    if parsed.machine_model:
        try:
            fitted_ids = set(machine_fitted_part_ids(session, parsed.machine_model))
        except Exception as e:
            logger.warning(f"Parts Intelligence fitment filter degraded: {e}")

    candidates: List[PartCandidate] = []
    for pid, part in candidates_by_id.items():
        methods = methods_by_id[pid]
        try:
            fitted_machines = fitted_machine_models(session, pid)
        except Exception:
            fitted_machines = []
        fitment_matched = pid in fitted_ids if parsed.machine_model else False
        score = score_candidate(methods, fitment_matched)
        candidate, cand_degraded, cand_degraded_reason = _to_candidate(
            provider, part, methods, fitted_machines, parsed.machine_model, score
        )
        candidates.append(candidate)
        if cand_degraded and not degraded:
            degraded = True
            degraded_reason = cand_degraded_reason

    candidates.sort(key=lambda c: c.match_score, reverse=True)
    candidates = candidates[:limit]

    return IntelligenceSearchResponse(
        query=query,
        parsed_intent=parsed,
        candidates=candidates,
        search_modes_used=search_modes_used,
        degraded=degraded,
        degraded_reason=degraded_reason,
    )


def get_graph_insights(session, part_id: str) -> GraphInsights:
    part_row = session.run("MATCH (p:Part {part_id: $id}) RETURN p", {"id": part_id}).single()
    if not part_row:
        from app.errors.exceptions import NotFoundError
        raise NotFoundError(f"Part '{part_id}' not found")
    part = part_row["p"]

    # Impact tab: related machines, services (via shared machine), related parts (same category/machine)
    related_machines = session.run(
        """
        MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p:Part {part_id: $id})
        RETURN m.machine_id AS machine_id, m.model AS model, r.fitment_type AS fitment_type
        ORDER BY m.model
        """,
        {"id": part_id},
    ).data()

    related_services = session.run(
        """
        MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part {part_id: $id})
        MATCH (m)-[:HAS_SERVICE]->(s:Service)
        RETURN DISTINCT s.service_id AS service_id, s.service_name AS service_name, s.service_category AS service_category
        LIMIT 20
        """,
        {"id": part_id},
    ).data()

    related_parts = session.run(
        """
        MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part {part_id: $id})
        MATCH (m)-[:HAS_PART_FITMENT]->(other:Part)
        WHERE other.part_id <> p.part_id
        RETURN DISTINCT other.part_id AS part_id, other.part_number AS part_number, other.part_name AS part_name
        LIMIT 20
        """,
        {"id": part_id},
    ).data()

    impact = ImpactTab(
        part_id=part_id,
        related_machines=related_machines,
        related_services=related_services,
        related_parts=related_parts,
        note="All relationships shown are graph-confirmed (HAS_PART_FITMENT / HAS_SERVICE). No quantities are fabricated where the source data does not provide them.",
    )

    fitments = get_fitments_for_part(session, part_id)
    fitment_evidence = FitmentEvidenceTab(part_id=part_id, fitments=fitments)

    source_availability = SourceAvailabilityTab(
        part_id=part_id,
        source_id=part.get("source_id"),
        confidence=part.get("confidence"),
        source_date=part.get("source_date"),
        availability=SourceAvailabilitySummary(),
    )

    alts = find_alternatives(session, part_id)
    alternatives = AlternativesTab(part_id=part_id, alternatives=alts)

    # Supply / Source Risk — derived only from source_id citations that
    # already exist on the Part record and its HAS_PART_FITMENT
    # relationships. No :Source node or supplier data exists in this
    # schema, so we never fabricate a risk score.
    source_ids = set()
    if part.get("source_id"):
        source_ids.add(part.get("source_id"))
    for f in fitments:
        if f.get("source_id"):
            source_ids.add(f["source_id"])
    distinct_sources = sorted(source_ids)
    if not distinct_sources:
        source_risk = SourceRiskTab(part_id=part_id)  # default note applies
    else:
        single = len(distinct_sources) == 1
        note = (
            "Only one distinct source citation is recorded for this part across its record and fitment evidence."
            if single
            else f"{len(distinct_sources)} distinct source citations recorded across this part's record and fitment evidence."
        )
        if single and not alts:
            note += " No alternative parts were found in the graph either, so there is no recorded mitigation path."
        source_risk = SourceRiskTab(
            part_id=part_id,
            distinct_sources=distinct_sources,
            alternative_count=len(alts),
            single_source_concentration=single,
            note=note,
        )

    return GraphInsights(
        part_id=part_id,
        impact=impact,
        fitment_evidence=fitment_evidence,
        source_availability=source_availability,
        alternatives=alternatives,
        source_risk=source_risk,
    )
