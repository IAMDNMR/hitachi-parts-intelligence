"""
backend/app/modules/intelligence/mitigation.py

Phase 7 Mitigation Intelligence Workflow.

Workflow:
    Analyze Impact
        ↓
    Find Candidate Alternatives
        ↓
    Validate Compatibility (Deterministic scoring)
        ↓
    Validate Compliance (Graph evidence)
        ↓
    Assess Source Risk (Sourcing buffer)
        ↓
    Rank Mitigation Options (Deterministic mathematical ranking)
        ↓
    Explain Mitigation Strategy (LLM reasoning over evidence)

Guarantees:
- Deterministic scoring formulas from app.modules.intelligence.scoring.
- Never invents scores or fake alternative parts.
- LLM only reasons over retrieved facts and calculated scores.
"""

from typing import Any, Dict, List, Optional, Set

from app.errors.exceptions import NotFoundError
from app.logging_config.logger import logger
from app.modules.intelligence.alternatives import find_alternatives
from app.modules.intelligence.compliance import get_compliance_analysis
from app.modules.intelligence.impact import get_impact_analysis
from app.modules.intelligence.providers import (
    DeterministicLLMProvider,
    LLMProvider,
    get_llm_provider,
)
from app.modules.intelligence.scoring import (
    calculate_compatibility_score,
    calculate_mitigation_score,
)
from app.modules.intelligence.source_risk import get_source_risk_analysis


def get_mitigation_analysis(session, part_id: str) -> Dict[str, Any]:
    part_row = session.run(
        "MATCH (p:Part {part_id: $id}) RETURN p",
        {"id": part_id},
    ).single()
    if not part_row:
        raise NotFoundError(f"Part '{part_id}' not found")
    target_part = dict(part_row["p"])

    # 1. Impact & Source Risk for target part
    impact_data = get_impact_analysis(session, part_id)
    risk_data = get_source_risk_analysis(session, part_id)
    compliance_data = get_compliance_analysis(session, part_id)

    # Collect fitted machine IDs for target part
    target_machines_res = session.run(
        "MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part {part_id: $id}) RETURN m.machine_id AS mid, m.model AS model",
        {"id": part_id},
    ).data()
    target_machine_ids = {r["mid"] for r in target_machines_res if r.get("mid")}
    target_models = {r["model"] for r in target_machines_res if r.get("model")}

    # 2. Find Candidate Alternative Parts
    # A. Authoritative & candidate alternatives from graph
    existing_alts = find_alternatives(session, part_id)

    # B. Additional candidate parts in same category/subcategory from catalogue
    category = target_part.get("part_category")
    subcategory = target_part.get("part_subcategory")
    candidate_parts_query = session.run(
        """
        MATCH (p:Part)
        WHERE p.part_id <> $id
          AND (p.part_category = $cat OR p.part_subcategory = $subcat)
        RETURN p
        LIMIT 10
        """,
        {"id": part_id, "cat": category, "subcat": subcategory},
    ).data()

    candidate_dict: Dict[str, Dict[str, Any]] = {}
    alt_reasons: Dict[str, str] = {}
    is_auth_map: Dict[str, bool] = {}

    for a in existing_alts:
        alt_pid = a.part_id
        alt_row = session.run("MATCH (p:Part {part_id: $id}) RETURN p", {"id": alt_pid}).single()
        if alt_row:
            candidate_dict[alt_pid] = dict(alt_row["p"])
            alt_reasons[alt_pid] = a.reason
            is_auth_map[alt_pid] = a.is_authoritative_replacement

    for row in candidate_parts_query:
        cand_p = dict(row["p"])
        cand_pid = cand_p["part_id"]
        if cand_pid not in candidate_dict:
            candidate_dict[cand_pid] = cand_p
            alt_reasons[cand_pid] = f"Shared catalogue classification ({category} / {subcategory})"
            is_auth_map[cand_pid] = False

    # Hard filters (orderable part, same specific type, shared fitment) - category similarity alone is not a candidate.
    from app.modules.intelligence import interchangeability as ic
    _fit = ic.fitment_sets(session, list(candidate_dict))
    for _pid in list(candidate_dict):
        if not is_auth_map.get(_pid) and not ic.gate(target_part, candidate_dict[_pid], target_machine_ids, _fit[_pid])[0]:
            del candidate_dict[_pid]

    mitigation_options: List[Dict[str, Any]] = []

    # 3. Score each candidate deterministically
    for cand_pid, cand_part in candidate_dict.items():
        # Candidate fitted machines
        cand_mach_res = session.run(
            "MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part {part_id: $id}) RETURN m.machine_id AS mid, m.model AS model",
            {"id": cand_pid},
        ).data()
        cand_machine_ids = {r["mid"] for r in cand_mach_res if r.get("mid")}

        # Compatibility score
        comp_score, comp_breakdown = calculate_compatibility_score(
            target_part=target_part,
            candidate_part=cand_part,
            target_machine_ids=target_machine_ids,
            candidate_machine_ids=cand_machine_ids,
        )

        # Candidate compliance
        cand_compliance = get_compliance_analysis(session, cand_pid)
        cand_compl_status = cand_compliance.get("overall_status", "UNKNOWN")

        # Candidate availability
        cand_risk = get_source_risk_analysis(session, cand_pid)
        avail_status = "CONFIRMED" if cand_part.get("genuine_hitachi_part") == "Yes" else "STALE"

        # Mitigation score
        mitig_score, mitig_breakdown = calculate_mitigation_score(
            compatibility_score=comp_score,
            availability_status=avail_status,
            compliance_status=cand_compl_status,
            source_risk_level=cand_risk.get("risk_level", "UNKNOWN"),
            confidence=cand_part.get("confidence"),
        )

        # Bonus for authoritative replacement
        if is_auth_map.get(cand_pid):
            mitig_score = min(1.0, round(mitig_score + 0.05, 3))
            mitig_breakdown["authoritative_bonus"] = "+0.05 (Official supersession edge)"

        mitigation_options.append({
            "candidate_part_id": cand_pid,
            "candidate_part_number": cand_part.get("part_number"),
            "candidate_part_name": cand_part.get("part_name"),
            "candidate_category": cand_part.get("part_category"),
            "candidate_subcategory": cand_part.get("part_subcategory"),
            "description": cand_part.get("description"),
            "is_authoritative_replacement": is_auth_map.get(cand_pid, False),
            "reason": alt_reasons.get(cand_pid, "Candidate alternative"),
            "compatibility_score": comp_score,
            "compatibility_breakdown": comp_breakdown,
            "mitigation_score": mitig_score,
            "mitigation_breakdown": mitig_breakdown,
            "compliance_status": cand_compl_status,
            "availability_status": avail_status,
            "source_risk_level": cand_risk.get("risk_level", "UNKNOWN"),
            "synthetic": cand_part.get("synthetic", False),
            "confidence": cand_part.get("confidence", "UNKNOWN"),
        })

    # Sort options by deterministic mitigation score descending
    mitigation_options.sort(key=lambda x: x["mitigation_score"], reverse=True)

    # 4. Generate AI Executive Summary explaining the deterministic scores
    ai_summary = _generate_mitigation_explanation(
        target_part=target_part,
        impact=impact_data,
        risk=risk_data,
        top_options=mitigation_options[:3],
    )

    return {
        "part_id": part_id,
        "part_name": target_part.get("part_name"),
        "part_number": target_part.get("part_number"),
        "target_impact_summary": {
            "affected_machines_count": impact_data["total_affected_machines_count"],
            "criticality_level": impact_data["criticality_level"],
            "product_families": [f["family_name"] for f in impact_data["product_families"][:3]],
        },
        "target_risk_level": risk_data["risk_level"],
        "options_count": len(mitigation_options),
        "mitigation_options": mitigation_options,
        "executive_summary": ai_summary,
        "note": "Mitigation ranking is computed deterministically. Recommended options require technical engineer validation prior to ordering.",
    }


