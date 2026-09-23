"""
backend/app/modules/intelligence/schemas.py

Pydantic schemas for the Parts Intelligence module.

This module is a READ-ONLY orchestration/search layer over the existing
canonical Part graph. It never allocates, orders, ships, or mutates
inventory — those stay in app.modules.allocation / fulfilment / availability.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NaturalLanguageQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Free-text request, e.g. 'hydraulic filter for ZX210-7'")
    limit: int = Field(10, ge=1, le=50)
    context_part_id: Optional[str] = Field(None, description="Part the user is looking at, for 'this part' follow-ups")
    follow_up_to: Optional[str] = Field(None, description="Original question when this query answers the assistant's clarifying question")


class ParsedIntent(BaseModel):
    """Structured intent extracted from a natural-language query.

    Produced by query_parser.py. The LLM (or deterministic fallback) is
    NOT authoritative for fitment/availability/pricing — it only proposes
    search terms that are then validated against the graph.

    Phase 10C additions — ALL entity fields are preserved simultaneously so
    multi-entity questions ("buckets suppliers for medium excavator in NL")
    are never silently collapsed to a single filter.
    """
    intent: str = "find_part"
    # --- Part Intelligence (original) ---
    machine_model: Optional[str] = None           # exact model code: ZX210-7
    part_requirement: Optional[str] = None         # remaining text after model removal
    # --- Phase 10C: multi-entity fields ---
    machine_type: Optional[str] = None            # "medium excavator", "wheel loader"
    part_category: Optional[str] = None           # "bucket", "filter", "undercarriage"
    requested_entity: Optional[str] = None        # "supplier", "dealer", "part", "machine"
    relationship_required: Optional[str] = None   # e.g. "Machine->Part->Supplier"
    follow_up_required: bool = False
    follow_up_type: Optional[str] = None          # "machine_selection", "part_selection"
    machine_candidates: List[str] = Field(default_factory=list)
    raw_query: str
    source: str = Field(..., description="'llm' if a real LLM provider produced this, 'deterministic' otherwise")


class SourceAvailabilitySummary(BaseModel):
    """Read-only snapshot of availability context. Never the authority —
    see app.modules.availability.service for the authoritative check."""
    status: str = "UNKNOWN"  # CONFIRMED | STALE | UNKNOWN | UNCONFIRMED
    note: str = "Availability not checked from Intelligence. Use the Availability step for an authoritative result."


class Evidence(BaseModel):
    kind: str  # e.g. "EXACT_PART_NUMBER", "LEXICAL_MATCH", "SEMANTIC_MATCH", "GRAPH_FITMENT"
    detail: str
    confidence: Optional[str] = None  # HIGH | MEDIUM | LOW | UNKNOWN — as stored in graph, never invented


class PartCandidate(BaseModel):
    part_id: str
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    part_category: Optional[str] = None
    part_subcategory: Optional[str] = None
    description: Optional[str] = None
    record_class: Optional[str] = None
    genuine_hitachi_part: Optional[str] = None
    source_id: Optional[str] = None
    confidence: Optional[str] = None  # provenance confidence from the graph record itself
    match_score: float = Field(..., description="0-1 retrieval score; see ranking.py docstring for exact formula")
    match_methods: List[str] = Field(default_factory=list, description="which retrieval stages surfaced this part")
    evidence: List[Evidence] = Field(default_factory=list)
    fitted_machines: List[str] = Field(default_factory=list, description="Machine models with graph-confirmed fitment")
    availability: SourceAvailabilitySummary = Field(default_factory=SourceAvailabilitySummary)
    explanation: str = ""


class IntelligenceSearchResponse(BaseModel):
    query: str
    parsed_intent: ParsedIntent
    candidates: List[PartCandidate]
    search_modes_used: List[str]
    degraded: bool = False
    degraded_reason: Optional[str] = None


class ImpactTab(BaseModel):
    part_id: str
    related_machines: List[Dict[str, Any]] = Field(default_factory=list)
    related_services: List[Dict[str, Any]] = Field(default_factory=list)
    related_parts: List[Dict[str, Any]] = Field(default_factory=list)
    note: str = ""


class FitmentEvidenceTab(BaseModel):
    part_id: str
    fitments: List[Dict[str, Any]] = Field(default_factory=list)
    note: str = "Fitment status reflects only graph-recorded HAS_PART_FITMENT evidence. Never claimed as 'approved' without authoritative source data."


class SourceAvailabilityTab(BaseModel):
    part_id: str
    source_id: Optional[str] = None
    confidence: Optional[str] = None
    source_date: Optional[str] = None
    availability: SourceAvailabilitySummary = Field(default_factory=SourceAvailabilitySummary)
    note: str = "Availability shown here is contextual only. The authoritative check is the existing Availability step."


class AlternativeCandidate(BaseModel):
    part_id: str
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    reason: str
    fitment_evidence: Optional[str] = None
    is_authoritative_replacement: bool = False


class AlternativesTab(BaseModel):
    part_id: str
    alternatives: List[AlternativeCandidate] = Field(default_factory=list)
    note: str = "These are candidate alternatives for manual review only — never auto-selected, auto-allocated, or auto-ordered."


class SourceRiskTab(BaseModel):
    """Supply / Source Risk — derived ONLY from graph-recorded source
    citations (Part.source_id and HAS_PART_FITMENT.source_id). There is no
    :Source node or supplier/reliability data in the current Neo4j schema,
    so this tab never fabricates a risk score or supplier name. When the
    graph doesn't carry enough source citations to say anything meaningful,
    `note` is the literal string below and `distinct_sources`/`alternative_count`
    are left at 0."""
    part_id: str
    distinct_sources: List[str] = Field(default_factory=list, description="Distinct non-null source_id values found on this part's own record and its fitment relationships")
    alternative_count: int = Field(0, description="Number of candidate/authoritative alternatives found (see AlternativesTab) — a possible mitigation path, not a guarantee")
    single_source_concentration: bool = Field(False, description="True only when exactly one distinct source_id is recorded across all citations found")
    note: str = "Insufficient source data for risk assessment."


class GraphInsights(BaseModel):
    part_id: str
    impact: ImpactTab
    fitment_evidence: FitmentEvidenceTab
    source_availability: SourceAvailabilityTab
    alternatives: AlternativesTab
    source_risk: SourceRiskTab
