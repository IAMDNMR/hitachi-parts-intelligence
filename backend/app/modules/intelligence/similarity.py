"""
Semantic / hybrid part search, similar parts and RFQ matching (Phase 11).

Ranking blends four explainable signals - never a single opaque score:
  semantic   cosine of the local embedding (embeddings.py) of the request vs the part document
  lexical    share of request words found in the part document
  spec       requested electrical specs (voltage, current) vs the part's tech_* fields, where the real part name states them
  exact      part number / part id match (always 100%)
Technical attributes exist only where the data has them: SOURCE_DERIVED from a real part name, or SYNTHETIC_DEMO
(labelled by `tech_attrs_source`). A requested attribute a part has no data for is reported as *missing*, never
assumed to match. Quantity/deadline are checked against demo stock only; lead time is not in the data and is
reported as such.
"""
import re
from datetime import date
from typing import Any, Dict, List, Optional

from app.modules.intelligence import embeddings
from app.modules.intelligence import interchangeability as ic

DIMS = embeddings.DIMS
INDEX_NAME = "part_spec_embedding_index"
MIN_RELEVANCE = 0.30  # below this a match is noise and is not shown (HCME's standard search stays the primary search)
RELATIVE_FLOOR = 0.70  # ...and neither is anything scoring under 70% of the best match: weak results are not shown next to a strong one

# Only electrical values that HCME part names actually state (e.g. "24V", "24V/100A"). No invented attributes.
TECH_KEYS = ("voltage_v", "current_a")


# --------------------------------------------------------------------------- documents & storage

def tech_of(p: Dict[str, Any]) -> Dict[str, Any]:
    return {k: p[f"tech_{k}"] for k in TECH_KEYS if p.get(f"tech_{k}") is not None}


def tech_text(p: Dict[str, Any]) -> str:
    t, bits = tech_of(p), []
    if "voltage_v" in t: bits.append(f"{t['voltage_v']:g}V")
    if "current_a" in t: bits.append(f"{t['current_a']:g}A")
    return " ".join(bits)


def part_document(p: Dict[str, Any]) -> str:
    return " ".join(str(p.get(k) or "") for k in
                    ("part_number", "part_name", "part_category", "part_subcategory", "component_assembly",
                     "description")) + " " + tech_text(p)


def _load_parts(session) -> List[Dict[str, Any]]:
    rows = session.run(
        """MATCH (p:Part) WHERE p.testRunId IS NULL AND p.part_id STARTS WITH 'PT-'
           CALL { WITH p OPTIONAL MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p)
                  RETURN collect(m.machine_id) AS machines, collect(DISTINCT m.model) AS models }
           CALL { WITH p OPTIONAL MATCH (p)-[:HAS_SYNTHETIC_INVENTORY]->(i:InventorySnapshot)
                  RETURN sum(i.quantity) AS stock, count(i) AS snaps }
           CALL { WITH p OPTIONAL MATCH (p)-[l:SUPPLIED_BY]->(s:Supplier)
                  RETURN count(s) AS suppliers, collect(l.role) AS roles }
           RETURN p, machines, models, CASE WHEN snaps = 0 THEN null ELSE stock END AS stock, suppliers, roles""").data()
    out = []
    for r in rows:
        p = dict(r["p"])
        p["_machines"] = set(r["machines"])
        p["_models"] = [x for x in r["models"] if x]
        p["_stock"] = r["stock"]
        p["_suppliers"] = r["suppliers"]
        p["_roles"] = [x for x in r["roles"] if x]
        out.append(p)
    return out


def write_embeddings(session) -> int:
    n = 0
    for p in _load_parts(session):
        vec = embeddings.embed(part_document(p))
        if vec is None:
            continue
        session.run("MATCH (p:Part {part_id:$id}) SET p.embedding=$e, p.embedding_model='local-hash-256'",
                    id=p["part_id"], e=vec).consume()
        n += 1
    session.run(f"""CREATE VECTOR INDEX {INDEX_NAME} IF NOT EXISTS FOR (p:Part) ON (p.embedding)
                    OPTIONS {{indexConfig: {{`vector.dimensions`: {DIMS}, `vector.similarity_function`: 'cosine'}}}}""").consume()
    return n


