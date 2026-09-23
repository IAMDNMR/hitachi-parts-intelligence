"""
backend/app/modules/intelligence/impact.py

Phase 7 Impact Intelligence.

Traverses canonical graph relationships:
    Part <-[:HAS_PART_FITMENT]- Machine
    Part -> Component Assembly / Context
    Machine -> Product Family / Generation Series

Enforces strict provenance: only reports machines, families, and assemblies
actually linked in the live Neo4j graph. Never hallucinates numbers.
"""

from collections import Counter
from typing import Any, Dict, List

from app.errors.exceptions import NotFoundError


def get_impact_analysis(session, part_id: str) -> Dict[str, Any]:
    part_row = session.run(
        "MATCH (p:Part {part_id: $id}) RETURN p",
        {"id": part_id},
    ).single()
    if not part_row:
        raise NotFoundError(f"Part '{part_id}' not found")
    part = dict(part_row["p"])

    # Traverse all machine fitments
    rows = session.run(
        """
        MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p:Part {part_id: $id})
        RETURN m.machine_id AS machine_id, m.model AS model,
               m.machine_category AS machine_category,
               m.machine_subcategory AS machine_subcategory,
               m.product_family AS product_family,
               m.generation_series AS generation_series,
               r.fitment_type AS fitment_type,
               r.assembly AS assembly,
               r.installation_context AS installation_context,
               r.confidence AS confidence,
               r.source_id AS source_id
        ORDER BY m.model ASC
        """,
        {"id": part_id},
    ).data()

    if not rows:
        return {
            "part_id": part_id,
            "part_name": part.get("part_name"),
            "part_number": part.get("part_number"),
            "component_assembly": part.get("component_assembly"),
            "total_affected_machines_count": 0,
            "total_fitment_relationships_count": 0,
            "product_families": [],
            "machine_categories": [],
            "affected_machines": [],
            "component_contexts": [part.get("component_assembly")] if part.get("component_assembly") else [],
            "criticality_level": "UNKNOWN",
            "insufficient_evidence": True,
            "note": "Insufficient graph evidence: No machine fitment relationships are recorded in the graph for this part.",
        }

    # Aggregate by product family
    fam_counter = Counter()
    cat_counter = Counter()
    gen_counter = Counter()
    assemblies = set()

    if part.get("component_assembly"):
        assemblies.add(part["component_assembly"])

    for r in rows:
        fam = r.get("product_family") or "Unclassified Family"
        cat = r.get("machine_category") or "Unclassified Category"
        gen = r.get("generation_series") or "General"
        fam_counter[fam] += 1
        cat_counter[cat] += 1
        gen_counter[gen] += 1
        if r.get("assembly"):
            assemblies.add(r["assembly"])
        if r.get("installation_context"):
            assemblies.add(r["installation_context"])

    product_families = [
        {"family_name": fam, "affected_machine_count": count}
        for fam, count in fam_counter.most_common()
    ]
    machine_categories = [
        {"category_name": cat, "affected_machine_count": count}
        for cat, count in cat_counter.most_common()
    ]

    total_machines = len(rows)
    criticality = "HIGH" if total_machines >= 10 else ("MEDIUM" if total_machines >= 3 else "FOCUSED")

    summary_note = (
        f"Graph-verified impact: part is fitted across {total_machines} machine model(s) "
        f"in {len(product_families)} product family/families ({', '.join(f['family_name'] for f in product_families[:3])})."
    )

    return {
        "part_id": part_id,
        "part_name": part.get("part_name"),
        "part_number": part.get("part_number"),
        "component_assembly": part.get("component_assembly"),
        "total_affected_machines_count": total_machines,
        "total_fitment_relationships_count": len(rows),
        "product_families": product_families,
        "machine_categories": machine_categories,
        "affected_machines": rows,
        "component_contexts": sorted(list(assemblies)),
        "criticality_level": criticality,
        "insufficient_evidence": False,
        "note": summary_note,
    }
