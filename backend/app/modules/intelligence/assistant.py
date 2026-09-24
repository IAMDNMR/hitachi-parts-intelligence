"""
backend/app/modules/intelligence/assistant.py

Parts Intelligence — natural-language question answering over the HCME graph.

    question
      -> Gemini: intent + entity extraction   (deterministic fallback)
      -> entity resolution in Neo4j           (part, machine, order, dealer, place)
      -> intent handler: multi-hop graph traversal -> evidence set + provenance
      -> Gemini: answer written ONLY from the evidence (deterministic fallback)

Neo4j provides every fact. Gemini only understands the question and phrases
the answer; it never decides fitment, stock, prices, dealers or statuses.
Every evidence item carries its provenance (SOURCE_DERIVED / DERIVED /
SYNTHETIC_DEMO / NOT_CONNECTED) and the answer must say so.
"""

import json
import re
import time
from typing import Any, Callable, Dict, List, Optional

from app.logging_config.logger import logger
from app.modules.dealer.geocode import resolve_location
from app.modules.dealer.service import (
    co_located,
    dealers_for_machine_categories,
    find_suppliers,
    find_dealers_by_name,
    list_dealers,
    nearest_dealers,
)
from app.modules.intelligence.graph_insights import get_part_graph_insights
from app.modules.intelligence import similarity, disruption, interchangeability
from app.errors.exceptions import NotFoundError
from app.modules.intelligence.part_finder import find_parts, to_card
from app.modules.intelligence.intent_resolution import (
    PART_SCOPED_RESULT_INTENTS,
    apply_entity_precedence,
    refers_to_context,
    result_type_for,
)
from app.modules.intelligence.providers import GeminiLLMProvider, get_llm_provider
from app.modules.intelligence.question_catalog import catalog_lookup

INTENTS = {
    "part_search": "find parts matching a description or a machine (e.g. 'hydraulic filter for ZX210-7')",
    "part_info": "what a specific part is / tell me everything about it / its category",
    "impact_analysis": "which machines use a part / what is affected if it is unavailable",
    "machine_parts": "which parts fit a given machine model",
    "machine_list": "list all machines / machines of a given type or category (e.g. 'show medium excavators')",
    "machine_parts_by_category": "which parts of a given category fit machines of a given type (e.g. 'buckets for medium excavators')",
    "machine_supplier_by_part_category": "which suppliers provide parts of a given category for machines of a given type — requires Machine+PartCategory+Supplier traversal",
    "dealer_supplier_network": "combined dealer and supplier network for a country or city",
    "compliance_analysis": "compliance requirements or regulations for a part",
    "supplier_risk": "supplier, single-source or source risk of a part",
    "mitigation_analysis": "what to do if a part is unavailable / mitigation options",
    "alternatives": "alternative, substitute or similar parts",
    "supply_chain": "where a part comes from, which depot/supplier, stock",
    "fulfilment_options": "how a part can be fulfilled / delivered / fulfilment options",
    "part_dealers": "which dealers can support or supply a part / a machine",
    "dealer_list": "list dealers in a country or city",
    "nearest_dealer": "nearest / closest dealer to a place or to the user",
    "dealer_contact": "contact details of a named dealer",
    "order_status": "status / journey / contents of an order",
    "shipment_status": "where a shipment is / who receives it",
    "service_status": "service job, installation or completion linked to an order",
    "unsupported": "prices, lead times, live ERP stock or anything the graph cannot hold",
    "supplier_lookup": "HCME suppliers by supplier number, name, city or country, or suppliers in the same city as a dealer or the depot",
    "general_question": "general knowledge about machines/parts/maintenance (what is X, how does X work, how often to change X)",
    "rfq_search": "an RFQ-style request with a quantity and/or electrical spec (e.g. 'need 20 units of a 24V starter motor for ZX210LC-7')",
    "disruption": "a what-if scenario: 'what happens if part/supplier X becomes unavailable / is out of stock / fails compliance'",
}

# Europe-only country vocabulary for the deterministic fallback (Gemini returns ISO codes itself).
_COUNTRIES = {
    "netherlands": "NL", "holland": "NL", "dutch": "NL", "germany": "DE", "german": "DE", "france": "FR",
    "belgium": "BE", "italy": "IT", "spain": "ES", "united kingdom": "GB", "uk": "GB", "england": "GB",
    "scotland": "GB", "ireland": "IE", "austria": "AT", "switzerland": "CH", "poland": "PL", "portugal": "PT",
    "denmark": "DK", "sweden": "SE", "norway": "NO", "finland": "FI", "czech": "CZ", "hungary": "HU",
    "romania": "RO", "greece": "GR", "croatia": "HR", "lithuania": "LT", "latvia": "LV", "estonia": "EE",
    "bulgaria": "BG", "serbia": "RS", "iceland": "IS", "cyprus": "CY", "ukraine": "UA",
}

_EXTRACT_SYSTEM = (
    "You extract intent and entities from a question to the Hitachi Construction Machinery Europe "
    "Parts Intelligence assistant. Return JSON only with keys: "
    '"intent" (one of: ' + ", ".join(INTENTS) + "), "
    '"part_ref" (part ID like PT-001, a part number, or the part description words; null if none), '
    '"machine_ref" (EXACT machine model code like ZX210-7 or ZW180; null if none — do NOT put type descriptions here), '
    '"machine_type" (machine type description WITHOUT a model code, e.g. "medium excavator", "wheel loader", "mini excavator"; null if none), '
    '"part_category" (part category name e.g. "bucket", "filter", "undercarriage", "hydraulic pump"; null if none), '
    '"requested_entity" (the thing the user wants to find: "supplier", "dealer", "part", "machine", or null), '
    '"order_ref" (order ID as written; null), "shipment_ref" (shipment ID; null), '
    '"dealer_name" (dealer company name; null), "supplier_ref" (supplier number or supplier company name; null), "country" (ISO 3166-1 alpha-2 code; null), '
    '"place" (city, town or postcode the user named; null — never guess the user\'s location), '
    '"refers_to_context" (true if the user says "this part"/"it"/"this machine" without naming one). '
    "Intent guide: " + "; ".join(f"{k} = {v}" for k, v in INTENTS.items()) + ". "
    "IMPORTANT: preserve ALL entities simultaneously. If the user asks about 'bucket suppliers for medium excavators in Netherlands', "
    "set intent=machine_supplier_by_part_category, machine_type='medium excavator', part_category='bucket', country='NL'. "
    "Never discard machine_type or part_category when supplier or country is present. "
    "Extract only what the user wrote. Do not invent IDs, places or countries."
)

_ANSWER_SYSTEM = (
    "You are the HCME Europe Parts Intelligence assistant. Answer the user's question using ONLY the "
    "JSON evidence provided — it comes from the HCME Neo4j graph and has already been validated. "
    "Rules: never invent parts, machines, dealers, quantities, prices, dates, statuses or relationships; "
    "if the evidence does not contain the answer, say the current HCME Europe dataset does not contain it. "
    "Respect each item's provenance: SOURCE_DERIVED = HCME Europe published data ('Based on the HCME Europe "
    "... dataset'); DERIVED = computed from that data (say how); SYNTHETIC_DEMO = say explicitly 'this is "
    "based on synthetic demo data'; NOT_CONNECTED = say the live HCME system is not connected. "
    "Attribute each fact to its OWN provenance: never describe a synthetic fact (suppliers, stock, BOM "
    "quantities, criticality, certificates, orders, shipments) as HCME published data, and never describe the "
    "HCME SAP supplier master or the dealer locator as synthetic: they are real source data. "
    "Cover every part of the question that the evidence supports (e.g. for an order: status, part, "
    "shipment, receiving dealer and service job). Do not add general knowledge beyond the evidence. "
    "Write British English, plain text (no JSON, no markdown headings), short: 2-6 sentences or a short "
    "list with '- ' bullets. Lead with the direct answer. Use metric units."
)


_GENERAL_SYSTEM = (
    "You are the HCME Europe Parts Intelligence assistant. The user asked a general question about "
    "construction machinery, parts or maintenance. Answer it briefly (2-5 sentences, British English, "
    "metric units, plain text) and start with 'General information (not HCME data):'. Do not state any "
    "HCME-specific fact (prices, stock, intervals for a specific model, dealers) unless it is in the JSON. "
    "Then, if related HCME catalogue parts are listed, end with one sentence naming them by part ID."
)


# ---------------------------------------------------------------------------
# 1. Extraction
# ---------------------------------------------------------------------------

_DEALER_INTENTS = {"dealer_list", "nearest_dealer", "dealer_contact", "part_dealers"}
_QUESTION_WORDS = {"what", "which", "who", "where", "how", "why", "when", "is", "are", "can", "does", "do", "tell", "give", "show", "explain"}


def _confident(ext: Dict[str, Any]) -> bool:
    """True when the deterministic parser found clear signals, so the Gemini
    extraction round trip can be skipped (latency)."""
    if ext["intent"] == "part_search":
        # Short keyword searches ("hydraulic pump", "filter ZX210-7") need no
        # LLM; full-sentence questions go to Gemini for understanding.
        words = ext["raw"].split()
        return len(words) <= 5 and "?" not in ext["raw"] and words[0].lower() not in _QUESTION_WORDS
    # Otherwise only hard identifiers skip the LLM; free phrasing is understood by Gemini.
    return bool(ext.get("part_ref") or ext.get("order_ref") or ext.get("shipment_ref")
                or re.search(r"\d{4}\s?[A-Z]{2}", ext["raw"]))


def _extract(provider, query: str) -> Dict[str, Any]:
    quick = _extract_deterministic(query)
    if _confident(quick) or not isinstance(provider, GeminiLLMProvider):
        return quick
    if isinstance(provider, GeminiLLMProvider):
        try:
            llm = json.loads(provider._generate(_EXTRACT_SYSTEM, query, json_mode=True, timeout=3.0))
            if llm.get("intent") in INTENTS:
                # The deterministic extraction stays the base (it owns machine type, part category, IDs).
                # Gemini may only supply the intent when the parser had none better than a generic search,
                # and fill entity gaps — it can never overwrite an entity the parser already resolved.
                ext = dict(quick)
                if quick["intent"] in ("part_search", "general_question"):
                    ext["intent"] = llm["intent"]
                for k in ("machine_ref", "dealer_name", "supplier_ref", "country", "place", "order_ref", "shipment_ref"):
                    if not ext.get(k) and llm.get(k):
                        ext[k] = llm[k]
                if not ext.get("part_ref") and re.fullmatch(r"(?i)pt-\d{3}|\d{7,8}", str(llm.get("part_ref") or "")):
                    ext["part_ref"] = str(llm["part_ref"]).upper()
                ext["source"] = "gemini"
                return ext
        except Exception as e:
            logger.warning(f"Parts Intelligence extraction degraded to deterministic: {e}")
    return quick