def _vec(p: Dict[str, Any]) -> List[float]:
    e = p.get("embedding")
    if e and len(e) == DIMS:
        return list(e)
    return embeddings.embed(part_document(p)) or [0.0] * DIMS


# --------------------------------------------------------------------------- request parsing

_NUM = r"(\d+(?:\.\d+)?)"


def parse_specs(text: str) -> Dict[str, Any]:
    """Requested electrical specs. Only what the text actually states."""
    s: Dict[str, Any] = {}
    if m := re.search(_NUM + r"\s*v(?:dc)?\b", text, re.I): s["voltage_v"] = float(m.group(1))
    if m := re.search(_NUM + r"\s*a(?:mps?)?\b", text, re.I): s["current_a"] = float(m.group(1))
    return s


def _fmt(k: str, v: Any) -> str:
    return {"voltage_v": f"{v:g}V", "current_a": f"{v:g}A"}.get(k, str(v))


def match_specs(req: Dict[str, Any], part: Dict[str, Any]) -> Dict[str, Any]:
    """matched / mismatched / missing for every requested attribute + 0..1 score (None if nothing requested)."""
    have = tech_of(part)
    matched, mismatched, missing = [], [], []
    for k, want in req.items():
        got = have.get(k)
        if got is None:
            missing.append(_fmt(k, want))
        elif k == "voltage_v":
            (matched if got == want else mismatched).append(_fmt(k, want) if got == want else f"{_fmt(k, want)} requested, part has {_fmt(k, got)}")
        elif k == "current_a":
            (matched if got >= want else mismatched).append(f"{want:g}A+" if got >= want else f"needs {want:g}A, part {got:g}A")
    n = len(req)
    return {"matched": matched, "mismatched": mismatched, "missing": missing,
            "score": None if not n else (len(matched) + 0.25 * len(missing)) / n}


def parse_rfq(text: str) -> Dict[str, Any]:
    """quantity / deadline / specs / machine / constraints from an RFQ-like sentence (rule-based, no LLM)."""
    out: Dict[str, Any] = {"specs": parse_specs(text)}
    if m := re.search(r"(?:need|require|want|quote for|rfq for|order)?\s*(\d[\d,]*)\s*(?:x|units?|pcs|pieces|off)\b", text, re.I) \
            or re.search(r"\b(?:need|require|want)\s+(\d[\d,]*)\b(?!\s*[vV]\b)", text, re.I):
        out["quantity"] = int(m.group(1).replace(",", ""))
    if m := re.search(r"within\s+(\d+)\s*(day|week|month)s?", text, re.I):
        out["deadline_days"] = int(m.group(1)) * {"day": 1, "week": 7, "month": 30}[m.group(2).lower()]
    elif m := re.search(r"\bby\s+(\d{4}-\d{2}-\d{2})", text):
        out["deadline_days"] = max((date.fromisoformat(m.group(1)) - date.today()).days, 0)
    constraints = []
    if re.search(r"stage\s*v|nrmm", text, re.I): constraints.append("EU Stage V / NRMM emissions")
    if re.search(r"\breach\b", text, re.I): constraints.append("REACH")
    if re.search(r"\bce\b|emc", text, re.I): constraints.append("CE / EMC")
    out["constraints"] = constraints
    if m := re.search(r"\bfor\s+(?:the\s+)?([a-z][a-z ]{3,40}?)(?:,|\.|\bwith\b|\bIP\d|\d+\s*v\b|$)", text, re.I):
        out["application"] = m.group(1).strip()
    return out


# --------------------------------------------------------------------------- ranking

