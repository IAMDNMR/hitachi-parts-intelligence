"""
backend/app/modules/intelligence/intent_resolution.py

Phase 10D — explicit intent, known-entity resolution and result typing for
Parts Intelligence. The deterministic parser in assistant.py extracts raw
signals; this module applies the ENTITY PRIORITY rules on top of them so a
recognised entity is never silently replaced by a broader one:

  1. exact part ID / part number     (a Part is anchored -> part-scoped intents)
  2. exact known dealer name         (a DealerBranch is anchored)
  3. supplier number / name          (handled by supplier_lookup)
  4. machine model / machine type
  5. controlled part-category taxonomy
  6. anything else                   -> UNKNOWN, never an arbitrary entity

It never reads previous-query state. Conversational references ("this part")
are resolved by the caller, and only when the query says so.
"""

import re
from typing import Any, Dict, List, Optional

# intent -> (result_type, source_entity, requested_entity, relationship_required)
INTENT_SPEC: Dict[str, tuple] = {
    "impact_analysis":                 ("MACHINE_RESULTS", "Part", "Machine", "HAS_PART_FITMENT"),
    "machine_list":                    ("MACHINE_RESULTS", None, "Machine", None),
    "machine_parts":                   ("PART_RESULTS", "Machine", "Part", "HAS_PART_FITMENT"),
    "machine_parts_by_category":       ("PART_RESULTS", "Machine", "Part", "HAS_PART_FITMENT"),
    "machine_supplier_by_part_category": ("SUPPLIER_RESULTS", "Machine", "Supplier", "HAS_PART_FITMENT>SUPPLIED_BY"),
    "part_search":                     ("PART_RESULTS", None, "Part", None),
    "part_info":                       ("PART_RESULTS", "Part", "Part", None),
    "alternatives":                    ("PART_RESULTS", "Part", "Part", None),
    "compliance_analysis":             ("PART_RESULTS", "Part", "ComplianceRequirement", None),
    "supplier_risk":                   ("PART_RESULTS", "Part", "Supplier", "SUPPLIED_BY"),
    "mitigation_analysis":             ("PART_RESULTS", "Part", "Part", None),
    "supply_chain":                    ("GRAPH_PATH", "Part", "Depot", "SUPPLIED_BY"),
    "machine_info":                    ("MACHINE_RESULTS", "Machine", "Machine", "HAS_PART_FITMENT"),
    "supplier_summary":                ("SUPPLIER_RESULTS", "Country", "Supplier", "LOCATED_IN"),
    "rfq_search":                      ("PART_RESULTS", "Machine", "Part", None),
    "disruption":                      ("DISRUPTION_ANALYSIS", "Part", "Impact", None),
    "fulfilment_options":              ("PART_RESULTS", "Part", "FulfilmentOption", None),
    "part_dealers":                    ("DEALER_RESULTS", "Part", "DealerBranch", None),
    "dealer_lookup":                   ("DEALER_RESULTS", None, "DealerBranch", None),
    "dealer_list":                     ("DEALER_RESULTS", "Country", "DealerBranch", "LOCATED_IN"),
    "nearest_dealer":                  ("DEALER_RESULTS", "City", "DealerBranch", None),
    "dealer_contact":                  ("DEALER_RESULTS", None, "DealerBranch", None),
    "supplier_lookup":                 ("SUPPLIER_RESULTS", None, "Supplier", "LOCATED_IN"),
    "dealer_supplier_network":         ("NETWORK_RESULTS", "Country", "DealerBranch+Supplier", "LOCATED_IN"),
    "order_status":                    ("ORDER_JOURNEY", "Order", "Shipment", None),
    "shipment_status":                 ("ORDER_JOURNEY", "Shipment", "DealerBranch", None),
    "service_status":                  ("ORDER_JOURNEY", "Order", "ServiceJob", None),
    "general_question":                ("INSUFFICIENT_DATA", None, None, None),
    "unsupported":                     ("UNSUPPORTED_QUERY", None, None, None),
}

# Result types whose UI may offer Graph Insights for a single Part.
PART_SCOPED_RESULT_INTENTS = {
    "part_info", "compliance_analysis", "supplier_risk", "mitigation_analysis",
    "alternatives", "supply_chain", "fulfilment_options", "impact_analysis",
}

_CONTEXT_REF = re.compile(r"\b(this|that|the same|these|those)\s+(part|item|component)s?\b|\bsame part\b", re.I)


def refers_to_context(query: str) -> bool:
    """True only when the user explicitly points back at an earlier part."""
    return bool(_CONTEXT_REF.search(query))