# Words the deterministic parser keys on; misspellings of these are corrected
# before parsing ("dearler" -> "dealer", "netehrlands" -> "netherlands").
_VOCAB = sorted(set(" ".join(_COUNTRIES).split()) | {
    "dealer", "dealers", "nearest", "closest", "contact", "phone", "email", "address", "order", "shipment",
    "compliance", "regulation", "certificate", "supplier", "single", "source", "alternative", "alternatives",
    "substitute", "similar", "replace", "mitigation", "impact", "affected", "unavailable", "machines", "stock",
    "inventory", "depot", "fulfilment", "delivery", "price", "cost", "installed", "service", "tracking",
    "suppliers", "vendor", "vendors",
})


def _correct_typos(query: str) -> str:
    from difflib import get_close_matches
    # A word split by a stray space ("netrehr leands"): try each adjacent pair joined.
    words = query.split()
    common = {"the", "to", "in", "a", "an", "of", "for", "me", "my", "near", "is", "are", "at", "on", "and", "or"}
    for i in range(len(words) - 1):
        a_, b_ = (re.sub(r"[^a-z]", "", w.lower()) for w in (words[i], words[i + 1]))
        if min(len(a_), len(b_)) < 3 or {a_, b_} & (common | set(_VOCAB)):
            continue
        pair = a_ + b_
        if len(pair) >= 7 and get_close_matches(pair, _VOCAB, n=1, cutoff=0.8) and not get_close_matches(a_, _VOCAB, n=1, cutoff=0.8):
            words[i], words[i + 1] = words[i] + words[i + 1], ""
    query = " ".join(w for w in words if w)
    out = []
    for w in re.findall(r"\S+", query):
        core = re.sub(r"[^\w-]", "", w).lower()
        # Skip real inflections of a vocabulary word ("supplies" is not "supplier").
        if len(core) >= 5 and core not in _VOCAB and not re.search(r"\d", core)                 and not any(v[:5] == core[:5] for v in _VOCAB):
            hit = [h for h in get_close_matches(core, _VOCAB, n=3, cutoff=0.8) if h[0] == core[0]][:1]  # typos keep the first letter ('available' must not become 'unavailable')
            if hit:
                w = w.lower().replace(core, hit[0])
        out.append(w)
    return " ".join(out)


def _extract_deterministic(query: str) -> Dict[str, Any]:
    from app.modules.intelligence.graph_query import MACHINE_TYPE_VOCAB, PART_CATEGORY_VOCAB, resolve_machine_type, resolve_part_category
    query = _correct_typos(query)
    q = query.lower()
    pid = re.search(r"\bpt-\d{3}\b", q)
    pn = re.search(r"\b\d{7,8}\b|\b[A-Z]{2}\d{6,10}\b", query)
    order = re.search(r"\border[-\s]?demo[-\s]?\d+|\bord-demo-\d+|\border-[0-9a-f-]{8,}", q)
    ship = re.search(r"\bship-(?:demo-)?[0-9a-f-]+", q)
    machine = re.search(r"\b(z[xw]\d{2,4}[a-z0-9\-]*|eh\d{3,4}[a-z0-9\-]*)\b", q)
    country = next((code for name, code in _COUNTRIES.items() if re.search(rf"\b{name}\b", q)), None)
    place = re.search(r"\b(?:near|nearest to|closest to|close to|in|to|around)\s+([A-Z][a-zA-Z\-']+(?:\s[A-Z][a-zA-Z\-']+)?|\d{4}\s?[A-Z]{2})", query)
    place_v = place.group(1) if place and place.group(1).lower() not in _COUNTRIES else None
    if place_v and place_v.lower().startswith("the same"):
        place_v = None
    postcode = re.search(r"\b\d{4}\s?[A-Z]{2}\b", query)
    if postcode:
        place_v = postcode.group(0)
    same_city = re.search(r"same (?:city|town|place) as (?:dealer )?(.+?)[?.!]*$", query, re.I)
    supplier_no = re.search(r"\b\d{10}\b|\b\d{6}\b", query)
    supplier_nm = re.search(r"supplier (?:called|named) (.+?)[?.!]*$", query, re.I)
    dealer_name = re.search(r"(?:contact|phone|email|address)\b.*?\b(?:for|of)\s+(.+?)[?.!]*$", query, re.I)

    # ---- Phase 10C: machine_type and part_category vocabulary extraction ----
    # Try multi-word vocabulary matches first (longest match wins).
    machine_type_raw = None
    machine_type_neo4j = None
    for vocab_key in sorted(MACHINE_TYPE_VOCAB.keys(), key=len, reverse=True):
        if vocab_key in q:
            machine_type_raw = vocab_key
            machine_type_neo4j = MACHINE_TYPE_VOCAB[vocab_key]
            break

    part_category_raw = None
    part_category_norm = None
    for vocab_key in sorted(PART_CATEGORY_VOCAB.keys(), key=len, reverse=True):
        if vocab_key in q:
            part_category_raw = vocab_key
            part_category_norm = PART_CATEGORY_VOCAB[vocab_key]
            break

    # Detect "requested entity" from leading plural noun patterns.
    requested_entity = None
    if re.search(r"\b(suppliers?|vendors?)\b", q):
        requested_entity = "supplier"
    elif re.search(r"\bdealers?\b", q):
        requested_entity = "dealer"
    elif re.search(r"\bparts?\b", q) and not re.search(r"\bpart number\b|\bpart id\b", q):
        requested_entity = "part"
    elif re.search(r"\bmachines?\b", q):
        requested_entity = "machine"

    def has(*words):
        return any(w in q for w in words)

    # ---- Phase 10E routing that must win over looser rules ----
    early_intent = None
    if re.search(r"\bwhat (?:happens|would happen)\b.*\bif\b|\bwhat if\b", q) and re.search(
            r"\b(unavailable|out of stock|stock ?out|shortage|discontinued|delayed|fails?|failed|fail|lost|disrupt\w*|not (?:available|certified|compliant))\b", q):
        early_intent = "disruption"
    elif re.search(r"\b\d[\d,]*\s*(?:units?|pcs|pieces)\b|\brfq\b|\b(?:need|require)\s+\d[\d,]*\b", q) and not order:
        early_intent = "rfq_search"
    elif machine and not (pid or pn) and re.search(r"\b(tell me about|about|details|profile|specifications?|info)\b", q) \
            and not has("part", "supplier", "dealer"):
        early_intent = "machine_info"
    elif (pid or pn) and re.search(r"\b(available|availability|in stock)\b", q) and not has("compliance", "regulation", "certif", "directive", "mitigation", "risk"):
        early_intent = "supply_chain"
    elif requested_entity == "supplier" and re.search(
            r"\b(how many suppliers|which countries|what countries|suppliers? (?:by|per) country|number of suppliers|suppliers recorded)\b", q):
        early_intent = "supplier_summary"

    # ---- Intent routing — multi-entity intents first ----
    # machine_supplier_by_part_category: "bucket suppliers for medium excavators in NL"
    if early_intent:
        intent = early_intent
    elif machine_type_raw and part_category_raw and requested_entity == "supplier":
        intent = "machine_supplier_by_part_category"
    # machine_parts_by_category: "buckets for medium excavators", "which parts fit medium excavators"
    elif machine_type_raw and (part_category_raw or has("part", "parts", "fit", "compatible", "fitment")) and requested_entity != "supplier":
        intent = "machine_parts_by_category"
    # dealer_supplier_network: "dealers and suppliers in NL", "cities with both dealers and suppliers"
    elif has("dealer") and has("supplier"):
        intent = "dealer_supplier_network"
    # machine_list: "show me medium excavators", "list wheel loaders", "what machines do we have"
    elif requested_entity == "machine" and not part_category_raw and not has("supplier", "dealer", "part", "fit", "compatible"):
        intent = "machine_list"
    elif machine_type_raw and not part_category_raw and requested_entity in ("machine", None) and not has("supplier", "dealer", "part", "fit", "compatible"):
        intent = "machine_list"
    elif has("machines", "machine") and has("what", "list", "show", "tell", "available", "we have") and not has("supplier", "dealer", "part", "fit", "compatible"):
        intent = "machine_list"
    # machine_parts_by_category fallback
    elif part_category_raw and machine_type_raw and not machine:
        intent = "machine_parts_by_category"
    # ---- Original intent routing ----
    elif has("stock", "inventory") and not has("price", "cost"):
        intent = "supply_chain"
    elif has("price", "cost", "how much", "lead time", "discount", "invoice"):
        intent = "unsupported"
    elif has("supplier", "vendor") and not (pid or pn) and not has("risk", "single", "sole", "source") and not machine_type_raw and not part_category_raw:
        intent = "supplier_lookup"
    elif has("shipment", "tracking", "delivered", "who is receiving", "who receives"):
        intent = "shipment_status"
    elif has("service job", "installed", "installation", "service complete", "job complete"):
        intent = "service_status"
    elif order or has("my order", "order status", "status of order", "the order", "which part is in"):
        intent = "order_status"
    elif has("nearest", "closest", "near me", "near ", "close to"):
        intent = "nearest_dealer"
    elif has("contact", "phone", "email", "address") and (has("dealer") or dealer_name):
        intent = "dealer_contact"
    elif has("dealer") and (pid or pn or machine or has("this part", "support")):
        intent = "part_dealers"
    elif has("dealer"):
        intent = "dealer_list"
    elif has("mitigat", "strategy", "what do we do", "what should we do"):
        intent = "mitigation_analysis"
    elif has("compliance", "regulation", "certif", "reach", "directive", "stage v"):
        intent = "compliance_analysis"
    elif has("single-source", "single source", "sole source", "supplier risk", "source risk") or (has("supplier") and (pid or pn)):
        intent = "supplier_risk"
    elif has("alternative", "substitute", "similar", "replace"):
        intent = "alternatives"
    elif has("fulfil", "fulfill", "deliver"):
        intent = "fulfilment_options"
    elif has("come from", "depot", "supply chain", "stock", "inventory"):
        intent = "supply_chain"
    elif has("impact", "affected", "unavailable", "which machines", "machines use", "compatible with this part"):
        intent = "impact_analysis"
    elif machine and not (pid or pn) and has("which parts", "what parts", "parts for", "parts fit"):
        intent = "machine_parts"
    elif (pid or pn) and has("what is", "tell me", "everything", "category", "about", "explain", "relationship"):
        intent = "part_info"
    elif not (pid or pn or order or ship) and re.match(r"(what (is|are)|how (does|do|often|long|to)|why|explain|when should)\b", q):
        intent = "general_question"
    else:
        intent = "part_search"

    return {
        "intent": intent,
        "part_ref": pid.group(0).upper() if pid else (pn.group(0) if pn else None),
        "machine_ref": machine.group(1).upper() if machine else None,
        "machine_type": machine_type_neo4j,          # Phase 10C: normalised category
        "machine_type_raw": machine_type_raw,         # Phase 10C: original text
        "part_category": part_category_norm,          # Phase 10C: normalised category
        "part_category_raw": part_category_raw,       # Phase 10C: original text
        "requested_entity": requested_entity,         # Phase 10C: what user wants
        "order_ref": order.group(0) if order else None,
        "shipment_ref": ship.group(0) if ship else None,
        "dealer_name": dealer_name.group(1).strip() if dealer_name else (same_city.group(1).strip() if same_city else None),
        "supplier_ref": supplier_no.group(0) if supplier_no else (supplier_nm.group(1).strip() if supplier_nm else None),
        "country": country,
        "place": place_v,
        "refers_to_context": has("this part", " it ", "this machine"),
        "raw": query.strip() or "?",
        "source": "deterministic",
    }