def _lexical(query: str, doc: str) -> float:
    q = {w for w in embeddings.tokens(query) if len(w) > 2 and not re.fullmatch(r"(v|a)\d+(\.\d+)?", w)}
    d = set(embeddings.tokens(doc))
    return len(q & d) / len(q) if q else 0.0


def _kind(p):
    return p.get("part_subcategory") or p.get("part_category")


def _card(p, score, factors, reasons, extra=None):
    d = {"part_id": p["part_id"], "part_number": p.get("part_number"), "part_name": p.get("part_name"),
         "category": p.get("part_category"), "subcategory": p.get("part_subcategory"),
         "similarity": round(score, 3), "similarity_pct": round(max(min(score, 1.0), 0) * 100),
         "factors": factors, "reasons": reasons, "tech_attributes": tech_of(p),
         "tech_attrs_source": p.get("tech_attrs_source"), "synthetic": bool(p.get("synthetic"))}
    d.update(extra or {})
    return d


def _correct_typos(text: str, parts: List[Dict[str, Any]]) -> str:
    """Fix near-miss words against the catalogue vocabulary ('hydralic pmp' -> 'hydraulic pump'); same first letter only."""
    from difflib import get_close_matches
    vocab = {w for p in parts for w in embeddings.tokens(part_document(p)) if len(w) >= 3 and not w.isdigit()}
    out = []
    for w in text.split():
        core = re.sub(r"[^a-z]", "", w.lower())
        if len(core) >= 3 and core not in vocab and core not in embeddings._STOP:
            cutoff = 0.75 if len(core) >= 4 else 0.85  # short words need a closer match
            hit = [h for h in get_close_matches(core, vocab, n=3, cutoff=cutoff) if h[0] == core[0] and (len(core) >= 4 or h[-1] == core[-1])][:1]
            if hit:
                w = w.lower().replace(core, hit[0])
        out.append(w)
    return " ".join(out)


