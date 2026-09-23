"""
backend/app/modules/intelligence/question_catalog.py

Reads the Parts Intelligence question catalogue from Aura (loaded by
docs/data/neo4j/scripts/load_question_catalog.py) and exposes it to routing:

  * catalog_lookup()  — a query that IS a catalogue question resolves to that
    template's intent and to the REAL nodes the template is wired to
    (ABOUT_PART, ABOUT_MACHINE, ABOUT_MACHINE_TYPE, ABOUT_PART_TYPE,
    ABOUT_DEALER, ABOUT_SUPPLIER, ABOUT_DEPOT, ABOUT_CITY, FILTERS_COUNTRY),
    so a catalogue question can never be re-interpreted by a looser rule.
  * list_catalog()    — categories/questions/intents for the UI launcher.
  * relationship_status() — live counts/provenance for a relationship type
    (e.g. SUPPLIED_BY has 0 real edges), read from the graph, not hardcoded.

The catalogue is routing metadata (INTERNAL_REFERENCE_ONLY); it is never
presented as HCME operational data. If the catalogue has not been loaded,
every function degrades to "no match" and the code-based parser still works.
"""

import re
from typing import Any, Dict, List, Optional

_LOOKUP_Q = """
MATCH (q:QuestionTemplate) WHERE q.enabled = true
WITH q, toLower(trim(q.question_template)) AS norm
WHERE norm = $norm
OPTIONAL MATCH (q)-[rel]->(n) WHERE type(rel) STARTS WITH 'ABOUT_' OR type(rel) = 'FILTERS_COUNTRY'
RETURN q.question_id AS question_id, q.intent AS intent, q.result_type AS result_type,
       q.fallback AS fallback,
       collect({rel: type(rel), label: labels(n)[0], props: properties(n)}) AS links
"""

_LIST_Q = """
MATCH (q:QuestionTemplate)-[:IN_CATEGORY]->(c:QuestionCategory)
OPTIONAL MATCH (q)-[:HAS_INTENT]->(i:Intent)
RETURN c.name AS category, q.question_id AS question_id, q.question_template AS text, q.intent AS intent,
       q.result_type AS result_type, q.enabled AS enabled, q.follow_up_required AS follow_up_required,
       i.relationship_required AS relationship_required
ORDER BY q.question_id
"""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def catalog_lookup(session, query: str) -> Optional[Dict[str, Any]]:
    try:
        row = session.run(_LOOKUP_Q, norm=_norm(query)).single()
    except Exception:
        return None
    if not row:
        return None
    ents: Dict[str, Any] = {}
    for link in row["links"]:
        p, rel = link.get("props") or {}, link.get("rel")
        if rel == "ABOUT_PART":
            ents["part_ref"] = p.get("part_id")
        elif rel == "ABOUT_MACHINE":
            ents["machine_ref"] = (p.get("model") or "").upper() or None
        elif rel == "ABOUT_MACHINE_TYPE":
            ents["machine_type"] = p.get("name")
        elif rel == "ABOUT_PART_TYPE":
            ents["part_category"] = p.get("name")
        elif rel == "ABOUT_DEALER":
            ents["dealer_id"], ents["dealer_name"] = p.get("dealer_id"), p.get("dealer_name")
        elif rel == "ABOUT_SUPPLIER":
            ents["supplier_ref"] = p.get("supplier_number")
        elif rel == "ABOUT_CITY":
            ents["place"] = p.get("name")
        elif rel == "FILTERS_COUNTRY":
            ents["country"] = p.get("code")
        elif rel == "ABOUT_DEPOT":
            ents["depot"] = True
    return {"question_id": row["question_id"], "intent": row["intent"], "result_type": row["result_type"],
            "fallback": row["fallback"], "entities": {k: v for k, v in ents.items() if v}}


def list_catalog(session) -> Dict[str, Any]:
    rows = session.run(_LIST_Q).data()
    cats: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        if r["enabled"]:
            cats.setdefault(r["category"], []).append(
                {k: r[k] for k in ("question_id", "text", "intent", "result_type", "follow_up_required", "relationship_required")})
    rels = session.run(
        "MATCH (r:RelationshipType) RETURN r.name AS name, r.classification AS classification, "
        "r.total_edges AS total_edges, r.real_edges AS real_edges, r.note AS note ORDER BY r.name").data()
    return {"categories": [{"name": k, "questions": v} for k, v in cats.items()],
            "relationship_types": rels, "source": "Aura :QuestionTemplate (INTERNAL_REFERENCE_ONLY)"}


def relationship_status(session, name: str) -> Optional[Dict[str, Any]]:
    row = session.run(
        "MATCH (r:RelationshipType {name: $n}) RETURN r.classification AS classification, "
        "r.total_edges AS total_edges, r.real_edges AS real_edges", n=name).single()
    return dict(row) if row else None