# ---------------------------------------------------------------------------
# 2. Resolution
# ---------------------------------------------------------------------------

def _resolve_part(session, ext, query, context_part_id) -> Optional[Dict[str, Any]]:
    ref = (ext.get("part_ref") or "").strip()
    if ref:
        # Entity priority 1-2: exact part ID or exact part number ONLY. A free-text
        # description ("multi-grade oil") is never fuzzy-matched to an arbitrary Part.
        row = session.run(
            "MATCH (p:Part) WHERE toUpper(p.part_id) = toUpper($r) OR p.part_number = $r RETURN p LIMIT 1", r=ref
        ).single()
        if row:
            return dict(row["p"])
        return None
    if context_part_id:
        row = session.run("MATCH (p:Part {part_id: $id}) RETURN p", id=context_part_id).single()
        if row:
            return dict(row["p"])
    return None


def _normalise_order_ref(ref: Optional[str]) -> Optional[str]:
    if not ref:
        return None
    m = re.search(r"demo\D*0*(\d+)", ref.lower())
    return f"order-demo-{int(m.group(1)):03d}" if m else ref.strip().lower()


# ---------------------------------------------------------------------------
# 3. Handlers — each returns {evidence, graph_path, data, fallback, clarify?}
# ---------------------------------------------------------------------------

def _need_part(intent_label: str) -> Dict[str, Any]:
    return {"clarify": f"Which part do you mean? Give a part ID (e.g. PT-001), a part number or a description, and I will check the {intent_label}.",
            "evidence": {}, "graph_path": [], "data": {}}


def _part_brief(p: Dict[str, Any]) -> Dict[str, Any]:
    return {"part_id": p["part_id"], "part_number": p.get("part_number"), "name": p.get("part_name"),
            "category": p.get("part_category"), "subcategory": p.get("part_subcategory"),
            "assembly": p.get("component_assembly"), "description": p.get("description"),
            "provenance": "SOURCE_DERIVED", "source_id": p.get("source_id"), "confidence": p.get("confidence")}


def h_part_search(session, ext, ctx):
    text = ext.get("part_ref") or ctx["query"]
    if similarity.parse_specs(ctx["query"]) and not ext.get("machine_ref"):
        hy = similarity.hybrid_search(session, ctx["query"], limit=ctx["limit"])
        cards = []
        for m in hy["results"]:
            c = _part_card(session, m["part_id"], m["similarity_pct"])
            c["assessment"] = " ".join(m["reasons"])
            cards.append(c)
        if cards:
            top = [{"part_id": c["part_id"], "name": c["part_name"], "match_pct": c["match_pct"]} for c in cards[:5]]
            return {"evidence": {"matches": top, "requested_specs": hy["requested_specs"], "provenance": "SOURCE_DERIVED catalogue; electrical specs read from real part names"},
                    "graph_path": ["Part"], "data": {"candidates": cards},
                    "fallback": f"Found {len(cards)} part(s) for the requested specs. Best match: {cards[0]['part_id']} {cards[0]['part_name']} ({cards[0]['match_pct']}%)."}
    every = find_parts(session, text, ext.get("machine_ref"), limit=500)
    if not every and ext.get("machine_ref"):
        every = find_parts(session, text, None, limit=500)
    cards = every[:ctx["limit"]]
    top = [{"part_id": c["part_id"], "name": c["part_name"], "match_pct": c["match_pct"]} for c in cards[:5]]
    shown = f"; showing the top {len(cards)}" if len(every) > len(cards) else ""
    fb = (f"Found {len(every)} matching part(s) in the HCME Europe catalogue{shown}. Best match: "
          f"{cards[0]['part_id']} {cards[0]['part_name']} ({cards[0]['match_pct']}%)." if cards
          else "No part in the current HCME Europe catalogue matches that description.")
    return {"evidence": {"matches": top, "machine_filter": ext.get("machine_ref"),
                         "provenance": "SOURCE_DERIVED catalogue; match % is DERIVED from term coverage"},
            "graph_path": ["Part", "Machine (fitment filter)"] if ext.get("machine_ref") else ["Part"],
            "data": {"candidates": cards}, "fallback": fb}


def _part_card(session, part_id, pct, machine=None):
    row = session.run("MATCH (p:Part {part_id:$id}) OPTIONAL MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p) "
                      "RETURN p, count(DISTINCT m) AS fits", id=part_id).single()
    return to_card(dict(row["p"]), row["fits"], pct, machine)


def h_rfq(session, ext, ctx):
    """RFQ-style request: ranked parts with spec match, demo-stock check, risks and the reason each was selected."""
    res = similarity.rfq_search(session, ctx["query"], limit=ctx["limit"])
    cards = []
    for m in res["matches"]:
        c = _part_card(session, m["part_id"], m["similarity_pct"], res["parsed"].get("machine_model"))
        c["assessment"] = " ".join(m["reasons"])
        c["risks"] = m["risks"]
        c["commercial"] = {"availability": m["availability"], "price": m["price"], "lead_time": m["lead_time"]}
        c["match_factors"] = m["factors"]
        cards.append(c)
    p = res["parsed"]
    asked = ", ".join(x for x in (f"quantity {p['quantity']}" if p.get("quantity") else "",
                                  ", ".join(f"{k.split('_')[0]} {v:g}" for k, v in p["specs"].items()),
                                  f"machine {p['machine_model']}" if p.get("machine_model") else "") if x)
    fb = (f"RFQ read as: {asked or 'free text'}. " if asked else "") + (
        f"{len(cards)} matching part(s); best is {cards[0]['part_id']} {cards[0]['part_name']} ({cards[0]['match_pct']}%). " if cards
        else "No matching part in the HCME Europe catalogue. ") + " ".join(res["notes"])
    return {"evidence": {"rfq": p, "matches": [{"part_id": m["part_id"], "score": m["similarity_pct"], "risks": m["risks"]} for m in res["matches"]],
                         "provenance": "SOURCE_DERIVED catalogue; stock, price and lead time are NOT_CONNECTED"},
            "graph_path": ["Part", "Machine (fitment)", "InventorySnapshot (demo)"], "data": {"candidates": cards, "rfq": p},
            "fallback": fb.strip(), "result_type": "PART_RESULTS" if cards else "INSUFFICIENT_DATA"}


def h_disruption(session, ext, ctx):
    """What-if scenarios: part unavailable / supplier unavailable / compliance failure / stock shortage."""
    q = ctx["query"].lower()
    part = ctx["part"]
    try:
        if part:
            kind = ("stock_shortage" if re.search(r"out of stock|stock ?out|shortage|low stock|stock", q)
                    else "compliance_failure" if re.search(r"complian|certif|fail", q) else "part_unavailable")
            res = disruption.analyse(session, kind, part_id=part["part_id"])
        else:
            names = [r["n"] for r in session.run("MATCH (:Part)-[:SUPPLIED_BY]->(s:Supplier) RETURN DISTINCT s.name AS n").data()]
            hit = next((n for n in sorted(names, key=len, reverse=True) if n.lower() in q), None)
            if not hit:
                m = re.search(r"if\s+(?:the\s+)?(?:supplier\s+)?(.+?)\s+(?:becomes|is|goes|fails|stops|are)\b", q)
                hit = m.group(1).strip() if m else None
            if not hit:
                return _need_part("disruption scenario")
            res = disruption.analyse(session, "supplier_unavailable", supplier=hit)
    except NotFoundError as exc:
        return {"clarify": f"{exc} Give a part ID (e.g. PT-031) or a supplier name.", "evidence": {}, "graph_path": [], "data": {}}
    aff = res["affected"]
    brief = {"scenario": res["scenario"], "trigger": res["trigger"], "summary": res["summary"],
             "provenance": res["provenance"], "supplier_dependency": res.get("supplier_dependency"),
             "counts": {"parts": len(aff["parts"]), "assemblies": len(aff["assemblies"]), "machines": len(aff["machines"]),
                        "customers": len(aff["customers"]), "orders": len(aff["orders"])},
             "customers_note": aff.get("customers_note"), "notes": res.get("notes", []),
             "mitigation": [{"target": m["target"], "explanation": m["explanation"], "label": m["label"], "candidates": m["candidates"][:3]} for m in res["mitigation"]]}
    return {"evidence": {"disruption": brief}, "graph_path": ["Supplier", "Part", "Assembly", "Machine"] if res["scenario"] == "supplier_unavailable" else ["Part", "Assembly", "Machine"],
            "data": {"machines": aff["machines"][:40], "disruption": brief}, "fallback": res["summary"], "result_type": "DISRUPTION_ANALYSIS"}


def h_machine_parts(session, ext, ctx):
    if not ext.get("machine_ref"):
        return {"clarify": "Which machine model do you mean (for example ZX210-7 or ZW180-7)?", "evidence": {}, "graph_path": [], "data": {}}
    return h_part_search(session, {**ext, "part_ref": None}, ctx)


def _insights(session, part):
    return get_part_graph_insights(session, part["part_id"])


