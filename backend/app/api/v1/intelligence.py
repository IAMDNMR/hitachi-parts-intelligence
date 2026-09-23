"""
backend/app/api/v1/intelligence.py

Parts Intelligence API — read-only orchestration/search layer over the
canonical Part graph. Never allocates, orders, ships, or mutates
inventory/fulfilment state (those remain in their existing domain routers).
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.db.neo4j.connection import get_neo4j_session
from app.modules.intelligence.schemas import NaturalLanguageQuery, IntelligenceSearchResponse, GraphInsights
from app.modules.intelligence.service import search as intelligence_search, get_graph_insights
from app.modules.intelligence import context as intelligence_context

router = APIRouter(prefix="/intelligence", tags=["Parts Intelligence"])


@router.post("/search", response_model=IntelligenceSearchResponse)
def search_parts(
    dto: NaturalLanguageQuery,
    session=Depends(get_neo4j_session),
):
    """Natural-language / exact / lexical search across the canonical Part
    graph. Falls back gracefully if semantic search is unavailable."""
    return intelligence_search(session, dto.query, dto.limit)


@router.get("/parts/{part_id}/insights", response_model=GraphInsights)
def graph_insights(
    part_id: str,
    session=Depends(get_neo4j_session),
):
    """Graph Insights: Impact / Fitment & Evidence / Source & Availability /
    Alternatives — for one canonical Part, all backed by real graph data."""
    return get_graph_insights(session, part_id)


# ---------------------------------------------------------------------------
# Operational/commercial context layer (HCME Europe KPI foundation) — see
# docs/research/HCME_EUROPE_OPERATIONAL_DATA_AND_KPI_FOUNDATION.md.
# Read-only. Every response distinguishes real vs SYNTHETIC_DEMO data via the
# `synthetic`/`data_source` fields on each record (see app/modules/
# intelligence/context.py docstring for the rule).
# ---------------------------------------------------------------------------

@router.get("/parts/{part_id}/order-context", response_model=Dict[str, Any])
def order_context(part_id: str, session=Depends(get_neo4j_session)):
    """KPI 1/3 — Part -> FulfilmentRequest -> Allocation -> Order -> Shipment
    -> DealerBranch, graph-traversed."""
    return intelligence_context.get_order_context(session, part_id)


@router.get("/orders/{order_id}/status", response_model=Dict[str, Any])
def order_status(order_id: str, session=Depends(get_neo4j_session)):
    """KPI 3 — 'What's the status of order X?' resolved from the graph."""
    return intelligence_context.get_order_status(session, order_id)


@router.get("/parts/{part_id}/supply-chain", response_model=Dict[str, Any])
def supply_chain(part_id: str, session=Depends(get_neo4j_session)):
    """Part -> synthetic InventorySnapshot / real Depot / synthetic Supplier."""
    return intelligence_context.get_supply_chain(session, part_id)


@router.get("/parts/{part_id}/cross-catalog", response_model=Dict[str, Any])
def cross_catalog(part_id: str, session=Depends(get_neo4j_session)):
    """KPI 2/4 — cross-catalog matches and deterministic master-data
    consistency verdicts (MATCH/MINOR_DIFFERENCE/SIGNIFICANT_DIFFERENCE/UNKNOWN)."""
    return intelligence_context.get_cross_catalog(session, part_id)


@router.get("/parts/{part_id}/customs", response_model=Dict[str, Any])
def customs_flags(part_id: str, session=Depends(get_neo4j_session)):
    """KPI 5 — synthetic customs-flag context for this part's demo shipments."""
    return intelligence_context.get_customs_flags(session, part_id)


@router.get("/graph-stats", response_model=Dict[str, Any])
def graph_stats(session=Depends(get_neo4j_session)):
    """Live real-vs-synthetic counts and integrity checks (Part 22 validation
    surface) — always re-queryable against the running graph."""
    return intelligence_context.get_graph_stats(session)


# ---------------------------------------------------------------------------
# Phase 7 Graph Intelligence Expansion
# ---------------------------------------------------------------------------

@router.get("/parts/{part_id}/impact", response_model=Dict[str, Any])
def impact_analysis(part_id: str, session=Depends(get_neo4j_session)):
    """Phase 7: Machine & Product Family Impact Analysis."""
    from app.modules.intelligence.impact import get_impact_analysis
    return get_impact_analysis(session, part_id)


@router.get("/parts/{part_id}/compliance", response_model=Dict[str, Any])
def compliance_analysis(part_id: str, session=Depends(get_neo4j_session)):
    """Phase 7: Regulatory & Standard Compliance Intelligence."""
    from app.modules.intelligence.compliance import get_compliance_analysis
    return get_compliance_analysis(session, part_id)


@router.get("/parts/{part_id}/source-risk", response_model=Dict[str, Any])
def source_risk_analysis(part_id: str, session=Depends(get_neo4j_session)):
    """Phase 7: Supplier & Source Risk Intelligence."""
    from app.modules.intelligence.source_risk import get_source_risk_analysis
    return get_source_risk_analysis(session, part_id)


