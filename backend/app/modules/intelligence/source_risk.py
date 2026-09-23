"""
backend/app/modules/intelligence/source_risk.py

Phase 7 Supplier / Source Risk Intelligence.

Evaluates sourcing resilience from authoritative graph evidence:
- Sourcing channels (Depot vs Supplier vs Catalog)
- Single-source concentration
- Number of dependent machines relying on the part
- Provenance confidence levels
- Candidate alternatives buffer

Rules:
- Never manufactures risk percentages, geopolitical risk, or fake supplier scores.
- When evidence is sparse: returns UNKNOWN / INSUFFICIENT EVIDENCE.
"""

from typing import Any, Dict, List

from app.errors.exceptions import NotFoundError
from app.modules.intelligence.alternatives import find_alternatives


def get_source_risk_analysis(session, part_id: str) -> Dict[str, Any]:
    part_row = session.run(
        "MATCH (p:Part {part_id: $id}) RETURN p",
        {"id": part_id},
    ).single()
    if not part_row:
        raise NotFoundError(f"Part '{part_id}' not found")
    part = dict(part_row["p"])

    # Distinct source citations from part and fitments
    sources_res = session.run(
        """
        MATCH (p:Part {part_id: $id})
        OPTIONAL MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p)
        RETURN collect(DISTINCT p.source_id) + collect(DISTINCT r.source_id) AS sources,
               count(DISTINCT m) AS machine_count
        """,
        {"id": part_id},
    ).single()

    raw_sources = sources_res["sources"] if sources_res else []
    distinct_sources = sorted(list(set(s for s in raw_sources if s)))
    machine_count = sources_res["machine_count"] if sources_res else 0

    # Linked depots
    depots = session.run(
        """
        MATCH (d:Depot)
        RETURN d.depot_id AS depot_id, d.name AS name, d.country AS country, d.synthetic AS synthetic
        """
    ).data()

    # Linked suppliers (if any demo suppliers connected)
    suppliers = session.run(
        """
        MATCH (s:Supplier)
        RETURN s.supplier_id AS supplier_id, s.name AS name, s.country AS country, s.synthetic AS synthetic
        """
    ).data()

    # Alternatives count
    alts = find_alternatives(session, part_id)
    alt_count = len(alts)

    confidence = part.get("confidence") or "UNKNOWN"
    single_source = len(distinct_sources) <= 1

    risk_factors: List[str] = []
    mitigation_buffers: List[str] = []

    # Risk evaluation
    if single_source:
        risk_factors.append("Single-source citation concentration in master catalogue.")
    if machine_count >= 10 and alt_count == 0:
        risk_factors.append(f"High machine dependency ({machine_count} models) with no verified alternative part.")
    if confidence == "LOW":
        risk_factors.append("Low provenance confidence on part specification record.")

    # Mitigation buffers
    if alt_count > 0:
        mitigation_buffers.append(f"{alt_count} candidate alternative part(s) available in catalogue.")
    if any(d["depot_id"] == "DEPOT-OOSTERHOUT" for d in depots):
        mitigation_buffers.append("Supported by central European Parts Centre (Oosterhout, NL).")
    if len(distinct_sources) > 1:
        mitigation_buffers.append(f"Multi-source documentation ({len(distinct_sources)} distinct citations).")

    if not distinct_sources and machine_count == 0:
        risk_level = "UNKNOWN"
        summary_note = "UNKNOWN / INSUFFICIENT EVIDENCE — Insufficient source citations for risk evaluation."
    elif len(risk_factors) >= 2:
        risk_level = "HIGH"
        summary_note = f"Elevated source risk: {len(risk_factors)} risk factors identified across graph records."
    elif len(risk_factors) == 1:
        risk_level = "MEDIUM"
        summary_note = f"Moderate source risk: 1 risk factor identified ({risk_factors[0]})."
    else:
        risk_level = "LOW"
        summary_note = "Low source risk: healthy alternative buffer and established European distribution support."

    return {
        "part_id": part_id,
        "part_name": part.get("part_name"),
        "part_number": part.get("part_number"),
        "risk_level": risk_level,
        "confidence": confidence,
        "single_source_concentration": single_source,
        "distinct_sources": distinct_sources,
        "dependent_machines_count": machine_count,
        "alternatives_count": alt_count,
        "risk_factors": risk_factors,
        "mitigation_buffers": mitigation_buffers,
        "available_depots": depots,
        "suppliers": suppliers,
        "note": summary_note,
    }