def h_part_info(session, ext, ctx):
    p = ctx["part"]
    if not p:
        return _need_part("details")
    gi = _insights(session, p)
    stock = session.run(
        "MATCH (:Part {part_id: $id})-[:HAS_SYNTHETIC_INVENTORY]->(i:InventorySnapshot) RETURN i.location_id AS location, i.quantity AS qty",
        id=p["part_id"]).data()
    orders = session.run(
        "MATCH (o:Order)-[:FOR_PART]->(:Part {part_id: $id}) RETURN o.id AS order_id, o.status AS status", id=p["part_id"]).data()
    ev = {
        "part": _part_brief(p),
        "fits": {"machines": gi["impact"]["affected_machines"],
                 "examples": [m["name"] for m in gi["impact"]["machines"][:6]], "provenance": "SOURCE_DERIVED"},
        "assemblies": [{"name": a["name"], "criticality": a["criticality"]} for a in gi["impact"]["assemblies"]],
        "suppliers": [{"name": s["name"], "share_pct": s["share_pct"]} for s in gi["supplier_risk"]["part_suppliers"]],
        "single_point_of_failure": gi["supplier_risk"]["spof"],
        "compliance": {"requirements": sorted({r["name"] for r in gi["compliance"]["requirements"]}),
                       "gaps": gi["compliance"]["gaps"]},
        "alternatives": [{"part_id": a["part_id"], "name": a["part_name"], "similarity_pct": a["similarity_pct"]}
                         for a in gi["mitigation"]["alternatives"][:3]],
        "depot_stock": stock or "none recorded",
        "orders": orders or "none linked",
        "provenance_notes": [gi["impact"]["data_basis"], gi["supplier_risk"]["data_basis"],
                             "Depot stock and orders: SYNTHETIC_DEMO. Live HCME ERP stock/orders: NOT_CONNECTED."],
    }
    sups = ", ".join(s["name"] for s in gi["supplier_risk"]["part_suppliers"]) or "none recorded (the supplier master has no part numbers)"
    fb = (f"{p['part_id']} is {p.get('part_name')} ({p.get('part_category')} / {p.get('part_subcategory')}), "
          f"fitted to {gi['impact']['affected_machines']} machine model(s) according to HCME Europe source data. "
          f"Supplier(s): {sups}; compliance gaps: {len(gi['compliance']['gaps'])}; "
          f"{len(gi['mitigation']['alternatives'])} candidate alternative(s). Suppliers, stock, certificates and "
          "orders are based on synthetic demo data; live HCME ERP data is not connected.")
    return {"evidence": ev, "deterministic": True, "graph_path": ["Part", "Machine", "Assembly", "Supplier", "ComplianceRequirement",
                                           "Alternative Part", "InventorySnapshot", "Order"],
            "data": {"part_id": p["part_id"], "candidates": [_card_for(session, p)]}, "fallback": fb}


def _candidate_card(session, p):
    """Card for an 'alternatives' answer: no match % (it is not a search hit) and an honest status line."""
    c = _card_for(session, p)
    c["match_pct"] = None
    c["assessment"] = "Candidate for engineering review, not an approved substitute."
    return c


def _card_for(session, p):
    n = session.run("MATCH (m:Machine)-[:HAS_PART_FITMENT]->(:Part {part_id: $id}) RETURN count(m) AS n", id=p["part_id"]).single()["n"]
    return to_card(p, n, 100)


def h_impact(session, ext, ctx):
    p = ctx["part"]
    if not p:
        return _need_part("impact")
    i = _insights(session, p)["impact"]
    ev = {"part": _part_brief(p), "affected_machines": i["affected_machines"], "total_bom_qty": i["total_bom_qty"],
          "machines": [f"{m['name']} ({m['category']})" for m in i["machines"][:25]],
          "critical_paths": [f"{a['name']} (qty {a['qty']})" for a in i["critical_paths"]],
          "assemblies": [f"{a['name']} ({a['criticality']})" for a in i["assemblies"]],
          "provenance": i["data_basis"]}
    machines = i["machines"]
    ev["machine_records"] = [{"machine_id": m["machine_id"], "model": m["name"], "category": m["category"],
                              "family": m["family"]} for m in machines]
    if machines:
        fb = (f"{p['part_id']} ({p.get('part_name')}) fits {len(machines)} machine model(s) according to HCME Europe "
              f"fitment data: " + ", ".join(m["name"] for m in machines[:12]) + ("…" if len(machines) > 12 else "") + ".")
    else:
        fb = f"No machine is recorded as fitted with {p['part_id']} in the HCME Europe fitment data."
    return {"evidence": ev, "graph_path": ["Part", "HAS_PART_FITMENT", "Machine"],
            "data": {"part_id": p["part_id"], "machines": ev["machine_records"], "part": _part_brief(p)}, "fallback": fb}


def h_compliance(session, ext, ctx):
    p = ctx["part"]
    if not p:
        return _need_part("compliance requirements")
    c = _insights(session, p)["compliance"]
    ev = {"part": _part_brief(p), "status": c["status"],
          "requirements": [{"name": r["name"], "standard": r["standard"], "via": r["via"], "held": r["held"]} for r in c["requirements"]],
          "gaps": c["gaps"], "provenance": c["data_basis"]}
    fb = (f"{p['part_id']} has {len(c['requirements'])} compliance requirement(s) and {len(c['gaps'])} gap(s). "
          "Assembly-level assignments and certificates are synthetic demo data.")
    return {"evidence": ev, "graph_path": ["Part", "Assembly", "ComplianceRequirement"], "data": {"part_id": p["part_id"]}, "fallback": fb}


def h_supplier_risk(session, ext, ctx):
    p = ctx["part"]
    if not p:
        return _need_part("supplier risk")
    s = _insights(session, p)["supplier_risk"]
    if not s.get("connected"):
        ev = {
            "part": _part_brief(p),
            "status": "NOT_CONNECTED",
            "connected": False,
            "supplier_master_count": s.get("supplier_master_count", 1720),
            "single_point_of_failure": s["spof"],
            "provenance": s["data_basis"],
            "reason": s.get("reason"),
            "required_source": s.get("required_source"),
        }
        fb = (f"Supplier master data is available (1,720 HCME suppliers), but supplier-to-part sourcing relationships "
              f"are not connected in the current HCME source data. Single-source and supplier risk for {p['part_id']} "
              "cannot be calculated without verified SAP purchasing/source-list/PO data.")
        return {"evidence": ev, "graph_path": ["Part", "Supplier (NOT_CONNECTED)"], "data": {"part_id": p["part_id"], "status": "NOT_CONNECTED"}, "fallback": fb}
    ev = {"part": _part_brief(p), "suppliers": s["part_suppliers"], "dual_source": s["dual_source"],
          "single_point_of_failure": s["spof"], "provenance": s["data_basis"]}
    fb = (f"{p['part_id']} is {'dual' if s['dual_source'] else 'single'}-sourced. {s['spof']['reason']}")
    return {"evidence": ev, "graph_path": ["Part", "Supplier", "Assembly (criticality)"], "data": {"part_id": p["part_id"]}, "fallback": fb}


def h_mitigation(session, ext, ctx):
    p = ctx["part"]
    if not p:
        return _need_part("mitigation options")
    m = _insights(session, p)["mitigation"]
    ev = {"part": _part_brief(p), "summary": m["executive_summary"], "alternatives": m["alternatives"],
          "preferred_substitutes_exist": m["preferred_substitutes_exist"], "provenance": m["data_basis"]}
    return {"evidence": ev, "graph_path": ["Part", "Machine", "Alternative Part", "Supplier", "ComplianceRequirement"],
            "data": {"part_id": p["part_id"], "mitigation_options": m["alternatives"]},
            "fallback": m["executive_summary"], "explanation_override": m["executive_summary"]}


def h_machine_info(session, ext, ctx):
    """Machine profile: the Machine node itself plus what is fitted to it (Machine -[:HAS_PART_FITMENT]-> Part)."""
    ref = ext.get("machine_ref")
    rows = session.run(
        """MATCH (m:Machine) WHERE toUpper(m.model) = $r OR toUpper(m.model) STARTS WITH $r
           RETURN m.machine_id AS machine_id, m.model AS model, m.machine_category AS category,
                  m.machine_subcategory AS subcategory, m.product_family AS family,
                  m.engine_rated_power AS engine_rated_power,
                  coalesce(m.operating_weight_published, m.operating_weight_kg) AS operating_weight,
                  m.source_id AS source_id, m.official_overview_text AS overview
           ORDER BY m.model LIMIT 5""", r=(ref or "").upper()).data()
    if not rows:
        return {"clarify": "Which machine model do you mean (for example ZX210LC-7)?", "evidence": {}, "graph_path": [], "data": {}}
    m = rows[0]
    fitted = session.run(
        "MATCH (:Machine {machine_id:$id})-[:HAS_PART_FITMENT]->(p:Part) RETURN p.part_id AS part_id, p.part_name AS name "
        "ORDER BY p.part_id", id=m["machine_id"]).data()
    ev = {"machine": m, "fitted_parts": fitted, "provenance": f"SOURCE_DERIVED — HCME Europe machine catalogue ({m['source_id']})"}
    fb = (f"{m['model']} is a {m['subcategory'] or m['category']} ({m['family'] or 'HCME'}), operating weight "
          f"{m['operating_weight'] or 'not published'}, engine power {m['engine_rated_power'] or 'not published'}. "
          f"{len(fitted)} catalogue part(s) are recorded as fitted (HAS_PART_FITMENT). Based on the HCME Europe machine catalogue.")
    cards = [_card_for(session, dict(session.run("MATCH (p:Part {part_id:$i}) RETURN p", i=f["part_id"]).single()["p"])) for f in fitted[:6]]
    return {"evidence": ev, "graph_path": ["Machine", "HAS_PART_FITMENT", "Part"],
            "data": {"machines": [{"machine_id": m["machine_id"], "model": m["model"], "category": m["category"], "family": m["family"]}],
                     "candidates": cards, "machine": m, "fitted_parts": fitted}, "fallback": fb}


def h_supplier_summary(session, ext, ctx):
    rows = session.run(
        """MATCH (s:Supplier {data_source:'HCME_SAP_SUPPLIER_MASTER'})
           RETURN s.country AS country, s.country_name AS country_name, count(s) AS suppliers ORDER BY suppliers DESC""").data()
    total = sum(r["suppliers"] for r in rows)
    ev = {"total_suppliers": total, "countries": len(rows), "by_country": rows[:15],
          "provenance": "SOURCE_DERIVED — HCME SAP supplier master (number, name, city, country only)"}
    fb = (f"The HCME SAP supplier master records {total} suppliers in {len(rows)} countries. Most: "
          + ", ".join(f"{r['country_name'] or r['country']} ({r['suppliers']})" for r in rows[:6]) + ".")
    return {"evidence": ev, "graph_path": ["Supplier", "City", "Country"], "data": {"country_counts": rows}, "fallback": fb}


