"""
Store the interchangeability-gate result in the graph as (Part)-[:CANDIDATE_ALTERNATIVE]->(Part) edges, so the relationship is visible and
queryable. Only pairs that pass the hard filters (orderable, same specific type, shared machine fitment) are stored.

These edges are DERIVED, never authoritative: they mean "Candidate for Engineering Review", not "approved replacement". They are separate from
SUPERSEDES / COMPATIBLE_WITH / NOT_COMPATIBLE_WITH, which stay reserved for real HCME engineering data. Idempotent: existing edges are rebuilt.

  python scripts/materialise_candidate_alternatives.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.neo4j.connection import get_neo4j_driver  # noqa: E402
from app.modules.intelligence import similarity  # noqa: E402


def main() -> None:
    with get_neo4j_driver().session() as s:
        parts = similarity._load_parts(s)
        s.run("MATCH (:Part)-[r:CANDIDATE_ALTERNATIVE]->(:Part) DELETE r")
        rows = []
        for p in parts:
            for a in similarity.similar_parts(s, p["part_id"], limit=50, loaded=parts).get("alternatives", []):
                rows.append({"a": p["part_id"], "b": a["part_id"], "cov": a["machine_coverage_pct"], "sim": a["similarity_pct"],
                             "shared": a["shared_machines"]})
        s.run("""UNWIND $rows AS r MATCH (a:Part {part_id: r.a}), (b:Part {part_id: r.b})
                 MERGE (a)-[e:CANDIDATE_ALTERNATIVE]->(b)
                 SET e.machine_coverage_pct = r.cov, e.text_similarity_pct = r.sim, e.shared_machines = r.shared,
                     e.basis = 'same part type + shared machine fitment', e.status = 'Candidate for Engineering Review',
                     e.data_class = 'DERIVED', e.authoritative = false""", rows=rows)
        print(f"CANDIDATE_ALTERNATIVE edges: {len(rows)}")


if __name__ == "__main__":
    main()
