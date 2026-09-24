"""
backend/app/modules/intelligence/scoring.py

Deterministic scoring algorithms for Graph Intelligence & Mitigation.

CORE AI PRINCIPLE:
Scoring is strictly deterministic and mathematical. The LLM NEVER invents or
guesses numbers or percentages. The LLM only explains the mathematically
computed scores based on the retrieved graph evidence.
"""

from typing import Any, Dict, Optional, Set, Tuple


def calculate_compatibility_score(
    target_part: Dict[str, Any],
    candidate_part: Dict[str, Any],
    target_machine_ids: Optional[Set[str]] = None,
    candidate_machine_ids: Optional[Set[str]] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Deterministic Compatibility Score (0.0 to 1.0).

    Formula & Weights:
      1. Category Match (weight = 0.25):
         - Target category == Candidate category: +0.25
      2. Subcategory Match (weight = 0.15):
         - Target subcategory == Candidate subcategory: +0.15
      3. Component Assembly Context (weight = 0.15):
         - Exact match of component_assembly: +0.15
         - Partial/token overlap: +0.10
      4. Fitted Machine Overlap (weight = 0.35):
         - Jaccard overlap = |Target ∩ Candidate| / |Target ∪ Candidate|
         - Weighted score = jaccard * 0.35
      5. Genuine Hitachi OEM Provenance (weight = 0.10):
         - Both marked genuine_hitachi_part == 'Yes': +0.10

    Returns:
      (score, breakdown_dict)
    """
    target_machines = target_machine_ids or set()
    candidate_machines = candidate_machine_ids or set()

    breakdown: Dict[str, Any] = {}

    # 1. Category
    cat_target = (target_part.get("part_category") or "").strip().lower()
    cat_cand = (candidate_part.get("part_category") or "").strip().lower()
    cat_match = bool(cat_target and cat_target == cat_cand)
    cat_score = 0.25 if cat_match else 0.0
    breakdown["category_match"] = {
        "target": target_part.get("part_category"),
        "candidate": candidate_part.get("part_category"),
        "matched": cat_match,
        "points": cat_score,
        "max_points": 0.25,
    }

    # 2. Subcategory
    sub_target = (target_part.get("part_subcategory") or "").strip().lower()
    sub_cand = (candidate_part.get("part_subcategory") or "").strip().lower()
    sub_match = bool(sub_target and sub_target == sub_cand)
    sub_score = 0.15 if sub_match else 0.0
    breakdown["subcategory_match"] = {
        "target": target_part.get("part_subcategory"),
        "candidate": candidate_part.get("part_subcategory"),
        "matched": sub_match,
        "points": sub_score,
        "max_points": 0.15,
    }

    # 3. Component Assembly Context
    asm_target = (target_part.get("component_assembly") or "").strip().lower()
    asm_cand = (candidate_part.get("component_assembly") or "").strip().lower()
    if asm_target and asm_cand:
        if asm_target == asm_cand:
            asm_score = 0.15
            asm_status = "EXACT_MATCH"
        else:
            tokens_t = set(asm_target.split())
            tokens_c = set(asm_cand.split())
            overlap = tokens_t.intersection(tokens_c)
            if overlap:
                asm_score = 0.10
                asm_status = f"PARTIAL_MATCH ({len(overlap)} terms in common)"
            else:
                asm_score = 0.0
                asm_status = "NO_OVERLAP"
    else:
        asm_score = 0.0
        asm_status = "MISSING_ASSEMBLY_DATA"
    breakdown["assembly_context"] = {
        "target": target_part.get("component_assembly"),
        "candidate": candidate_part.get("component_assembly"),
        "status": asm_status,
        "points": asm_score,
        "max_points": 0.15,
    }

    # 4. Fitted Machine Overlap (Jaccard similarity)
    if target_machines and candidate_machines:
        union = target_machines.union(candidate_machines)
        intersection = target_machines.intersection(candidate_machines)
        jaccard = len(intersection) / len(union) if union else 0.0
        machine_score = round(jaccard * 0.35, 4)
        breakdown["machine_overlap"] = {
            "common_models_count": len(intersection),
            "common_models_sample": sorted(list(intersection))[:5],
            "total_distinct_models": len(union),
            "jaccard_similarity": round(jaccard, 3),
            "points": machine_score,
            "max_points": 0.35,
        }
    else:
        machine_score = 0.0
        breakdown["machine_overlap"] = {
            "status": "INSUFFICIENT_GRAPH_EVIDENCE",
            "reason": "One or both parts have no graph-linked machine fitment records",
            "points": 0.0,
            "max_points": 0.35,
        }

    # 5. Genuine Hitachi OEM
    gen_t = target_part.get("genuine_hitachi_part") == "Yes"
    gen_c = candidate_part.get("genuine_hitachi_part") == "Yes"
    gen_score = 0.10 if (gen_t and gen_c) else (0.05 if gen_c else 0.0)
    breakdown["genuine_oem"] = {
        "target_genuine": gen_t,
        "candidate_genuine": gen_c,
        "points": gen_score,
        "max_points": 0.10,
    }

    total_score = round(cat_score + sub_score + asm_score + machine_score + gen_score, 3)
    return total_score, breakdown


def calculate_mitigation_score(
    compatibility_score: float,
    availability_status: str,
    compliance_status: str,
    source_risk_level: str,
    confidence: Optional[str] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Deterministic Mitigation Ranking Score (0.0 to 1.0).

    Weights:
      - Compatibility (40%): compatibility_score * 0.40
      - Availability (30%):
          * CONFIRMED / IN_STOCK -> 1.0 (0.30)
          * STALE / REGIONAL -> 0.60 (0.18)
          * UNKNOWN / UNCONFIRMED -> 0.30 (0.09)
          * OUT_OF_STOCK -> 0.0 (0.00)
      - Compliance (20%):
          * COMPLIANT -> 1.0 (0.20)
          * UNKNOWN / INSUFFICIENT_EVIDENCE -> 0.50 (0.10)
          * NON_COMPLIANT -> 0.0 (0.00)
      - Source Risk & Provenance (10%):
          * LOW risk & HIGH confidence -> 1.0 (0.10)
          * MEDIUM risk / MEDIUM confidence -> 0.70 (0.07)
          * UNKNOWN -> 0.50 (0.05)
          * HIGH risk / LOW confidence -> 0.20 (0.02)

    Returns:
      (mitigation_score, breakdown_dict)
    """
    # 1. Compatibility
    comp_points = round(compatibility_score * 0.40, 3)

    # 2. Availability
    avail_upper = (availability_status or "UNKNOWN").upper()
    if avail_upper in ("CONFIRMED", "AVAILABLE", "IN_STOCK"):
        avail_mult = 1.0
    elif avail_upper in ("STALE", "REGIONAL_ONLY"):
        avail_mult = 0.60
    elif avail_upper in ("UNKNOWN", "UNCONFIRMED"):
        avail_mult = 0.30
    else:
        avail_mult = 0.0
    avail_points = round(avail_mult * 0.30, 3)

    # 3. Compliance
    comp_upper = (compliance_status or "UNKNOWN").upper()
    if comp_upper in ("COMPLIANT", "VERIFIED"):
        comp_mult = 1.0
    elif comp_upper in ("UNKNOWN", "INSUFFICIENT_EVIDENCE"):
        comp_mult = 0.50
    else:
        comp_mult = 0.0
    compl_points = round(comp_mult * 0.20, 3)

    # 4. Source Risk & Provenance
    risk_upper = (source_risk_level or "UNKNOWN").upper()
    conf_upper = (confidence or "UNKNOWN").upper()
    if risk_upper == "LOW" or conf_upper == "HIGH":
        risk_mult = 1.0
    elif risk_upper == "MEDIUM" or conf_upper == "MEDIUM":
        risk_mult = 0.70
    elif risk_upper == "HIGH" or conf_upper == "LOW":
        risk_mult = 0.20
    else:
        risk_mult = 0.50
    risk_points = round(risk_mult * 0.10, 3)

    total_mitigation_score = round(comp_points + avail_points + compl_points + risk_points, 3)

    breakdown = {
        "compatibility": {"raw_score": compatibility_score, "weighted_points": comp_points, "weight": "40%"},
        "availability": {"status": availability_status, "multiplier": avail_mult, "weighted_points": avail_points, "weight": "30%"},
        "compliance": {"status": compliance_status, "multiplier": comp_mult, "weighted_points": compl_points, "weight": "20%"},
        "source_risk": {"risk_level": source_risk_level, "confidence": confidence, "multiplier": risk_mult, "weighted_points": risk_points, "weight": "10%"},
        "total_score": total_mitigation_score,
    }

    return total_mitigation_score, breakdown