def h_dealer_lookup(session, ext, ctx):
    """A known DealerBranch, resolved by exact name (never the machine catalogue)."""
    rows = session.run(
        """MATCH (d:DealerBranch) WHERE d.dealer_id = $id
           OPTIONAL MATCH (d)-[:LOCATED_IN]->(c:City)-[:IN_COUNTRY]->(co:Country)
           RETURN d.dealer_id AS dealer_id, d.dealer_name AS dealer_name, d.city AS city, d.country AS country,
                  d.address AS address, d.phone AS phone, d.email AS email, d.website AS website,
                  d.latitude AS latitude, d.longitude AS longitude, d.source_id AS source_id,
                  d.data_class AS data_class, d.confidence AS confidence,
                  c.name AS city_node, co.name AS country_name""", id=ext.get("dealer_id")).data()
    if not rows:
        return {"clarify": "Which dealer do you mean? Give the dealer name or a city.", "evidence": {}, "graph_path": [], "data": {}}
    d = rows[0]
    ev = {"dealer": d, "provenance": f"SOURCE_DERIVED — HCME Europe dealer locator ({d['source_id']}, {d['data_class']})"}
    where = ", ".join(x for x in (d["city"], d["country"]) if x)
    fb = (f"{d['dealer_name']}{' — ' + where if where else ''}. Address: {d['address'] or 'not published'}; "
          f"phone: {d['phone'] or 'not published'}; email: {d['email'] or 'not published'}. "
          f"Based on the HCME Europe dealer dataset ({d['source_id']}).")
    return {"evidence": ev, "graph_path": ["DealerBranch", "City", "Country"], "data": {"dealers": [d]}, "fallback": fb}


def _alternatives_by_domain(session, ext, ctx):
    """'Alternatives for <product domain>' with no specific Part: resolve the domain from the catalogue's own
    part_subcategory values, then look for the requested qualifier in real Part records. Never substitutes
    the UI's previously selected Part."""
    q = _norm_words(ctx["query"])
    subs = [r["s"] for r in session.run(
        "MATCH (p:Part) WHERE p.part_subcategory IS NOT NULL RETURN DISTINCT p.part_subcategory AS s").data()]
    hits = sorted((s_ for s_ in subs if s_.lower() in q), key=len, reverse=True)
    if not hits:
        return {"clarify": "Which part or product type do you want alternatives for? Give a part ID (e.g. PT-030) "
                           "or a product type such as engine oil.", "evidence": {}, "graph_path": [], "data": {}}
    domain = hits[0]
    parts = session.run(
        "MATCH (p:Part {part_subcategory: $d}) RETURN p ORDER BY p.part_id", d=domain).data()
    parts = [dict(r["p"]) for r in parts]
    qualifiers = [w for w in ("multi-grade", "multigrade", "multi grade", "synthetic", "10w", "15w", "5w") if w in q]
    matching = [x for x in parts if not qualifiers or any(
        w in _norm_words(f"{x.get('part_name')} {x.get('description')}") for w in qualifiers)]
    ev = {"product_domain": domain, "requested_qualifier": qualifiers or None,
          "domain_parts": [{"part_id": x["part_id"], "name": x["part_name"]} for x in parts],
          "parts_matching_qualifier": [x["part_id"] for x in matching if qualifiers],
          "provenance": "SOURCE_DERIVED — HCME Europe catalogue. Whether one part replaces another is not "
                        "recorded; listed parts are candidates for engineering review, not approved substitutes."}
    if qualifiers and not matching:
        fb = (f"No verified {qualifiers[0]} {domain.lower()} alternative is recorded in the current HCME Europe catalogue. "
              f"The catalogue lists {len(parts)} {domain.lower()} product(s) ("
              + ", ".join(f"{x['part_id']} {x['part_name']}" for x in parts) + ") but none records that attribute.")
        cards = [_candidate_card(session, x) for x in parts[:6]]
        return {"evidence": ev, "graph_path": ["Part (product domain)"], "result_type": "INSUFFICIENT_DATA",
                "data": {"candidates": cards}, "fallback": fb}
    fb = (f"The catalogue lists {len(matching)} {domain.lower()} product(s): "
          + ", ".join(f"{x['part_id']} {x['part_name']}" for x in matching[:6])
          + ". These are candidates for engineering review, not approved substitutes.")
    return {"evidence": ev, "graph_path": ["Part (product domain)"],
            "data": {"candidates": [_candidate_card(session, x) for x in matching[:6]]}, "fallback": fb}


def _norm_words(text: str) -> str:
    return re.sub(r"[^a-z0-9 \-]+", " ", (text or "").lower())


def h_alternatives(session, ext, ctx):
    p = ctx["part"]
    if not p:
        return _alternatives_by_domain(session, ext, ctx)
    m = _insights(session, p)["mitigation"]
    ev = {"part": _part_brief(p),
          "alternatives": [{k: a[k] for k in ("part_id", "part_name", "similarity_pct", "suppliers", "compliance_gaps", "availability")} for a in m["alternatives"]],
          "provenance": "Similarity is DERIVED from HCME catalogue taxonomy and fitment overlap; suppliers, stock and certificates are SYNTHETIC_DEMO. No authoritative HCME supersession data is connected, so alternatives are candidates for engineering review, not approved replacements."}
    if m["alternatives"]:
        fb = (f"Candidate for Engineering Review for {p['part_id']}: {m['alternatives'][0]['part_id']} - same part type and shares machine fitment "
              f"(text similarity {m['alternatives'][0]['similarity_pct']}%, a supporting signal only). It is not an approved replacement: no HCME supersession or "
              "interchangeability data is loaded.")
    elif interchangeability.is_family(p):
        fb = f"{p['part_id']} is a product-line family record, not an orderable part, so no substitute is assessed for it."
    else:
        fb = (f"No alternatives are available for {p['part_id']}. Other parts of the same type exist in the catalogue, but none is fitted to the same "
              "machine models, so none can be offered as a candidate. No HCME supersession or interchangeability data is loaded.")
        ev["alternatives_available"] = False
    return {"evidence": ev, "graph_path": ["Part", "Machine", "Alternative Part"], "data": {"part_id": p["part_id"]}, "fallback": fb,
            "deterministic": not m["alternatives"],  # a plain "not available" is stated as is, not reworded by the LLM
            "result_type": None if m["alternatives"] else "INSUFFICIENT_DATA"}


def h_supply_chain(session, ext, ctx):
    p = ctx["part"]
    if not p:
        return _need_part("supply chain")
    rows = session.run(
        """MATCH (p:Part {part_id: $id})
           OPTIONAL MATCH (p)-[l:SUPPLIED_BY]->(s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
           WITH p, collect({supplier: s.name, country: s.country, share_pct: l.share_pct}) AS suppliers
           OPTIONAL MATCH (p)-[:HAS_SYNTHETIC_INVENTORY]->(i:InventorySnapshot)
           OPTIONAL MATCH (d:Depot {depot_id: i.location_id})
           OPTIONAL MATCH (b:DealerBranch {dealer_id: i.location_id})
           RETURN suppliers, collect({location: coalesce(d.name + ', ' + d.city, b.dealer_name, i.location_id), type: i.location_type, qty: i.quantity}) AS stock""",
        id=p["part_id"]).single()
    depot = session.run("MATCH (d:Depot) RETURN d.name AS name, d.city AS city, d.country AS country, d.storage_locations AS storage_locations, d.source_id AS source_id").data()
    ev = {"part": _part_brief(p),
          "suppliers": [s for s in rows["suppliers"] if s["supplier"]], "suppliers_provenance": "SOURCE_DERIVED (HCME SAP supplier master; it has no part numbers, so no supplier is linked to a part)",
          "stock": [s for s in rows["stock"] if s["location"]], "stock_provenance": "SYNTHETIC_DEMO (no live HCME stock feed is connected)",
          "hcme_depot": depot, "depot_provenance": "SOURCE_DERIVED (published facility facts; no per-part stock)",
          "transport": "NOT_CONNECTED — no HCME carrier, tariff or transit data is connected"}
    stock = [s for s in rows["stock"] if s["location"]]
    sups = [s for s in rows["suppliers"] if s["supplier"]]
    fb = (f"{p['part_id']} ({p.get('part_name')}): " +
          (f"demo stock of {sum(s['qty'] or 0 for s in stock)} unit(s) at " + ", ".join(s["location"] for s in stock) + " (synthetic demo data — no live HCME stock feed is connected). "
           if stock else "no stock is recorded for it (no live HCME stock feed is connected). ") +
          (f"Supplier link: {', '.join(s['supplier'] for s in sups)}. " if sups else "No supplier is recorded for this part (the HCME supplier master has no part numbers)."))
    return {"evidence": ev, "graph_path": ["Part", "Supplier", "InventorySnapshot", "Depot"],
            "data": {"part_id": p["part_id"], "part": _part_brief(p), "stock": stock, "supply_suppliers": sups},
            "fallback": fb}


def h_fulfilment(session, ext, ctx):
    out = h_supply_chain(session, ext, ctx)
    if "clarify" in out:
        return out
    out["evidence"]["fulfilment_rule"] = ("A fulfilment option is offered for every stock location holding the part "
                                          "(DERIVED from the stock above); transport mode, carrier, transit time and "
                                          "cost are NOT_CONNECTED and are not shown.")
    out["graph_path"] = out["graph_path"] + ["FulfilmentOption"]
    return out


def _place_and_country(ext):
    return ext.get("place"), (ext.get("country") or None)


def h_dealer_list(session, ext, ctx):
    place, country = _place_and_country(ext)
    if not country and not place:
        return {"clarify": "Which country or city should I list Hitachi dealers for?", "evidence": {}, "graph_path": [], "data": {}}
    rows = list_dealers(session, country=country, city=place) if place else list_dealers(session, country=country)
    if place and not rows:
        return h_nearest(session, ext, ctx)
    ev = {"filter": {"country": country, "city": place}, "count": len(rows),
          "dealers": [_dealer_brief(d) for d in rows[:30]], "provenance": "SOURCE_DERIVED — HCME Europe dealer locator (SRC-049)"}
    fb = f"The HCME Europe dealer dataset lists {len(rows)} dealer location(s) for {place or country}."
    return {"evidence": ev, "graph_path": ["DealerBranch"], "data": {"dealers": rows}, "fallback": fb}


def _dealer_brief(d):
    out = {k: d.get(k) for k in ("dealer_id", "dealer_name", "city", "country", "address", "phone", "email", "website")}
    if "distance_km" in d:
        out["distance_km"] = d["distance_km"]
    return out


