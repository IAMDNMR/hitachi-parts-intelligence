"""
Interchangeability gate (Phase 11b) - the single place that decides whether one HCME part may even be SHOWN as a
candidate substitute for another.

Principles
  * Text/category similarity is never proof of interchangeability. Hard filters come first: the candidate must be an
    orderable part (not a product-line family record), of the same specific part type, and fitted to at least one machine the
    target part is fitted to.
  * Without an authoritative HCME supersession / compatibility relationship the most we can say is
    "Candidate for Engineering Review". No such data exists yet; the relationship types below are the hooks for it.
  * Similarity remains a supporting signal for ordering candidates that already passed the filters.
"""
import re
from typing import Any, Dict, List, Set, Tuple

FAMILY_RECORD_CLASS = "PRODUCT_LINE_PART_FAMILY"
CANDIDATE_LABEL = "Candidate for Engineering Review"
# Future authoritative data (none is loaded today): (a)-[:SUPERSEDES]->(b), (a)-[:COMPATIBLE_WITH]-(b), (a)-[:NOT_COMPATIBLE_WITH]-(b)
AUTHORITATIVE_RELATIONS = ("SUPERSEDES", "COMPATIBLE_WITH", "NOT_COMPATIBLE_WITH")


def is_family(p: Dict[str, Any]) -> bool:
    """Product-line / family records (e.g. 'Hitachi Genuine Oil Filter') have no part number and are not orderable parts."""
    return p.get("record_class") == FAMILY_RECORD_CLASS


def type_key(p: Dict[str, Any]) -> str:
    """Specific part type. The catalogue sub-category is too coarse in places ('Filter' covers oil AND fuel filters,
    'Battery' covers starter AND traction batteries), so those are refined from the part name."""
    sub = (p.get("part_subcategory") or p.get("part_category") or "").strip().lower()
    name = (p.get("part_name") or "").lower()
    if sub == "filter":
        m = re.search(r"([a-z]+)\s+filter", name)
        return f"{m.group(1)} filter" if m else "filter (unspecified)"
    if sub == "battery":
        m = re.search(r"battery\s*-\s*([a-z]+)", name)
        return f"battery/{m.group(1)}" if m else "battery (unspecified)"
    return sub


def gate(target: Dict[str, Any], cand: Dict[str, Any], target_machines: Set[str], cand_machines: Set[str]) -> Tuple[bool, str]:
    """(passes, reason). Hard filters only - no similarity."""
    if is_family(target):
        return False, "the part is a product-line family record; interchangeability is not assessed for families"
    if is_family(cand):
        return False, "product-line family record, not an orderable part"
    if type_key(cand) != type_key(target):
        return False, f"different part type ({type_key(cand)} vs {type_key(target)})"
    if not target_machines:
        return False, "the part has no machine fitment, so compatibility cannot be assessed"
    if not (target_machines & cand_machines):
        return False, "no shared machine fitment"
    return True, "same part type with shared machine fitment"


def fitment_sets(session, part_ids: List[str]) -> Dict[str, Set[str]]:
    rows = session.run(
        "UNWIND $ids AS id MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part {part_id:id}) RETURN id, collect(m.machine_id) AS ms",
        ids=part_ids).data()
    out: Dict[str, Set[str]] = {i: set() for i in part_ids}
    for r in rows:
        out[r["id"]] = set(r["ms"])
    return out


def authoritative_map(session, target_id: str) -> Dict[str, str]:
    """{other_part_id: SUPERSEDES | COMPATIBLE_WITH | NOT_COMPATIBLE_WITH} from authoritative HCME relationships.
    Empty today: no such data is loaded. This is where it plugs in."""
    rows = session.run(
        """MATCH (a:Part {part_id:$a})-[r]-(b:Part) WHERE type(r) IN $kinds
           RETURN b.part_id AS other, type(r) AS kind""", a=target_id, kinds=list(AUTHORITATIVE_RELATIONS)).data()
    return {r["other"]: r["kind"] for r in rows}