@router.get("/parts/{part_id}/mitigation", response_model=Dict[str, Any])
def mitigation_analysis(part_id: str, session=Depends(get_neo4j_session)):
    """Phase 7: Multi-criteria Mitigation Ranking & Strategy."""
    from app.modules.intelligence.mitigation import get_mitigation_analysis
    return get_mitigation_analysis(session, part_id)


@router.post("/parts/{part_id}/match-parts", response_model=Dict[str, Any])
def technical_part_matching(
    part_id: str,
    limit: int = 5,
    session=Depends(get_neo4j_session),
):
    """Phase 7: Deterministic Technical Part & Attribute Matching."""
    from app.modules.intelligence.matching import match_parts
    return match_parts(session, part_id, limit=limit)


@router.get("/parts/{part_id}/graph-insights", response_model=Dict[str, Any])
def part_graph_insights(part_id: str, session=Depends(get_neo4j_session)):
    """Phase 10: Impact · Compliance · Supplier Risk · Mitigation in one response."""
    from app.modules.intelligence.graph_insights import get_part_graph_insights
    return get_part_graph_insights(session, part_id)


@router.get("/catalog", response_model=Dict[str, Any])
def question_catalog(session=Depends(get_neo4j_session)):
    """Verified question catalogue (categories -> questions) read from Aura."""
    from app.modules.intelligence.question_catalog import list_catalog
    return list_catalog(session)


@router.post("/query", response_model=Dict[str, Any])
def natural_language_assistant(
    dto: NaturalLanguageQuery,
    session=Depends(get_neo4j_session),
):
    """Phase 7: Natural Language Query Router & Evidence Explainer."""
    from app.modules.intelligence.assistant import route_and_answer_query
    return route_and_answer_query(session, dto.query, context_part_id=dto.context_part_id, limit=dto.limit, follow_up_to=dto.follow_up_to)


# ---------------------------------------------------------------------------
# Phase 11 - HCME Parts Intelligence extensions (see docs/research/PHASE_11_HCME_PARTS_INTELLIGENCE_FIT.md).
# Read-only. Existing endpoints above are unchanged.
# ---------------------------------------------------------------------------

from typing import Optional

from pydantic import BaseModel, Field

from app.modules.intelligence import similarity as intelligence_similarity, kpis as intelligence_kpis, disruption as intelligence_disruption
from app.errors.exceptions import ValidationError as _ValidationError


class RfqQuery(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class DisruptionQuery(BaseModel):
    scenario: str
    part_id: Optional[str] = None
    supplier: Optional[str] = None
    compliance_id: Optional[str] = None


@router.get("/search/semantic", response_model=Dict[str, Any])
def semantic_search(q: str, limit: int = 8, session=Depends(get_neo4j_session)):
    """Embedding-only ranking over the catalogue (local embeddings, no external API)."""
    return intelligence_similarity.semantic_search(session, q, limit)


@router.get("/search/hybrid", response_model=Dict[str, Any])
def hybrid_search(q: str, limit: int = 8, session=Depends(get_neo4j_session)):
    """Exact part number + semantic + keyword + electrical-spec match, with match factors per result."""
    return intelligence_similarity.hybrid_search(session, q, limit)


@router.get("/parts/{part_id}/similar", response_model=Dict[str, Any])
def similar_parts(part_id: str, limit: int = 5, session=Depends(get_neo4j_session)):
    """Ranked similar parts with score and why each is recommended or rejected."""
    return intelligence_similarity.similar_parts(session, part_id, limit)


@router.post("/rfq", response_model=Dict[str, Any])
def rfq_search(dto: RfqQuery, session=Depends(get_neo4j_session)):
    """RFQ-style request -> ranked parts with spec match, demo-stock check, risks and reasons."""
    return intelligence_similarity.rfq_search(session, dto.text, dto.limit)


@router.post("/disruption", response_model=Dict[str, Any])
def disruption(dto: DisruptionQuery, session=Depends(get_neo4j_session)):
    """Scenario analysis: part_unavailable | supplier_unavailable | compliance_failure | stock_shortage."""
    try:
        return intelligence_disruption.analyse(session, dto.scenario, part_id=dto.part_id, supplier=dto.supplier,
                                               compliance_id=dto.compliance_id)
    except ValueError as exc:
        raise _ValidationError(str(exc))


@router.get("/parts/{part_id}/compliance-check", response_model=Dict[str, Any])
def compliance_check(part_id: str, substitute: str, session=Depends(get_neo4j_session)):
    """Does `substitute` satisfy the requirements inherited by the assemblies `part_id` sits in? PASS / WARNING / FAIL."""
    return intelligence_disruption.compliance_verdict(session, part_id, substitute)


@router.get("/kpis", response_model=Dict[str, Any])
def kpis(session=Depends(get_neo4j_session)):
    """KPIs calculable from the current graph, with numerator/denominator, method and data source."""
    return intelligence_kpis.all_kpis(session)