def h_nearest(session, ext, ctx):
    place, country = _place_and_country(ext)
    if not place and country and not re.search(r"\b(near|to|from|closest to) me\b|\bmy (location|site|position)", ctx["query"].lower()):
        return h_dealer_list(session, ext, ctx)  # "all dealers near the Netherlands" = the country's dealers
    if not place:
        where = f" in {country}" if country else ""
        return {"clarify": f"Which city or postcode{where} should I use to find the nearest Hitachi dealer?",
                "evidence": {}, "graph_path": [], "data": {}}
    loc = resolve_location(session, place, country)
    if not loc:
        return {"clarify": f"I could not locate '{place}'. Please give another city or a postcode.", "evidence": {}, "graph_path": [], "data": {}}
    rows = nearest_dealers(session, loc["lat"], loc["lon"], country=country, limit=5)
    ev = {"location": {"query": place, "resolved": loc["name"], "source": loc["source"]},
          "ranking": "straight-line (great-circle) distance from the resolved location, DERIVED",
          "nearest": [_dealer_brief(d) for d in rows],
          "provenance": "Dealers: SOURCE_DERIVED — HCME Europe dealer locator (SRC-049). Dealers without coordinates are excluded."}
    fb = (f"Nearest Hitachi dealer to {place}: {rows[0]['dealer_name']}"
          f"{', ' + rows[0]['city'] if rows[0]['city'] else ''} ({rows[0]['distance_km']} km, straight line)." if rows
          else f"No dealer with coordinates found near {place}.")
    return {"evidence": ev, "graph_path": ["Location", "DealerBranch (distance)"], "data": {"dealers": rows, "location": loc}, "fallback": fb}


def h_dealer_contact(session, ext, ctx):
    if ext.get("dealer_name"):
        rows = find_dealers_by_name(session, ext["dealer_name"])
        if rows:
            ev = {"dealers": [_dealer_brief(d) for d in rows], "provenance": "SOURCE_DERIVED — HCME Europe dealer locator (SRC-049)"}
            d = rows[0]
            fb = f"{d['dealer_name']} ({d['city']}, {d['country']}): phone {d['phone'] or 'not published'}, email {d['email'] or 'not published'}."
            return {"evidence": ev, "graph_path": ["DealerBranch"], "data": {"dealers": rows}, "fallback": fb}
    if ext.get("place"):
        return h_nearest(session, ext, ctx)
    return {"clarify": "Which dealer do you need contact details for? Give the dealer name or a city/postcode.", "evidence": {}, "graph_path": [], "data": {}}


def h_part_dealers(session, ext, ctx):
    p = ctx["part"]
    machine = ext.get("machine_ref")
    if not p and not machine:
        return _need_part("dealer support")
    if p:
        cats = session.run("MATCH (m:Machine)-[:HAS_PART_FITMENT]->(:Part {part_id: $id}) RETURN collect(DISTINCT m.machine_category) AS c", id=p["part_id"]).single()["c"]
    else:
        cats = session.run("MATCH (m:Machine) WHERE toLower(m.model) CONTAINS toLower($m) RETURN collect(DISTINCT m.machine_category) AS c", m=machine).single()["c"]
    country = ext.get("country")
    rows = dealers_for_machine_categories(session, cats, country=country, limit=15)
    ev = {"part": _part_brief(p) if p else None, "machine": machine, "machine_categories": cats,
          "dealers": [_dealer_brief(d) for d in rows], "country_filter": country,
          "relationship": "DERIVED: dealers whose published HCME product categories cover the machine categories this part/machine belongs to.",
          "not_available": "No verified part-level dealer relationship or dealer stock exists in the HCME Europe dataset."}
    fb = (f"No verified dealer-to-part relationship exists; {len(rows)} dealer(s){' in ' + country if country else ''} "
          f"handle the machine categories ({', '.join(cats)}) this {'part fits' if p else 'machine belongs to'}.")
    return {"evidence": ev, "graph_path": ["Part", "Machine", "Machine category", "DealerBranch (product categories)"],
            "data": {"dealers": rows, "part_id": p["part_id"] if p else None}, "fallback": fb}


_ORDER_Q = """
MATCH (o:Order {id: $id})
OPTIONAL MATCH (o)-[:FOR_PART]->(p:Part)
OPTIONAL MATCH (o)-[:BASED_ON_ALLOCATION]->(a:Allocation)
OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
OPTIONAL MATCH (sh)-[:SHIPPED_TO]->(d:DealerBranch)
OPTIONAL MATCH (dest:DealerBranch {dealer_id: o.destinationBranchId})
WITH o, p, a, sh, coalesce(d, dest) AS dl
OPTIONAL MATCH (sh)-[:HAS_SERVICE_JOB]->(j:ServiceJob)
RETURN o {.id, .status, .quantity, .partNumber, .provenance, .synthetic, .createdAt} AS order,
       p {.part_id, .part_name, .part_number} AS part,
       a {.id, .status, .sourceId, .quantity} AS allocation,
       sh {.shipment_id, .status, .carrier, .tracking_number, .eta, .shipped_at, .delivered_at, .origin, .synthetic} AS shipment,
       dl {.dealer_id, .dealer_name, .city, .country, .phone} AS dealer,
       j {.service_job_id, .status, .service_type, .received_at, .installed_at, .completed_at, .synthetic} AS service_job,
       [(sh)-[:HAS_EVENT]->(e:ShipmentEvent) | e {.event_type, .location, .timestamp, .description}] AS shipment_events,
       [(j)-[:HAS_EVENT]->(se:ServiceEvent) | se {.event_type, .timestamp, .description}] AS service_events
"""


def h_order(session, ext, ctx):
    oid = _normalise_order_ref(ext.get("order_ref"))
    if not oid and ext.get("shipment_ref"):
        r = session.run("MATCH (o:Order)-[:HAS_SHIPMENT]->(s:Shipment) WHERE toLower(s.shipment_id) = toLower($s) RETURN o.id AS id", s=ext["shipment_ref"]).single()
        oid = r["id"] if r else None
    if not oid:
        demo = session.run("MATCH (o:Order) RETURN o.id AS id ORDER BY id").value()
        return {"clarify": ("Which order do you mean? Live HCME ERP/order data is not currently connected, so I can only "
                            f"look up orders in the demo dataset: {', '.join(demo) or 'none'}."),
                "evidence": {}, "graph_path": [], "data": {}}
    row = session.run(_ORDER_Q, id=oid).single()
    if not row or not row["order"]:
        return {"clarify": f"Order '{oid}' is not in the current HCME Europe dataset. Live HCME ERP/order data is not connected.",
                "evidence": {}, "graph_path": [], "data": {}}
    ev = {k: _plain(row[k]) for k in ("order", "part", "allocation", "shipment", "dealer", "service_job", "shipment_events", "service_events")}
    ev["provenance"] = ("Order, allocation, shipment and service records are SYNTHETIC_DEMO. Dealer is SOURCE_DERIVED. "
                        "Live HCME ERP/order data is NOT_CONNECTED.")
    sh = ev["shipment"] or {}
    fb = (f"Order {oid} is {ev['order']['status']} for {ev['order'].get('quantity')} × "
          f"{(ev['part'] or {}).get('part_name', ev['order'].get('partNumber'))}. "
          f"Shipment: {sh.get('status', 'not yet created')}. Receiving dealer: {(ev['dealer'] or {}).get('dealer_name', 'unknown')}. "
          "This is based on synthetic demo operational data.")
    return {"evidence": ev, "graph_path": ["Order", "Part", "Allocation", "Shipment", "ShipmentEvent", "DealerBranch", "ServiceJob"],
            "data": {"order_id": oid, "part_id": (ev["part"] or {}).get("part_id")}, "fallback": fb}


def _plain(v):
    """Neo4j temporal values -> ISO strings so the evidence is JSON-safe."""
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_plain(x) for x in v]
    if v is not None and not isinstance(v, (str, int, float, bool)):
        return str(v)
    return v


def h_unsupported(session, ext, ctx):
    ev = {"requested": ctx["query"],
          "status": "NOT_CONNECTED — HCME prices, lead times, live ERP stock and dealer pricing are not connected to this prototype.",
          "what_is_available": "catalogue parts, machine fitment, dealer network (source-derived); demo stock, suppliers, orders and shipments (synthetic)."}
    return {"evidence": ev, "graph_path": [], "data": {"part_id": ctx["part"]["part_id"] if ctx["part"] else None},
            "fallback": "That information is not available: live HCME pricing, lead-time and ERP data are not currently connected."}


def h_general(session, ext, ctx):
    cards = find_parts(session, ext.get("part_ref") or ctx["query"], ext.get("machine_ref"), limit=6)
    ev = {"general_question": ctx["query"],
          "related_hcme_parts": [{"part_id": c["part_id"], "name": c["part_name"], "category": c["category"]} for c in cards],
          "provenance": "Related parts: SOURCE_DERIVED HCME catalogue. Any general explanation is GENERAL KNOWLEDGE, not HCME data."}
    fb = ("General explanations need the language model, which is unavailable right now. "
          + (f"Related parts in the HCME Europe catalogue: {', '.join(c['part_id'] + ' ' + (c['part_name'] or '') for c in cards[:3])}."
             if cards else "No related part was found in the HCME Europe catalogue."))
    return {"evidence": ev, "graph_path": ["Part (related)"], "data": {"candidates": cards}, "fallback": fb, "general": True}


def h_supplier_lookup(session, ext, ctx):
    q = ctx["query"].lower()
    place, country = _place_and_country(ext)
    ref = (ext.get("supplier_ref") or "").strip() or None
    src = ("SOURCE_DERIVED — HCME SAP supplier master (20260609_Source data for Supplier.xlsx): "
           "supplier number, name, city and country only")
    if ext.get("dealer_name") or "same city" in q or "depot" in q:
        target = ext.get("dealer_name")
        res = co_located(session, dealer_name=target, city=None if target else (place or "Oosterhout"))
        if not res["city"]:
            return {"clarify": "Which dealer or city do you mean?", "evidence": {}, "graph_path": [], "data": {}}
        is_depot = bool(res.get("anchor_is_depot") or ("depot" in q) or (target and "depot" in target.lower()))
        rel_label = "SAME CITY AS DEPOT — DERIVED" if is_depot else "SAME CITY — DERIVED"
        ev = {"city": res["city"], "country": res["country"], "anchor_dealer": res["anchor_dealer"],
              "anchor_is_depot": is_depot,
              "depots": res["depots"], "suppliers_in_city": res["supplier_total"], "suppliers": res["suppliers"][:30],
              "dealers_in_city": [d["dealer_name"] for d in res["dealers"]],
              "relationship": rel_label, "provenance": src}
        if is_depot:
            depot_name = res["depots"][0] if res["depots"] else (res["anchor_dealer"] or "European Parts Centre")
            fb = (f"{res['supplier_total']} HCME supplier(s) are located in {res['city']} ({res['country']}), "
                  f"sharing the city with the {depot_name} depot. This is geographic colocation only "
                  f"({rel_label}); no commercial supply relationship is recorded.")
            graph_path = ["Depot", "City", "Supplier"]
        else:
            fb = (f"{res['supplier_total']} HCME supplier(s) are located in {res['city']} ({res['country']})"
                  f"{', the city of ' + res['anchor_dealer'] if res['anchor_dealer'] else ''} "
                  f"({rel_label}; geographic colocation only — no commercial supply relationship is recorded).")
            graph_path = ["DealerBranch", "City", "Supplier"]
        names = [x.get("name") for x in res["suppliers"][:5] if x.get("name")]
        if names:
            fb += " Suppliers: " + ", ".join(names).rstrip(".") + (" and others." if res["supplier_total"] > len(names) else ".")
        return {"evidence": ev, "graph_path": graph_path, "result_type": "NETWORK_RESULTS", "deterministic": True,
                "data": {"suppliers": res["suppliers"], "dealers": res["dealers"], "depots": res["depots"]}, "fallback": fb}
    number = ref if ref and ref.isdigit() else None
    name = ref if ref and not ref.isdigit() else None
    if not (number or name or place or country):
        return {"clarify": "Which supplier number, supplier name, city or country should I look up?",
                "evidence": {}, "graph_path": [], "data": {}}
    res = find_suppliers(session, number=number, name=name, city=place, country=country)
    ev = {"filter": {"number": number, "name": name, "city": place, "country": country}, "total": res["total"],
          "suppliers": res["suppliers"][:30], "provenance": src,
          "not_available": "The supplier master has no part numbers, so which parts a supplier supplies is not known."}
    where = number or name or place or country
    fb = (f"The HCME supplier master lists {res['total']} supplier(s) for {where}." if res["total"]
          else f"No supplier in the HCME supplier master matches {where}.")
    return {"evidence": ev, "graph_path": ["Supplier", "City", "Country"], "deterministic": True,
            "data": {"suppliers": res["suppliers"]}, "fallback": fb}



