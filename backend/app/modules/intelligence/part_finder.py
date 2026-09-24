"""
backend/app/modules/intelligence/part_finder.py

Phase 10 part matching for the Parts Intelligence result cards.

One graph query loads the catalogue (60 parts) with fitment counts; matching
and scoring run in Python, so a search costs one round trip instead of one per
candidate. The match percentage is deterministic: how many of the request's
terms the part covers, and in how strong a field (name / sub-category >
category / assembly > description). An exact part number or part ID is 100%.
"""

import re
from typing import Any, Dict, List, Optional

_STOP = {
    "a", "an", "the", "for", "i", "need", "needs", "find", "show", "me", "part", "parts", "which", "what",
    "is", "are", "my", "of", "to", "with", "on", "in", "fit", "fits", "fitting", "compatible", "hitachi",
    "please", "do", "you", "have", "any", "can", "get", "there", "that", "this", "and", "or", "we", "our",
    "machine", "machines", "model", "genuine", "looking", "want", "replacement", "new", "used", "use", "by",
    "why", "does", "how", "often", "it", "its", "wear", "work", "works", "change", "about", "tell", "explain",
    "when", "should", "be", "much", "many", "who", "where", "all", "some", "type", "kind", "good", "best",
    # conversational filler around the real request ("the old one's clogged and the customer's waiting")
    "old", "one", "ones", "clogged", "blocked", "broken", "worn", "dirty", "damaged", "faulty", "failed", "leaking", "customer", "customers",
    "waiting", "wait", "urgent", "urgently", "asap", "quickly", "quick", "now", "today", "soon", "but", "so", "then", "still", "just", "really",
    "very", "would", "could", "like", "if", "because", "since", "as", "at", "from", "into", "them", "they", "he", "she", "his", "her", "was",
    "were", "has", "had", "got", "am", "im", "ive", "thanks", "thank", "hi", "hello", "hey", "sorry", "help",
    "won", "lose", "losing", "lost", "flat", "dead", "order", "ordering", "buy", "usually", "else", "also", "down", "stopped", "start", "starts",
    "starting", "options", "option", "available", "stock", "supply", "supplies", "fits", "fitted", "models", "which", "own", "their", "theirs",
}
_FIELD_WEIGHTS = [("part_name", 3), ("part_subcategory", 3), ("part_category", 2), ("component_assembly", 2), ("description", 1)]

_CATALOGUE_Q = """
MATCH (p:Part)
RETURN p AS part,
       [(m:Machine)-[:HAS_PART_FITMENT]->(p) | m.model] AS models
"""


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9][a-z0-9\-]*", (text or "").lower())
    return [_stem(w) for w in words if w not in _STOP and len(w) > 1]


def _hit(term: str, words: set) -> bool:
    """Exact word match, or a close misspelling of one ("hydralic" ~ "hydraulic")."""
    if term in words:
        return True
    if len(term) < 5:
        return False
    from difflib import get_close_matches
    return bool(get_close_matches(term, words, n=1, cutoff=0.8))


def assessment(pct: int) -> str:
    if pct >= 100:
        return "Exact match."
    if pct >= 90:
        return "Very strong match."
    if pct >= 75:
        return "Strong match."
    if pct >= 60:
        return "Good match with minor trade-offs."
    return "Partial match — review the details."


def to_card(part: Dict[str, Any], fits_count: int, pct: int, machine: Optional[str] = None) -> Dict[str, Any]:
    note = assessment(pct)
    if machine:
        note += f" Fits {machine}."
    return {
        "part_id": part["part_id"],
        "part_number": part.get("part_number"),
        "part_name": part.get("part_name"),
        "description": part.get("description"),
        "match_pct": pct,
        "category": part.get("part_category"),
        "subcategory": part.get("part_subcategory"),
        "assembly": part.get("component_assembly"),
        "fits_count": fits_count,
        "assessment": note,
        "specs": {
            "genuine_hitachi_part": part.get("genuine_hitachi_part"),
            "wear_part": part.get("wear_part"),
            "service_part": part.get("service_part"),
            "consumable": part.get("consumable"),
            "record_class": part.get("record_class"),
            "confidence": part.get("confidence"),
            "source_id": part.get("source_id"),
            "source_date": str(part.get("source_date")) if part.get("source_date") else None,
        },
    }


def find_parts(session, text: str, machine: Optional[str] = None, limit: int = 9) -> List[Dict[str, Any]]:
    rows = session.run(_CATALOGUE_Q).data()
    machine_l = (machine or "").lower()
    terms = [t for t in _tokens(text) if not machine_l or t not in _tokens(machine_l)]
    # Words that appear nowhere in the catalogue ("clogged", "waiting" and other talk around the request) must not dilute the match.
    vocab = {w for r in rows for f, _ in _FIELD_WEIGHTS for w in _tokens(str(dict(r["part"]).get(f) or ""))}
    known = [t for t in terms if _hit(t, vocab)]
    dropped = [t for t in terms if t not in known and len(t) >= 5]   # long unknown words are reported (e.g. "bucket" when there is none)
    if known:
        terms = known
    raw = (text or "").strip().lower()

    cards = []
    for r in rows:
        part = dict(r["part"])
        models = r["models"]
        unmatched: List[str] = []
        if machine_l and not any(machine_l in (m or "").lower() for m in models):
            continue

        if raw and raw in {str(part.get("part_number") or "").lower(), part["part_id"].lower()}:
            pct = 100
        elif any(t in {str(part.get("part_number") or "").lower(), part["part_id"].lower()} for t in terms):
            pct = 100
        elif terms:
            fields = {f: set(_tokens(str(part.get(f) or ""))) for f, _ in _FIELD_WEIGHTS}
            best = [max((w for f, w in _FIELD_WEIGHTS if _hit(t, fields[f])), default=0) for t in terms]
            matched = sum(1 for b in best if b)
            if not matched:
                continue
            unmatched = [t for t, b in zip(terms, best) if not b] + dropped
            strong = sum(1 for b in best if b >= 2)
            pct = round(100 * (0.7 * matched / len(terms) + 0.3 * sum(best) / (3 * len(terms))))
            if not strong:
                pct = min(pct, 45)  # a passing mention in a description is not a match on the part itself
        elif machine_l:
            pct = 90  # no part terms: every part fitted to the requested machine
        else:
            continue
        card = to_card(part, len(models), pct, machine)
        if unmatched and pct < 100:
            card["unmatched_terms"] = unmatched
            card["assessment"] += f" Nothing in this part matches: {', '.join(unmatched)}."
        cards.append(card)

    cards.sort(key=lambda c: (-c["match_pct"], -c["fits_count"], c["part_id"]))
    return [c for c in cards if c["match_pct"] >= 50][:limit]