_GENERIC_LEAD = {"hitachi", "the", "de", "van", "der", "den", "gmbh", "kiesel", "teramat", "comac", "scai", "alwark"}
_dealer_cache: Optional[List[Dict[str, str]]] = None


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _load_dealers(session) -> List[Dict[str, str]]:
    global _dealer_cache
    if _dealer_cache is None:
        rows = session.run("MATCH (d:DealerBranch) RETURN d.dealer_id AS id, d.dealer_name AS name").data()
        _dealer_cache = [{"id": r["id"], "name": r["name"], "norm": _norm(r["name"])} for r in rows if r["name"]]
    return _dealer_cache


def resolve_known_dealer(session, query: str) -> Optional[Dict[str, str]]:
    """Exact known dealer name found in the query (whole-word phrase match).

    A dealer matches when its full normalised name, or its first two words
    (e.g. 'pellen machines' for 'Pellen Machines Veldhoven BV'), appears in
    the query as whole words. Names that start with a generic word need the
    full name. Ambiguous prefixes (several dealers share them) resolve to
    nothing rather than to an arbitrary one."""
    q = f" {_norm(query)} "
    best: Dict[str, Any] = {}
    for d in _load_dealers(session):
        words = d["norm"].split()
        keys = {d["norm"]}
        if len(words) >= 2 and words[0] not in _GENERIC_LEAD:
            keys.add(" ".join(words[:2]))
        for k in keys:
            if len(k) >= 6 and f" {k} " in q and len(k) > len(best.get("key", "")):
                best = {"key": k, "matches": [d]}
            elif len(k) >= 6 and f" {k} " in q and len(k) == len(best.get("key", "")) and d not in best["matches"]:
                best["matches"].append(d)
    if best and len({m["norm"] for m in best["matches"]}) == 1:
        return best["matches"][0]
    if best:  # several branches share the prefix: prefer an exact full-name hit, else none
        exact = [m for m in best["matches"] if f" {m['norm']} " in q]
        return exact[0] if len(exact) == 1 else None
    return None


def apply_entity_precedence(session, ext: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Apply the entity-priority rules to the parser's raw extraction.

    Returns ext with a corrected `intent` and resolved `dealer_id`; adds the
    structured-intent fields. Never consults previous queries."""
    q = query.lower()
    intent = ext["intent"]
    has_part = bool(ext.get("part_ref"))
    dealer = None if has_part else resolve_known_dealer(session, query)
    if dealer:
        ext["dealer_id"], ext["dealer_name"] = dealer["id"], dealer["name"]

    # 1. A Part ID / number anchors the question to that Part. "Which machines
    #    use PT-001?" is a Part -> Machine fitment traversal, never the catalogue.
    if has_part and intent in ("machine_list", "part_search", "machine_parts", "machine_parts_by_category"):
        if re.search(r"\b(machines?|models?|use[sd]?|fits?|fitted|compatible|equipment)\b", q):
            intent = "impact_analysis"
        elif intent in ("machine_list", "machine_parts", "machine_parts_by_category"):
            intent = "part_info"

    # 2. A known dealer name anchors the question to that DealerBranch.
    elif dealer and intent in ("machine_list", "part_search", "general_question", "dealer_list", "machine_parts",
                               "machine_parts_by_category"):
        if not re.search(r"\b(supplier|vendor|same (city|town)|nearest|closest|near)\b", q):
            intent = "dealer_lookup"

    ext["intent"] = intent
    spec = INTENT_SPEC.get(intent, ("UNSUPPORTED_QUERY", None, None, None))
    ext["structured_intent"] = {
        "intent": intent, "result_type": spec[0], "source_entity": spec[1],
        "requested_entity": spec[2], "relationship_required": spec[3],
        "part_id": ext.get("part_ref"), "dealer_id": ext.get("dealer_id"),
        "machine_type": ext.get("machine_type"), "part_category": ext.get("part_category"),
        "country": ext.get("country"), "city": ext.get("place"),
    }
    return ext


def result_type_for(intent: str, result: Dict[str, Any]) -> str:
    """Final result type: explicit per intent, downgraded honestly when the
    handler found nothing (never an empty 'success')."""
    if result.get("clarify"):
        return "CLARIFICATION_REQUIRED"
    if result.get("result_type"):
        return result["result_type"]
    rtype = INTENT_SPEC.get(intent, ("UNSUPPORTED_QUERY",))[0]
    data = result.get("data") or {}
    empty = not any(data.get(k) for k in ("candidates", "dealers", "suppliers", "machines", "parts", "category_summary",
                                  "country_counts", "cities_with_both", "stock", "shared_cities")) \
        and not result.get("evidence", {}).get("order")
    if rtype in ("PART_RESULTS", "MACHINE_RESULTS", "DEALER_RESULTS", "SUPPLIER_RESULTS") and empty:
        return "NO_RELATIONSHIP" if INTENT_SPEC.get(intent, (None, None, None, None))[3] else "INSUFFICIENT_DATA"
    return rtype