def h_machine_list(session, ext, ctx):
    """List machines, optionally filtered to a machine_type category."""
    from app.modules.intelligence.graph_query import machines_by_category, machines_by_type_all_categories
    machine_type = ext.get("machine_type")
    if machine_type:
        rows = machines_by_category(session, machine_type, limit=30)
        ev = {
            "machine_category": machine_type,
            "count": len(rows),
            "machines": [{"machine_id": r["machine_id"], "model": r["model"],
                          "operating_weight": r.get("operating_weight")} for r in rows],
            "data_class": "SOURCE_DERIVED",
            "provenance": "SOURCE_DERIVED — HCME Europe machine catalogue",
        }
        fb = (f"The HCME Europe catalogue lists {len(rows)} {machine_type} model(s): "
              f"{', '.join(r['model'] for r in rows[:10])}{'...' if len(rows) > 10 else ''}." if rows
              else f"No machines of type '{machine_type}' found in the HCME Europe catalogue.")
        return {"evidence": ev, "graph_path": ["Machine (by category)"],
                "data": {"machines": rows}, "fallback": fb}
    summary = machines_by_type_all_categories(session)
    total_machines = sum(v["count"] for v in summary.values())
    ev = {
        "total_machines": total_machines,
        "categories": [{"category": k, "count": v["count"], "examples": v["examples"]}
                       for k, v in summary.items()],
        "data_class": "SOURCE_DERIVED",
        "provenance": "SOURCE_DERIVED — HCME Europe machine catalogue",
    }
    fb = (f"The HCME Europe catalogue contains {total_machines} machines across "
          + "; ".join(f"{v['count']} {k} (e.g. {', '.join(v['examples'][:3])})" for k, v in summary.items()) + ".")
    return {"evidence": ev, "graph_path": ["Machine (all categories)"],
            "data": {"category_summary": summary}, "fallback": fb}


def h_machine_parts_by_category(session, ext, ctx):
    """Parts of a given category fitted to machines of a given type.

    Graph path: Machine -[:HAS_PART_FITMENT]-> Part  (SOURCE_DERIVED)
    """
    from app.modules.intelligence.graph_query import parts_by_category_across_machines
    machine_type = ext.get("machine_type")
    part_category = ext.get("part_category")
    if not machine_type:
        return {"clarify": "Which machine type do you mean? (e.g. medium excavator, wheel loader)",
                "evidence": {}, "graph_path": [], "data": {}}
    result = parts_by_category_across_machines(session, machine_type, part_category, limit=25)
    parts = result["parts"]
    ev = {
        "machine_type": machine_type, "part_category": part_category,
        "count": result["total"],
        "parts": [{"part_id": p["part_id"], "part_number": p["part_number"],
                   "part_name": p["part_name"], "part_subcategory": p["part_subcategory"],
                   "machine_count": p["machine_count"], "fitted_models": p["fitted_models"][:5]}
                  for p in parts],
        "data_class": "SOURCE_DERIVED",
        "relationship_path": result["relationship_path"],
        "note": result["note"],
    }
    cat_lbl = f"{part_category} " if part_category else ""
    if parts:
        fb = (f"Found {result['total']} {cat_lbl}part(s) fitted to {machine_type}(s) in the HCME Europe catalogue. "
              f"Top result: {parts[0]['part_id']} {parts[0]['part_name']}.")
    else:
        n_machines = session.run(
            "MATCH (m:Machine) WHERE toLower(m.machine_subcategory) = toLower($t) OR toLower(m.machine_category) = toLower($t) "
            "RETURN count(m) AS n", t=machine_type).single()["n"]
        n_parts = session.run(
            "MATCH (p:Part) WHERE $c IS NOT NULL AND (toLower(p.part_category) CONTAINS toLower($c) OR "
            "toLower(p.part_subcategory) CONTAINS toLower($c) OR toLower(p.part_name) CONTAINS toLower($c)) "
            "RETURN count(p) AS n", c=part_category).single()["n"] if part_category else None
        ev["machines_checked"] = n_machines
        ev["parts_in_category_catalogue_wide"] = n_parts
        if part_category and n_parts == 0:
            fb = (f"No {part_category} part is recorded anywhere in the HCME Europe catalogue, so none can fit the "
                  f"{n_machines} {machine_type} model(s) checked (Machine → HAS_PART_FITMENT → Part).")
        else:
            fb = (f"No {cat_lbl}part is recorded as fitting the {n_machines} {machine_type} model(s) in the HCME Europe "
                  f"catalogue (Machine → HAS_PART_FITMENT → Part).")
    candidates = []
    for p in parts[:6]:
        row = session.run("MATCH (p:Part {part_id: $id}) RETURN p", id=p["part_id"]).single()
        if row:
            candidates.append(_card_for(session, dict(row["p"])))
    machine_options = []
    if parts:
        machine_options = session.run(
            """MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part) WHERE p.part_id IN $pids
                 AND (toLower(m.machine_subcategory) = toLower($t) OR toLower(m.machine_category) = toLower($t))
               RETURN m.machine_id AS machine_id, m.model AS model, count(DISTINCT p) AS fitted_parts
               ORDER BY fitted_parts DESC, m.model LIMIT 16""",
            pids=[x["part_id"] for x in parts], t=machine_type).data()
    return {"evidence": ev, "graph_path": ["Machine", "Part (fitment + category filter)"],
            "data": {"parts": parts, "candidates": candidates, "machine_type": machine_type,
                     "part_category": part_category, "machine_options": machine_options}, "fallback": fb}


def h_machine_supplier_by_part_category(session, ext, ctx):
    """Suppliers for a part category fitted to a machine type.

    Pipeline (per Phase 10 Section 11):
      1. Parts in part_category fitted to machine_type (SOURCE_DERIVED)
      2. Check verified SUPPLIED_BY relationship (verified supplier-to-part)
      3. If no verified Supplier → Part relationship exists:
         State honestly: 'Supplier-to-part mapping is not recorded in the current HCME supplier source.'
         Do NOT return unrelated country suppliers or fallback to 1,131 suppliers.
    """
    from app.modules.intelligence.graph_query import (
        parts_by_category_across_machines, suppliers_by_part
    )
    machine_type = ext.get("machine_type")
    part_category = ext.get("part_category")
    country = ext.get("country")
    if not machine_type:
        return {"clarify": "Which machine type do you mean? (e.g. medium excavator, wheel loader)",
                "evidence": {}, "graph_path": [], "data": {}}
    if not part_category:
        return {"clarify": (f"Which part category are you looking for suppliers of, for {machine_type}s? "
                            "(e.g. bucket, filter, undercarriage)"),
                "evidence": {}, "graph_path": [], "data": {}}
    part_result = parts_by_category_across_machines(session, machine_type, part_category, limit=20)
    parts = part_result["parts"]
    verified_supplier_links = []
    for p in parts[:5]:
        sup_result = suppliers_by_part(session, p["part_id"], include_synthetic=False)
        if sup_result["suppliers"]:
            for s in sup_result["suppliers"]:
                s["_part_id"] = p["part_id"]
                s["_data_class"] = sup_result["data_class"]
            verified_supplier_links.extend(sup_result["suppliers"])
    ev = {
        "query_entities": {"machine_type": machine_type, "part_category": part_category, "country": country},
        "parts_found": {
            "count": part_result["total"], "data_class": "SOURCE_DERIVED",
            "relationship_path": "Machine -[:HAS_PART_FITMENT]-> Part",
            "parts": [{"part_id": p["part_id"], "part_name": p["part_name"],
                       "machine_count": p["machine_count"]} for p in parts[:10]],
        },
        "supplier_part_mapping": {
            "status": "CONNECTED" if verified_supplier_links else "NOT_CONNECTED",
            "data_class": "SOURCE_DERIVED" if verified_supplier_links else "NOT_CONNECTED",
            "count": len(verified_supplier_links),
            "suppliers": verified_supplier_links[:10],
            "critical_note": (
                "Verified supplier-to-part records."
                if verified_supplier_links else
                "Supplier-to-part mapping is not recorded in the current HCME supplier source. "
                "The HCME SAP supplier master (1,720 records) contains supplier location data only — "
                "it has NO part numbers or supplier-part assignments."
            ),
        },
    }
    if verified_supplier_links:
        fb = (f"The HCME Europe catalogue lists {part_result['total']} {part_category} part(s) fitted to "
              f"{machine_type}(s). Found {len(verified_supplier_links)} verified supplier(s).")
        graph_path = ["Machine", "Part (fitment)", "Supplier (verified)"]
    else:
        fb = (f"The HCME Europe catalogue lists {part_result['total']} {part_category} part(s) fitted to "
              f"{machine_type}(s). However, supplier-to-part mapping is not recorded in the current HCME supplier source. "
              "Authoritative supplier sourcing relationships cannot be shown.") if parts else (
              f"No {part_category} parts are recorded in the HCME Europe catalogue for {machine_type}, "
              "and supplier-to-part mapping is not recorded in the current HCME supplier source.")
        graph_path = ["Machine", "Part (fitment)", "Supplier → Part (NOT_CONNECTED)"]
    return {
        "evidence": ev,
        "graph_path": graph_path,
        "data": {"parts": parts, "suppliers": verified_supplier_links,
                 "machine_type": machine_type, "part_category": part_category},
        "fallback": fb,
    }


