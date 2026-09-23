"""
backend/app/modules/intelligence/explanation.py

Builds human-readable, evidence-backed explanations for a candidate Part.
Never says "AI recommends this part" alone — always cites the concrete
evidence (match method, fitment, provenance/confidence, availability
state) that produced the result.
"""

from typing import Dict, List

from app.modules.intelligence.schemas import Evidence


def build_evidence(part: Dict, match_methods: List[str], fitted_machines: List[str], machine_model_requested: str = None) -> List[Evidence]:
    evidence: List[Evidence] = []
    if "EXACT_PART_NUMBER" in match_methods:
        evidence.append(Evidence(kind="EXACT_PART_NUMBER", detail="Query matched this part's part number or part ID exactly."))
    if any(m.startswith("LEXICAL") for m in match_methods):
        evidence.append(Evidence(kind="LEXICAL_MATCH", detail="Matched on name/description/category text search."))
    if "SEMANTIC" in match_methods:
        evidence.append(Evidence(kind="SEMANTIC_MATCH", detail="Matched via semantic (vector) similarity."))
    if machine_model_requested and fitted_machines:
        matched = [m for m in fitted_machines if machine_model_requested.upper() in m.upper()]
        if matched:
            evidence.append(Evidence(
                kind="GRAPH_FITMENT",
                detail=f"Graph-confirmed HAS_PART_FITMENT relationship to {', '.join(matched)}.",
                confidence=part.get("confidence"),
            ))
    evidence.append(Evidence(
        kind="PROVENANCE",
        detail=f"Source: {part.get('source_id') or 'UNKNOWN'}; record confidence: {part.get('confidence') or 'UNKNOWN'}.",
        confidence=part.get("confidence") or "UNKNOWN",
    ))
    return evidence


def build_explanation_text(part: Dict, evidence: List[Evidence]) -> str:
    parts_text = []
    for e in evidence:
        if e.kind == "EXACT_PART_NUMBER":
            parts_text.append("exact part number match")
        elif e.kind == "LEXICAL_MATCH":
            parts_text.append("text match on name/description/category")
        elif e.kind == "SEMANTIC_MATCH":
            parts_text.append("semantic similarity match")
        elif e.kind == "GRAPH_FITMENT":
            parts_text.append(e.detail)
    base = ", ".join(parts_text) if parts_text else "candidate surfaced by search"
    return f"{part.get('part_name', 'This part')} — {base}. Source: {part.get('source_id') or 'UNKNOWN'} (confidence: {part.get('confidence') or 'UNKNOWN'})."