def _generate_mitigation_explanation(
    target_part: Dict[str, Any],
    impact: Dict[str, Any],
    risk: Dict[str, Any],
    top_options: List[Dict[str, Any]],
) -> str:
    """Uses LLM (or deterministic fallback) to formulate an executive
    briefing explaining the deterministic mitigation options."""
    if not top_options:
        return (
            f"No compatible alternative parts were found in the graph for {target_part.get('part_id')} "
            f"({target_part.get('part_name')}). Sourcing requires direct inquiry through the European Parts Centre."
        )

    best = top_options[0]
    provider = get_llm_provider()

    if isinstance(provider, DeterministicLLMProvider):
        return (
            f"Mitigation Analysis for {target_part.get('part_name')} ({target_part.get('part_id')}):\n"
            f"• Operational Impact: {impact['total_affected_machines_count']} machine model(s) affected with {impact['criticality_level']} criticality.\n"
            f"• Source Risk: {risk['risk_level']} risk level ({risk['note']}).\n"
            f"• Top Recommended Mitigation: {best['candidate_part_name']} ({best['candidate_part_id']}) with "
            f"Mitigation Score {int(best['mitigation_score'] * 100)}% (Compatibility: {int(best['compatibility_score'] * 100)}%). "
            f"{best['reason']}."
        )

    try:
        prompt = (
            f"You are an HCME Europe After-Sales Systems Engineer. Summarize the mitigation strategy for this part in 2-3 concise paragraphs. "
            f"State ONLY facts provided below. Never invent certifications, part numbers, or scores.\n\n"
            f"Target Part: {target_part.get('part_name')} (ID: {target_part.get('part_id')}, PN: {target_part.get('part_number')})\n"
            f"Impact: {impact['total_affected_machines_count']} machines across {len(impact['product_families'])} families ({', '.join(f['family_name'] for f in impact['product_families'][:3])})\n"
            f"Source Risk Level: {risk['risk_level']}\n"
            f"Top Alternative: {best['candidate_part_name']} (ID: {best['candidate_part_id']}, PN: {best['candidate_part_number']})\n"
            f"Deterministic Mitigation Score: {best['mitigation_score']} / 1.0\n"
            f"Deterministic Compatibility Score: {best['compatibility_score']} / 1.0\n"
            f"Compatibility Breakdown: {best['compatibility_breakdown']}\n"
            f"Compliance Status: {best['compliance_status']}\n"
            f"Availability: {best['availability_status']}\n"
            f"Reason: {best['reason']}\n"
        )
        return provider.call_gemini(prompt)
    except Exception as e:
        logger.warning(f"LLM mitigation summary degraded: {e}")
        return (
            f"Top mitigation candidate is {best['candidate_part_name']} ({best['candidate_part_id']}) "
            f"with deterministic mitigation score {int(best['mitigation_score'] * 100)}% and compatibility score {int(best['compatibility_score'] * 100)}%. "
            f"Reason: {best['reason']}."
        )