def h_dealer_supplier_network(session, ext, ctx):
    """Dealer + supplier network for a country or city (SOURCE_DERIVED both)."""
    from app.modules.intelligence.graph_query import network_summary_by_country
    place, country = _place_and_country(ext)
    target_country = country or ("NL" if not place else None)
    if not target_country and not place:
        target_country = "NL"
    if not place and not country and re.search(r"\bcit(?:y|ies)\b", ctx["query"].lower()):
        rows = session.run(
            """MATCH (d:DealerBranch)-[:LOCATED_IN]->(c:City)<-[:LOCATED_IN]-(s:Supplier)
               WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
               RETURN c.name AS city, c.country AS country, count(DISTINCT d) AS dealers, count(DISTINCT s) AS suppliers
               ORDER BY suppliers DESC, dealers DESC LIMIT 15""").data()
        total = session.run(
            """MATCH (d:DealerBranch)-[:LOCATED_IN]->(c:City)<-[:LOCATED_IN]-(s:Supplier)
               WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' RETURN count(DISTINCT c) AS n""").single()["n"]
        ev = {"cities_with_both": rows, "total_cities": total, "relationship": "SAME CITY — DERIVED",
              "provenance": "SOURCE_DERIVED — dealer locator (SRC-049) and SAP supplier master; colocation only."}
        fb = (f"{total} cities hold both a Hitachi dealer branch and HCME SAP suppliers (SAME CITY — DERIVED; geographic "
              "colocation only). Most suppliers: " + ", ".join(f"{r['city']} ({r['country']}: {r['dealers']} dealer(s), {r['suppliers']} supplier(s))" for r in rows[:5]) + ".")
        return {"evidence": ev, "graph_path": ["DealerBranch", "City", "Supplier"], "result_type": "NETWORK_RESULTS",
                "data": {"cities_with_both": rows}, "fallback": fb}
    if place and not country:
        res = co_located(session, city=place)
        if not res["city"]:
            return {"clarify": f"I couldn't find city '{place}'. Please give another city name.",
                    "evidence": {}, "graph_path": [], "data": {}}
        ev = {
            "city": res["city"], "country": res["country"],
            "dealer_count": len(res["dealers"]), "supplier_count": res["supplier_total"],
            "dealers": [_dealer_brief(d) for d in res["dealers"]],
            "suppliers": res["suppliers"][:20], "depots": res["depots"],
            "data_class": "SOURCE_DERIVED",
            "relationship_path": "DealerBranch / Supplier -[:LOCATED_IN]-> City",
            "relationship": "SAME CITY — DERIVED",
            "note": "Colocation is geographic only (SAME CITY — DERIVED) — no commercial relationship implied.",
        }
        fb = (f"In {res['city']} ({res['country']}): {len(res['dealers'])} Hitachi dealer branch(es) "
              f"and {res['supplier_total']} HCME SAP supplier(s) are registered (SAME CITY — DERIVED).")
        return {"evidence": ev, "graph_path": ["City", "DealerBranch", "Supplier"],
                "data": {"dealers": res["dealers"], "suppliers": res["suppliers"]}, "fallback": fb}
    summary = network_summary_by_country(session, target_country)
    ev = {
        "country": target_country,
        "dealer_count": summary["dealer_count"], "supplier_count": summary["supplier_count"],
        "shared_cities": summary["shared_cities"],
        "dealer_data_class": "SOURCE_DERIVED", "supplier_data_class": "SOURCE_DERIVED",
        "note": summary["note"],
        "relationship": "SAME CITY — DERIVED",
        "relationship_path": "DealerBranch/Supplier -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country",
    }
    fb = (f"In {target_country}: {summary['dealer_count']} Hitachi dealer branch(es) and "
          f"{summary['supplier_count']} HCME SAP supplier(s). "
          f"They share {len(summary['shared_cities'])} city/cities (SAME CITY — DERIVED; "
          "geographic colocation only — no commercial relationship implied).")
    return {"evidence": ev, "graph_path": ["Country", "City", "DealerBranch", "Supplier"],
            "data": {"shared_cities": summary["shared_cities"]}, "fallback": fb}


HANDLERS: Dict[str, Callable] = {
    "machine_info": h_machine_info,
    "supplier_summary": h_supplier_summary,
    "dealer_lookup": h_dealer_lookup,
    "supplier_lookup": h_supplier_lookup,
    "general_question": h_general,
    "part_search": h_part_search, "part_info": h_part_info, "impact_analysis": h_impact,
    "machine_parts": h_machine_parts, "compliance_analysis": h_compliance, "supplier_risk": h_supplier_risk,
    "mitigation_analysis": h_mitigation, "alternatives": h_alternatives, "supply_chain": h_supply_chain,
    "fulfilment_options": h_fulfilment, "part_dealers": h_part_dealers, "dealer_list": h_dealer_list,
    "nearest_dealer": h_nearest, "dealer_contact": h_dealer_contact, "order_status": h_order,
    "shipment_status": h_order, "service_status": h_order, "unsupported": h_unsupported,
    # Phase 10C new intents
    "machine_list": h_machine_list,
    "machine_parts_by_category": h_machine_parts_by_category,
    "machine_supplier_by_part_category": h_machine_supplier_by_part_category,
    "dealer_supplier_network": h_dealer_supplier_network,
    "rfq_search": h_rfq,
    "disruption": h_disruption,
}



# ---------------------------------------------------------------------------
# 4. Answer
# ---------------------------------------------------------------------------

def _answer(provider, query: str, intent: str, result: Dict[str, Any]) -> tuple[str, str]:
    if result.get("clarify"):
        return result["clarify"], "clarification"
    if intent == "part_search" or result.get("deterministic"):
        return result["fallback"], "deterministic"  # the result cards / a plain "not available" are the answer
    if isinstance(provider, GeminiLLMProvider):
        try:
            if result.get("general"):
                user = f"Question: {query}\nRelated HCME catalogue parts (JSON):\n{json.dumps(result['evidence'], default=str)}"
                return provider._generate(_GENERAL_SYSTEM, user, timeout=4.5).strip(), "gemini"
            user = f"Question: {query}\nIntent: {intent}\nEvidence (JSON):\n{json.dumps(result['evidence'], default=str)[:14000]}"
            return provider._generate(_ANSWER_SYSTEM, user, timeout=4.5).strip(), "gemini"
        except Exception as e:
            logger.warning(f"Parts Intelligence answer generation degraded to deterministic: {e}")
    return result["fallback"], "deterministic"


def route_and_answer_query(session, query_text: str, context_part_id: Optional[str] = None, limit: int = 9,
                           follow_up_to: Optional[str] = None) -> Dict[str, Any]:
    started = time.perf_counter()
    provider = get_llm_provider()
    query = query_text.strip()
    if follow_up_to:
        # The user is replying to a clarifying question: read the reply as the
        # missing piece of the original question ("dealers near me" + "Eindhoven").
        query = f"{follow_up_to.strip().rstrip('?')} in {query}"

    ext = _extract(provider, query)
    # Entity-priority rules (intent_resolution.py): a recognised Part / dealer is never replaced by a
    # broader entity. The query is self-contained; nothing from earlier turns is consulted.
    catalog = catalog_lookup(session, query)
    if catalog and catalog["intent"] in HANDLERS:
        ext.update(catalog["entities"])
        ext["intent"] = catalog["intent"]
        if catalog["entities"].get("dealer_id"):
            ext["refers_dealer"] = True
    ext = apply_entity_precedence(session, ext, query)
    if catalog and catalog["intent"] in HANDLERS:
        ext["intent"] = catalog["intent"]  # the catalogue outranks looser precedence rules
    t_extract = time.perf_counter()

    # Only an EXPLICIT back-reference ("this part", "the same part") may use the UI's context part.
    explicit_ref = refers_to_context(query)
    part = _resolve_part(session, ext, query, context_part_id if explicit_ref else None)
    intent = ext["intent"]
    # A part-specific question whose part could not be resolved becomes a search.
    if intent == "part_info" and not part and ext.get("part_ref"):
        intent = "part_search"
    if intent == "impact_analysis" and not part and not ext.get("part_ref"):
        intent = "machine_list" if ext.get("machine_type") else intent
    ctx = {"query": query, "part": part, "limit": limit}
    if explicit_ref and not part and not ext.get("part_ref") and intent in ("part_search", "part_info"):
        result = _need_part("answer")  # "this part" with nothing to refer to: ask, never guess
    else:
        result = HANDLERS.get(intent, h_part_search)(session, ext, ctx)
    t_graph = time.perf_counter()

    answer, answer_source = _answer(provider, query, intent, result)
    done = time.perf_counter()

    data = result.setdefault("data", {})
    _PART_INTENTS = {
        "part_search", "part_info", "compliance_analysis", "supplier_risk",
        "mitigation_analysis", "alternatives", "supply_chain", "fulfilment_options",
        "part_dealers",
    }
    if part and not data.get("candidates") and not result.get("clarify") and intent in _PART_INTENTS:
        data["candidates"] = [_card_for(session, part)]
    target = data.get("part_id") or data.get("order_id")
    from app.modules.intelligence.graph_view import build_graph_view
    graph = build_graph_view(intent, ext, result)
    rtype = result_type_for(intent, result)
    # Graph Insights are offered only when this response is itself about one Part.
    insights_part = part["part_id"] if (part and intent in PART_SCOPED_RESULT_INTENTS) else None
    return {
        "intent": intent,
        "result_type": rtype,
        "structured_intent": ext.get("structured_intent"),
        "insights_part_id": insights_part,
        "catalog_question_id": catalog["question_id"] if catalog else None,
        "entities": {k: ext.get(k) for k in (
            "part_ref", "machine_ref", "machine_type", "part_category",
            "requested_entity", "order_ref", "shipment_ref", "dealer_name", "country", "place",
        )},
        "resolved_part_id": part["part_id"] if part else None,
        "target_entity": target,
        "graph_path": result.get("graph_path", []),
        "graph": graph,
        "evidence": result.get("evidence", {}),
        "needs_clarification": bool(result.get("clarify")),
        "answer": answer,
        "explanation": answer,
        "data": result.get("data", {}),
        "pipeline": {
            "extraction": ext.get("source"), "answer": answer_source,
            "timings_ms": {"understand": round((t_extract - started) * 1000), "graph": round((t_graph - t_extract) * 1000),
                           "explain": round((done - t_graph) * 1000), "total": round((done - started) * 1000)},
        },
    }
