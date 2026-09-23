"""
backend/app/modules/intelligence/matching.py

Phase 7 Technical Part & Connector Matching.

Adapts candidate-matching capabilities to HCME Europe machinery components.
Uses deterministic similarity calculations based on real graph attributes:
- Machine category & subcategory
- Component assembly context
- Machine fitment overlap
- Technical specifications in description (voltage, dimensions, capacity) where recorded.

Rules:
- Never invents technical pins, voltage, or fake specs not present in graph.
- Calculates similarity score mathematically (0.0 to 1.0).
- If attributes are unavailable: explains "Technical attribute evidence unavailable."
"""

from typing import Any, Dict, List, Optional

from app.errors.exceptions import NotFoundError
from app.modules.intelligence.scoring import calculate_compatibility_score


def match_parts(
    session,
    target_part_id: str,
    query_context: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    part_row = session.run(
        "MATCH (p:Part {part_id: $id}) RETURN p",
        {"id": target_part_id},
    ).single()
    if not part_row:
        raise NotFoundError(f"Target Part '{target_part_id}' not found")
    target_part = dict(part_row["p"])

    # Target machines
    target_mach_res = session.run(
        "MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part {part_id: $id}) RETURN m.machine_id AS mid",
        {"id": target_part_id},
    ).data()
    target_machine_ids = {r["mid"] for r in target_mach_res if r.get("mid")}

    # Retrieve all candidate parts in the catalogue (excluding target)
    all_parts_res = session.run(
        """
        MATCH (p:Part)
        WHERE p.part_id <> $id
        RETURN p
        """,
        {"id": target_part_id},
    ).data()

    matches: List[Dict[str, Any]] = []

    for row in all_parts_res:
        cand_part = dict(row["p"])
        cand_pid = cand_part["part_id"]

        cand_mach_res = session.run(
            "MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part {part_id: $id}) RETURN m.machine_id AS mid",
            {"id": cand_pid},
        ).data()
        cand_machine_ids = {r["mid"] for r in cand_mach_res if r.get("mid")}

        similarity_score, breakdown = calculate_compatibility_score(
            target_part=target_part,
            candidate_part=cand_part,
            target_machine_ids=target_machine_ids,
            candidate_machine_ids=cand_machine_ids,
        )

        if similarity_score > 0.15:  # filter non-relevant parts
            matches.append({
                "part_id": cand_pid,
                "part_number": cand_part.get("part_number"),
                "part_name": cand_part.get("part_name"),
                "part_category": cand_part.get("part_category"),
                "part_subcategory": cand_part.get("part_subcategory"),
                "component_assembly": cand_part.get("component_assembly"),
                "similarity_score": similarity_score,
                "similarity_percentage": f"{int(similarity_score * 100)}%",
                "score_breakdown": breakdown,
                "genuine_hitachi_part": cand_part.get("genuine_hitachi_part") == "Yes",
                "fitted_machines_count": len(cand_machine_ids),
                "confidence": cand_part.get("confidence", "UNKNOWN"),
            })

    # Sort matches by similarity score descending
    matches.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_matches = matches[:limit]

    return {
        "target_part": {
            "part_id": target_part.get("part_id"),
            "part_name": target_part.get("part_name"),
            "part_number": target_part.get("part_number"),
            "part_category": target_part.get("part_category"),
            "part_subcategory": target_part.get("part_subcategory"),
            "component_assembly": target_part.get("component_assembly"),
        },
        "query_context": query_context or "General candidate matching",
        "total_evaluated_candidates": len(all_parts_res),
        "matched_candidates_count": len(top_matches),
        "matches": top_matches,
        "note": (
            "Similarity scores are computed deterministically from catalogue taxonomy, "
            "assembly context, and graph-linked machine fitment overlap."
        ),
    }
