"""
backend/app/modules/intelligence/compliance.py

Phase 7 Compliance Intelligence.

Traverses canonical graph relationships:
    Part -[:HAS_COMPLIANCE_REQUIREMENT]-> ComplianceRequirement

Preserves real vs synthetic boundaries:
- Real compliance records (e.g., EU Battery Regulation from SRC-039) marked synthetic=False
- Demo compliance scenarios marked synthetic=True / SYNTHETIC DEMO DATA
- Parts without graph evidence return UNKNOWN / INSUFFICIENT EVIDENCE.
"""

from typing import Any, Dict, List

from app.errors.exceptions import NotFoundError


def get_compliance_analysis(session, part_id: str) -> Dict[str, Any]:
    part_row = session.run(
        "MATCH (p:Part {part_id: $id}) RETURN p",
        {"id": part_id},
    ).single()
    if not part_row:
        raise NotFoundError(f"Part '{part_id}' not found")
    part = dict(part_row["p"])

    rows = session.run(
        """
        MATCH (p:Part {part_id: $id})-[r:HAS_COMPLIANCE_REQUIREMENT]->(c:ComplianceRequirement)
        RETURN c.compliance_id AS compliance_id,
               c.name AS name,
               c.regulation_standard AS regulation_standard,
               c.issuing_body AS issuing_body,
               c.requirement_type AS requirement_type,
               c.description AS description,
               c.source_id AS source_id,
               c.confidence AS confidence,
               c.synthetic AS synthetic,
               c.data_source AS data_source,
               r.status AS status,
               r.evidence_type AS evidence_type
        ORDER BY c.name ASC
        """,
        {"id": part_id},
    ).data()

    if not rows:
        return {
            "part_id": part_id,
            "part_name": part.get("part_name"),
            "part_number": part.get("part_number"),
            "overall_status": "UNKNOWN",
            "has_graph_evidence": False,
            "requirements_count": 0,
            "requirements": [],
            "note": "UNKNOWN / INSUFFICIENT EVIDENCE — No compliance standards or regulatory certifications are recorded in the graph for this part.",
        }

    has_synthetic = any(r.get("synthetic") for r in rows)
    has_real = any(not r.get("synthetic") for r in rows)

    if has_real and not has_synthetic:
        prov_note = "All compliance requirements are verified from official HCME publications / EU Regulatory frameworks."
    elif has_synthetic and not has_real:
        prov_note = "SYNTHETIC DEMO DATA — compliance requirements are demo graph records for workflow demonstration only."
    else:
        prov_note = "Mixed provenance — contains both official HCME compliance facts and synthetic demo scenarios."

    return {
        "part_id": part_id,
        "part_name": part.get("part_name"),
        "part_number": part.get("part_number"),
        "overall_status": "COMPLIANT",
        "has_graph_evidence": True,
        "requirements_count": len(rows),
        "requirements": rows,
        "has_synthetic_records": has_synthetic,
        "note": prov_note,
    }
