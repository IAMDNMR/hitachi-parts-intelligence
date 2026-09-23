"""
backend/app/modules/intelligence/alternatives.py

Requested Part -> candidate alternatives, using only real graph
relationships (same category, shared machine fitment, or an explicit
supersedes/superseded_by link already present on the Part record).

Never auto-replaces, never labels a candidate "approved replacement"
without authoritative evidence (i.e. an explicit supersedes/superseded_by
field from the source data), and never triggers allocation/order.
"""

from typing import Any, Dict, List

from app.modules.intelligence.schemas import AlternativeCandidate
from app.modules.intelligence import interchangeability as ic


def find_alternatives(session, part_id: str) -> List[AlternativeCandidate]:
    part_row = session.run(
        "MATCH (p:Part {part_id: $id}) RETURN p", {"id": part_id}
    ).single()
    if not part_row:
        return []
    part = part_row["p"]
    alternatives: List[AlternativeCandidate] = []

    # 1. Explicit supersession data on the record itself (authoritative).
    if part.get("supersedes_part_number"):
        rows = session.run(
            "MATCH (p:Part {part_number: $pn}) RETURN p LIMIT 3",
            {"pn": part["supersedes_part_number"]},
        ).data()
        for r in rows:
            alternatives.append(AlternativeCandidate(
                part_id=r["p"]["part_id"],
                part_number=r["p"].get("part_number"),
                part_name=r["p"].get("part_name"),
                reason="This part's record states it supersedes this part number.",
                fitment_evidence=None,
                is_authoritative_replacement=True,
            ))
    if part.get("superseded_by"):
        rows = session.run(
            "MATCH (p:Part {part_number: $pn}) RETURN p LIMIT 3",
            {"pn": part["superseded_by"]},
        ).data()
        for r in rows:
            alternatives.append(AlternativeCandidate(
                part_id=r["p"]["part_id"],
                part_number=r["p"].get("part_number"),
                part_name=r["p"].get("part_name"),
                reason="This part's record states it is superseded by this part number.",
                fitment_evidence=None,
                is_authoritative_replacement=True,
            ))

    # 2. Same category/subcategory, fitted to at least one shared machine —
    #    a non-authoritative candidate for manual review only.
    rows = session.run(
        """
        MATCH (p:Part {part_id: $id})
        MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p)
        MATCH (m)-[:HAS_PART_FITMENT]->(alt:Part)
        WHERE alt.part_id <> p.part_id
          AND alt.part_subcategory = p.part_subcategory
        RETURN DISTINCT alt, m.model AS shared_model
        LIMIT 5
        """,
        {"id": part_id},
    ).data()
    seen = {a.part_id for a in alternatives}
    fit = ic.fitment_sets(session, [part_id] + sorted({r["alt"]["part_id"] for r in rows}))
    for r in rows:
        alt = r["alt"]
        if alt["part_id"] in seen:
            continue
        ok, _ = ic.gate(dict(part), dict(alt), fit[part_id], fit[alt["part_id"]])
        if not ok:  # hard filters: orderable part, same specific type, shared fitment
            continue
        seen.add(alt["part_id"])
        alternatives.append(AlternativeCandidate(
            part_id=alt["part_id"],
            part_number=alt.get("part_number"),
            part_name=alt.get("part_name"),
            reason=f"{ic.CANDIDATE_LABEL}: same part type ({ic.type_key(dict(alt))}) and shares graph-confirmed fitment on {r['shared_model']}. Not an approved replacement.",
            fitment_evidence=f"HAS_PART_FITMENT -> {r['shared_model']}",
            is_authoritative_replacement=False,
        ))

    return alternatives
