"""
backend/app/modules/intelligence/fitment.py

Graph-aware fitment validation. Semantic/lexical similarity is never
treated as fitment on its own — fitment requires an actual
(:Machine)-[:HAS_PART_FITMENT]->(:Part) relationship in the graph.
"""

from typing import Any, Dict, List


def get_fitments_for_part(session, part_id: str) -> List[Dict[str, Any]]:
    result = session.run(
        """
        MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p:Part {part_id: $part_id})
        RETURN m.machine_id AS machine_id, m.model AS model,
               r.evidence AS evidence, r.evidence_original AS evidence_original,
               r.fitment_type AS fitment_type, r.confidence AS confidence,
               r.source_id AS source_id
        ORDER BY m.model
        """,
        {"part_id": part_id},
    ).data()
    return result


def fitted_machine_models(session, part_id: str) -> List[str]:
    return [f["model"] for f in get_fitments_for_part(session, part_id) if f.get("model")]