def hybrid_search(session, text: str, limit: int = 8, parts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Exact part number/id -> 100%; otherwise semantic + lexical + spec blend, ranked with match factors."""
    parts = parts if parts is not None else _load_parts(session)
    text = _correct_typos(text, parts)
    specs = parse_specs(text)
    qv = embeddings.embed(text)
    ids = {m.upper() for m in re.findall(r"\bPT-\d{3}\b", text, re.I)}
    numbers = set(re.findall(r"\b[A-Z0-9]{2}\d{5,}[A-Z0-9-]*\b|\b\d{7,8}\b", text.upper()))
    ranked = []
    for p in parts:
        doc = part_document(p)
        exact = p["part_id"] in ids or (p.get("part_number") and str(p["part_number"]).upper() in numbers)
        sem = max(embeddings.cosine(qv, _vec(p)), 0.0) if qv else 0.0
        lex = _lexical(text, doc)
        sm = match_specs(specs, p) if specs else None
        if exact:
            score, reasons = 1.0, ["Exact part number / part id match."]
        else:
            if sm and sm["score"] is not None:
                score = 0.4 * sem + 0.25 * lex + 0.35 * sm["score"]
            else:
                score = 0.6 * sem + 0.4 * lex
            reasons = [f"Semantic similarity {round(sem * 100)}%, keyword overlap {round(lex * 100)}%."]
        if sm:
            if sm["matched"]: reasons.append("Matches: " + ", ".join(sm["matched"]) + ".")
            if sm["mismatched"]: reasons.append("Does not match: " + "; ".join(sm["mismatched"]) + ".")
            if sm["missing"]: reasons.append("No data for: " + ", ".join(sm["missing"]) + ".")
        ranked.append((score, p, {"semantic": round(sem, 3), "keyword": round(lex, 3),
                                  "spec": None if not sm or sm["score"] is None else round(sm["score"], 3),
                                  "exact": bool(exact)}, reasons, sm))
    ranked.sort(key=lambda x: (-x[0], x[1]["part_id"]))
    cut = max(MIN_RELEVANCE, RELATIVE_FLOOR * (ranked[0][0] if ranked else 0))
    shown = [x for x in ranked[:limit] if x[0] >= cut]
    cards = [_card(p, sc, f, r, {"spec_match": sm}) for sc, p, f, r, sm in shown]
    return {"query": text, "requested_specs": specs, "results": cards, "min_relevance_pct": round(MIN_RELEVANCE * 100),
            "weak_matches_hidden": sum(1 for x in ranked[:limit] if x[0] < cut),
            "method": "supporting search for typos, electrical specs and RFQ sentences (the standard HCME search stays primary): local hashed-text "
                      "embedding + keyword overlap + electrical-spec match; exact part numbers = 100%; matches below the relevance floor are not shown"}


def semantic_search(session, text: str, limit: int = 8) -> Dict[str, Any]:
    """Embedding-only ranking (no keyword/spec blending)."""
    parts = _load_parts(session)
    qv = embeddings.embed(text)
    ranked = sorted(((max(embeddings.cosine(qv, _vec(p)), 0.0), p) for p in parts), key=lambda x: (-x[0], x[1]["part_id"]))
    return {"query": text, "min_relevance_pct": round(MIN_RELEVANCE * 100),
            "results": [_card(p, s, {"semantic": round(s, 3)}, [f"Semantic similarity {round(s * 100)}%."])
                        for s, p in ranked[:limit] if s >= max(MIN_RELEVANCE, RELATIVE_FLOOR * ranked[0][0])],
            "method": "local hashed-text embedding (cosine)"}


def similar_parts(session, part_id: str, limit: int = 5, loaded: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Candidates for engineering review. Hard filters (orderable part, same specific type, shared machine fitment) decide who is
    shown; text similarity only orders candidates that already passed them. Nothing here is an approved replacement."""
    parts = {p["part_id"]: p for p in (loaded if loaded is not None else _load_parts(session))}
    target = parts.get(part_id)
    if not target:
        return {"found": False, "part_id": part_id, "alternatives": [], "rejected": []}
    base = {"found": True, "part_id": part_id, "part_name": target.get("part_name"), "label": ic.CANDIDATE_LABEL,
            "authoritative_data": "none loaded (no HCME supersession / interchangeability relationships exist yet)"}
    if ic.is_family(target):
        return {**base, "alternatives": [], "rejected": [],
                "note": f"{part_id} is a product-line family record, not an orderable part; no substitute is assessed for it.",
                "method": "hard filters"}
    tv = _vec(target)
    auth = ic.authoritative_map(session, part_id)  # empty until HCME supersession / compatibility data is loaded
    ranked, rejected = [], []
    for pid, p in parts.items():
        if pid == part_id or ic.is_family(p):
            continue
        cos = max(embeddings.cosine(tv, _vec(p)), 0.0)
        kind = auth.get(pid)
        if kind == "NOT_COMPATIBLE_WITH":
            continue
        ok, why = ic.gate(target, p, target["_machines"], p["_machines"])
        if not ok:
            if cos >= 0.62 and "type" in why:
                rejected.append(_card(p, cos, {"text_similarity": round(cos, 3)}, [f"Not a candidate: {why}. Text similarity alone is not evidence of interchangeability."]))
            elif "type" not in why and ic.type_key(p) == ic.type_key(target):
                rejected.append(_card(p, cos, {"text_similarity": round(cos, 3)}, [f"Not a candidate: {why}."]))
            continue
        union = target["_machines"] | p["_machines"]
        shared = len(target["_machines"] & p["_machines"])
        cover = shared / len(target["_machines"])
        reasons = [f"Same part type ({ic.type_key(p)}) - hard filter passed.",
                   f"Shares {shared} of the {len(target['_machines'])} machine models {part_id} is fitted to ({round(cover * 100)}%).",
                   f"Text similarity {round(cos * 100)}% (supporting signal only)."]
        ranked.append(_card(p, cos, {"machine_coverage": round(cover, 3), "text_similarity": round(cos, 3)}, reasons,
                            {"status": ("Authoritative HCME relationship: " + kind) if kind in ("SUPERSEDES", "COMPATIBLE_WITH") else ic.CANDIDATE_LABEL, "machine_coverage_pct": round(cover * 100), "shared_machines": shared,
                             "similarity_role": "supporting signal, not proof of interchangeability", "union_machines": len(union)}))
    ranked.sort(key=lambda c: (-c["machine_coverage_pct"], -c["similarity"], c["part_id"]))
    rejected.sort(key=lambda c: -c["similarity"])
    return {**base, "alternatives": ranked[:limit], "rejected": rejected[:3],
            "method": "hard filters (orderable part, same specific part type, shared machine fitment) decide who is shown; candidates are ordered by "
                      "machine-fitment coverage, then text similarity. Candidates for engineering review, not approved replacements."}


def commercial_status(part: Dict[str, Any], quantity: Optional[int], deadline_days: Optional[int]) -> Dict[str, Any]:
    """Integration point for REAL stock / price / lead time. Nothing is connected today, so each is NOT_CONNECTED and the requested
    quantity is never compared with the synthetic demo stock. When a real feed exists, fill these three from it."""
    nc = "NOT_CONNECTED"
    return {
        "availability": {"status": nc, "requested_quantity": quantity, "note": "No real stock feed is connected."},
        "price": {"status": nc, "note": "No price data exists."},
        "lead_time": {"status": nc, "requested_deadline_days": deadline_days,
                      "note": "No lead-time data exists; the deadline cannot be verified."},
    }


def rfq_search(session, text: str, limit: int = 5) -> Dict[str, Any]:
    """RFQ-like request -> ranked parts with spec match, quantity/deadline check, risks and the reason for selection."""
    parts = _load_parts(session)
    rfq = parse_rfq(text)
    models = {m.upper(): m for p in parts for m in p["_models"]}
    machine = next((orig for up, orig in sorted(models.items(), key=lambda kv: -len(kv[0])) if up in text.upper()), None)
    core = re.sub(r"\b(need|required|require|units?|pcs|within|weeks?|days?|months?|quote|rfq)\b|\d+\s*(?:units?|pcs)", " ", text, flags=re.I)
    base = hybrid_search(session, core, limit=limit, parts=parts)
    qty, dl = rfq.get("quantity"), rfq.get("deadline_days")
    by_id = {p["part_id"]: p for p in parts}
    for c in base["results"]:
        p = by_id[c["part_id"]]
        risks = []
        if p["_suppliers"] == 0: risks.append("No supplier recorded for this part.")
        elif "SOLE" in p["_roles"]: risks.append("Sole-sourced (demo supplier link).")
        sm = c.get("spec_match") or {}
        if sm.get("mismatched"): risks.append("Specification mismatch: " + "; ".join(sm["mismatched"]) + ".")
        if sm.get("missing"): risks.append("Specification not in data: " + ", ".join(sm["missing"]) + ".")
        if machine:
            fits = machine.upper() in {m.upper() for m in p["_models"]}
            c["fits_requested_machine"] = fits
            if not fits: risks.append(f"No recorded fitment to {machine}.")
        c.update(commercial_status(p, qty, dl))
        c["risks"] = risks
        c["selected_because"] = " ".join(c["reasons"])
    note = []
    if dl: note.append(f"Deadline of {dl} days cannot be validated: lead-time data is not available.")
    if rfq["constraints"]: note.append("Constraints noted (" + ", ".join(rfq["constraints"]) + "): verify per part in Graph Insights > Compliance (demo compliance data).")
    note.append("Stock, price and lead time are not connected: this shortlist shows which parts fit the request, not whether they can be supplied.")
    return {"request": text, "parsed": {**rfq, "machine_model": machine}, "matches": base["results"], "notes": note,
            "method": base["method"] + "; requested quantity is recorded but NOT compared with any stock figure"}
