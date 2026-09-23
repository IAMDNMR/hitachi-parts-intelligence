"""
Disruption scenarios and mitigation options (Phase 11b - corrected for HCME).

Scenarios:  part_unavailable | supplier_unavailable | compliance_failure | stock_shortage
Each answers, from the graph: what is affected (parts, assemblies, machine models, open orders), the candidates for engineering
review, each candidate's compliance status, supplier dependency and stock, and why a candidate is shown or rejected.

What this module deliberately does NOT do
  * No severity number and no weighted score: the fixed weights of the first version were never validated by HCME, so results are
    ordered by stated rules and every factor is shown instead.
  * No candidate is an approved replacement. Candidates pass hard filters (orderable part, same specific part type, shared machine
    fitment - see interchangeability.py) and are labelled "Candidate for Engineering Review". No HCME supersession data is loaded.
  * No compliance PASS on synthetic evidence. PASS needs real evidence; demo certificates give UNVERIFIED.
  * No customers: there is no installed-base data, so `customers` is empty and says so.

Provenance of every block is returned in `provenance`: machines/fitment are SOURCE_DERIVED; assemblies/BOM/criticality, supplier-part
links, certificates and stock are SYNTHETIC_DEMO today. Real SAP purchasing data would populate the same relationships later
(see docs/research/PHASE_11_SUPPLIER_DATA_MODEL.md) with synthetic=false and this module reports them as REAL automatically.
"""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.errors.exceptions import NotFoundError
from app.modules.intelligence import interchangeability as ic
from app.modules.intelligence import similarity

EXPIRY_WARNING_DAYS = 90
SCENARIOS = ("part_unavailable", "supplier_unavailable", "compliance_failure", "stock_shortage")
NO_INSTALLED_BASE = "No customer installed-base data exists in the graph, so affected customers cannot be listed."
STATUS_CANDIDATE = ic.CANDIDATE_LABEL
STATUS_NOT_SUITABLE = "Not Suitable"
STATUS_INSUFFICIENT = "Insufficient Data"


def _provenance(sup_links: List[Dict[str, Any]], comp_real: Optional[bool] = None) -> Dict[str, str]:
    real_sup = bool(sup_links) and all(not s["synthetic"] for s in sup_links)
    return {
        "machines_and_fitment": "SOURCE_DERIVED (HCME fitment data)",
        "assemblies_bom_criticality": "SYNTHETIC_DEMO",
        "supplier_links": ("REAL" if real_sup else "SYNTHETIC_DEMO" if sup_links else "NOT_CONNECTED"),
        "compliance_evidence": "REAL" if comp_real else "SYNTHETIC_DEMO",
        "stock": "SYNTHETIC_DEMO",
        "orders": "SYNTHETIC_DEMO / browser-created",
    }


# --------------------------------------------------------------------------- graph reads

def _part(session, part_id: str) -> Dict[str, Any]:
    row = session.run("MATCH (p:Part {part_id:$id}) RETURN p", id=part_id).single()
    if not row:
        raise NotFoundError(f"Part '{part_id}' not found")
    return dict(row["p"])


def usage(session, part_id: str) -> Dict[str, Any]:
    """Where the part is used: machine models (real fitment) and assemblies (SYNTHETIC_DEMO BOM)."""
    machines = {r["machine_id"]: r for r in session.run(
        "MATCH (m:Machine)-[:HAS_PART_FITMENT]->(:Part {part_id:$id}) RETURN m.machine_id AS machine_id, m.model AS model", id=part_id).data()}
    rows = session.run(
        """MATCH (m:Machine)-[:HAS_ASSEMBLY]->(a:Assembly)-[c:CONTAINS_PART]->(:Part {part_id:$id})
           RETURN a.name AS assembly, a.criticality AS criticality, c.quantity AS quantity,
                  coalesce(a.synthetic, false) AS synthetic""", id=part_id).data()
    asm: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        a = asm.setdefault(r["assembly"], {"assembly": r["assembly"], "criticality": r["criticality"], "machines": 0, "bom_qty": 0,
                                          "basis": "SYNTHETIC_DEMO" if r["synthetic"] else "REAL"})
        a["machines"] += 1
        a["bom_qty"] += r["quantity"] or 0
    return {"machines": sorted(machines.values(), key=lambda m: m["model"] or ""), "assemblies": sorted(asm.values(), key=lambda a: a["assembly"])}


def customers_for(session, machine_ids: List[str]) -> List[Dict[str, Any]]:
    """Customer -OPERATES-> Machine. Not populated (no installed-base data); returns [] until real data is loaded."""
    if not machine_ids:
        return []
    return session.run(
        """MATCH (c:Customer)-[o:OPERATES]->(m:Machine) WHERE m.machine_id IN $ids
           RETURN c.customer_id AS customer_id, c.name AS name, c.country AS country, coalesce(c.synthetic,false) AS synthetic,
                  collect(DISTINCT m.model) AS machines, sum(coalesce(o.units,1)) AS units ORDER BY name""", ids=machine_ids).data()


def open_orders(session, part_id: str) -> List[Dict[str, Any]]:
    return session.run(
        """MATCH (o:Order)-[:FOR_PART]->(:Part {part_id:$id}) WHERE o.testRunId IS NULL AND o.status <> 'CANCELLED'
           RETURN o.id AS order_id, o.status AS status, o.quantity AS quantity, o.destinationBranchId AS dealer_id,
                  coalesce(o.synthetic,false) AS synthetic ORDER BY o.id""", id=part_id).data()


def suppliers_of(session, part_id: str) -> List[Dict[str, Any]]:
    """Part -SUPPLIED_BY-> Supplier. `synthetic` distinguishes demo links from real SAP purchasing links (none exist yet)."""
    return session.run(
        """MATCH (:Part {part_id:$id})-[l:SUPPLIED_BY]->(s:Supplier)
           RETURN s.supplier_id AS supplier_id, s.name AS name, s.country AS country, l.role AS role,
                  l.share_pct AS share_pct, coalesce(l.synthetic,false) AS synthetic ORDER BY share_pct DESC""", id=part_id).data()


def stock_of(session, part_id: str) -> Dict[str, Any]:
    rows = session.run(
        """MATCH (:Part {part_id:$id})-[:HAS_SYNTHETIC_INVENTORY]->(i:InventorySnapshot)
           RETURN i.location_id AS location, i.location_type AS type, i.quantity AS quantity""", id=part_id).data()
    return {"total": sum(r["quantity"] or 0 for r in rows) if rows else None, "locations": rows,
            "basis": "SYNTHETIC_DEMO stock snapshots - no real stock feed is connected"}


def requirements_of(session, part_id: str) -> List[Dict[str, Any]]:
    """Requirements the part INHERITS from every assembly it sits in (Assembly -REQUIRES_COMPLIANCE-> Requirement)."""
    return session.run(
        """MATCH (:Part {part_id:$id})<-[:CONTAINS_PART]-(a:Assembly)-[:REQUIRES_COMPLIANCE]->(c:ComplianceRequirement)
           RETURN c.compliance_id AS compliance_id, c.name AS name, collect(DISTINCT a.name) AS via_assemblies
           ORDER BY name""", id=part_id).data()


def evidence_of(session, part_id: str) -> Dict[str, Dict[str, Any]]:
    rows = session.run(
        """MATCH (:Part {part_id:$id})-[r:HAS_CERTIFICATION|HAS_COMPLIANCE_REQUIREMENT]->(c:ComplianceRequirement)
           RETURN c.compliance_id AS cid, type(r) AS kind, toString(r.valid_until) AS valid_until,
                  coalesce(r.synthetic, false) AS synthetic""", id=part_id).data()
    return {r["cid"]: r for r in rows}


# --------------------------------------------------------------------------- compliance

def compliance_verdict(session, target_id: str, candidate_id: str, only: Optional[List[str]] = None,
                       today: Optional[date] = None) -> Dict[str, Any]:
    """Does the candidate hold evidence for every requirement the TARGET's assemblies impose?

    FAIL                     a requirement has no evidence, or its certificate has expired
    WARNING                  a certificate expires within 90 days
    PASS                     every requirement is covered by REAL (non-synthetic) evidence
    UNVERIFIED               covered, but only by synthetic/demo evidence - never presented as compliant
    NO_REQUIREMENT_RECORDED  nothing is recorded for the assemblies this part sits in
    Structure is ready for real HCME compliance evidence: real edges (synthetic=false) make the same code return PASS."""
    today = today or date.today()
    required = [r for r in requirements_of(session, target_id) if not only or r["compliance_id"] in only]
    held = evidence_of(session, candidate_id)
    missing, expired, expiring, real_ok, demo_ok = [], [], [], [], []
    for r in required:
        ev = held.get(r["compliance_id"])
        if not ev:
            missing.append(r["name"])
            continue
        vu = ev.get("valid_until")
        if vu:
            d = date.fromisoformat(vu)
            if d < today:
                expired.append(f"{r['name']} (expired {vu})")
                continue
            if d <= today + timedelta(days=EXPIRY_WARNING_DAYS):
                expiring.append(f"{r['name']} (expires {vu})")
                continue
        (demo_ok if ev["synthetic"] else real_ok).append(r["name"])
    if not required:
        status = "NO_REQUIREMENT_RECORDED"
    elif missing or expired:
        status = "FAIL"
    elif expiring:
        status = "WARNING"
    elif demo_ok:
        status = "UNVERIFIED"
    else:
        status = "PASS"
    return {"status": status, "required": [r["name"] for r in required],
            "inherited_from": {r["name"]: r["via_assemblies"] for r in required},
            "satisfied_real_evidence": real_ok, "satisfied_demo_evidence": demo_ok,
            "missing": missing, "expired": expired, "expiring_soon": expiring,
            "verified": status == "PASS",
            "basis": "The requirement assignment and the certificates are SYNTHETIC_DEMO unless listed under real evidence; "
                     "a demo certificate never yields PASS."}


# --------------------------------------------------------------------------- candidates

_COMP_RANK = {"PASS": 0, "UNVERIFIED": 1, "NO_REQUIREMENT_RECORDED": 1, "WARNING": 2, "FAIL": 3}
_SUP_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 1, "UNKNOWN": 2, "BLOCKED": 3}
_STOCK_RANK = {"AVAILABLE": 0, "LOW": 1, "UNKNOWN": 2, "NONE": 3}


def _supplier_view(sups: List[Dict[str, Any]], banned_suppliers: set) -> Dict[str, Any]:
    live = [s for s in sups if s["supplier_id"] not in banned_suppliers]
    basis = "SYNTHETIC_DEMO" if any(s["synthetic"] for s in sups) else "REAL"
    if not sups:
        return {"risk": "UNKNOWN", "basis": "NOT_CONNECTED", "suppliers": 0, "usable_suppliers": 0, "note": "No supplier recorded."}
    if not live:
        return {"risk": "BLOCKED", "basis": basis, "suppliers": len(sups), "usable_suppliers": 0,
                "note": "Every recorded supplier is the disrupted supplier."}
    if len(live) >= 2:
        return {"risk": "LOW", "basis": basis, "suppliers": len(sups), "usable_suppliers": len(live), "note": f"{len(live)} usable suppliers."}
    return {"risk": "HIGH" if len(sups) == 1 else "MEDIUM", "basis": basis, "suppliers": len(sups), "usable_suppliers": 1,
            "note": "Single usable supplier (sole-source dependency)."}


def _stock_view(total: Optional[int]) -> Dict[str, Any]:
    if total is None:
        return {"status": "UNKNOWN", "on_hand": None, "basis": "SYNTHETIC_DEMO"}
    if total <= 0:
        return {"status": "NONE", "on_hand": total, "basis": "SYNTHETIC_DEMO"}
    return {"status": "AVAILABLE" if total >= 10 else "LOW", "on_hand": total, "basis": "SYNTHETIC_DEMO"}


def candidates_for(session, target_id: str, banned_suppliers: Optional[set] = None, only_requirements: Optional[List[str]] = None,
                   need_stock: bool = False, limit: int = 5, loaded: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Candidates for engineering review for one target part, each with compliance, supplier dependency, stock and the reasons it is
    shown or rejected. Ordered by rules (below), not by a weighted score."""
    banned_suppliers = banned_suppliers or set()
    sim = similarity.similar_parts(session, target_id, limit=12, loaded=loaded)
    rows: List[Dict[str, Any]] = []
    for alt in sim["alternatives"]:
        cid = alt["part_id"]
        comp = compliance_verdict(session, target_id, cid, only=only_requirements)
        sup = _supplier_view(suppliers_of(session, cid), banned_suppliers)
        stk = _stock_view(stock_of(session, cid)["total"])
        why_not = []
        if comp["status"] == "FAIL":
            why_not.append("compliance FAIL: " + "; ".join(comp["missing"] + comp["expired"]) + " (demo evidence)")
        if sup["risk"] == "BLOCKED":
            why_not.append("its only supplier is the disrupted supplier")
        if need_stock and stk["status"] in ("NONE", "UNKNOWN"):
            why_not.append("no stock recorded to cover the shortage (demo stock)")
        open_q = []
        if comp["status"] in ("UNVERIFIED", "NO_REQUIREMENT_RECORDED"):
            open_q.append("compliance not verified with real evidence")
        if sup["risk"] == "UNKNOWN":
            open_q.append("supplier unknown")
        if stk["status"] == "UNKNOWN":
            open_q.append("stock unknown")
        if why_not:
            status = STATUS_NOT_SUITABLE
        elif len(open_q) == 3:
            status = STATUS_INSUFFICIENT
        else:
            status = STATUS_CANDIDATE
        rows.append({"part_id": cid, "part_name": alt["part_name"], "part_number": alt.get("part_number"), "status": status,
                     "shared_machine_models": alt["shared_machines"], "machine_coverage_pct": alt["machine_coverage_pct"],
                     "text_similarity_pct": alt["similarity_pct"], "similarity_role": alt["similarity_role"],
                     "compliance": comp, "supplier_dependency": sup, "stock": stk,
                     "not_suitable_because": why_not, "open_questions": open_q, "why_shown": alt["reasons"]})
    order = {STATUS_CANDIDATE: 0, STATUS_INSUFFICIENT: 1, STATUS_NOT_SUITABLE: 2}
    rows.sort(key=lambda r: (order[r["status"]], _COMP_RANK[r["compliance"]["status"]], _SUP_RANK[r["supplier_dependency"]["risk"]],
                             _STOCK_RANK[r["stock"]["status"]], -r["machine_coverage_pct"], -r["text_similarity_pct"], r["part_id"]))
    for i, r in enumerate(rows):
        r["order"] = i + 1
    return {"target": target_id, "candidates": rows[:limit], "not_candidates": sim["rejected"], "label": STATUS_CANDIDATE,
            "explanation": _explain(target_id, rows, sim),
            "ordering_rule": "Not Suitable last; then compliance evidence, supplier dependency, stock, shared machine fitment; text similarity only "
                             "breaks ties. No score or weights: none have been validated by HCME.",
            "authoritative_data": sim.get("authoritative_data")}


def _explain(target: str, rows: List[Dict[str, Any]], sim: Dict[str, Any]) -> str:
    if sim.get("note"):
        return sim["note"]
    if not rows:
        return (f"No candidate for {target}: nothing else in the catalogue is the same part type and fitted to the same machines. "
                "Qualify a new part or a second source with HCME engineering.")
    top = rows[0]
    if top["status"] == STATUS_NOT_SUITABLE:
        return (f"No suitable candidate: {top['part_id']} passes the fitment/type filters but is not suitable - "
                + "; ".join(top["not_suitable_because"]) + ".")
    txt = (f"{top['part_id']} is listed first as a {STATUS_CANDIDATE.lower()} because it is the same part type, shares "
           f"{top['shared_machine_models']} machine models ({top['machine_coverage_pct']}%), compliance is {top['compliance']['status']}, "
           f"supplier dependency {top['supplier_dependency']['risk']}, stock {top['stock']['status']}")
    if top["open_questions"]:
        txt += "; open: " + ", ".join(top["open_questions"])
    rejected = [r for r in rows[1:] if r["status"] == STATUS_NOT_SUITABLE]
    if rejected:
        txt += f". {rejected[0]['part_id']} is not suitable: " + "; ".join(rejected[0]["not_suitable_because"])
    return txt + ". Not an approved replacement."


# --------------------------------------------------------------------------- scenarios

def _impact_block(session, part_id: str) -> Dict[str, Any]:
    u = usage(session, part_id)
    cust = customers_for(session, [m["machine_id"] for m in u["machines"]])
    return {"machines": u["machines"], "assemblies": u["assemblies"], "customers": cust,
            "customers_note": None if cust else NO_INSTALLED_BASE, "orders": open_orders(session, part_id)}


def _dependency(sups: List[Dict[str, Any]]) -> Dict[str, Any]:
    real = [s for s in sups if not s["synthetic"]]
    return {"suppliers": sups, "sole_source": bool(sups) and all(s["role"] == "SOLE" for s in sups),
            "basis": "REAL" if real and len(real) == len(sups) else "SYNTHETIC_DEMO" if sups else "NOT_CONNECTED",
            "note": None if real else "No real supplier-to-part data is connected; any link shown is a demo link."}


def _facts(imp: Dict[str, Any]) -> str:
    return (f"{len(imp['machines'])} machine models (source-derived fitment), {len(imp['assemblies'])} assemblies (demo BOM), "
            f"{len(imp['orders'])} open orders")


def _scenario_part(session, scenario: str, part_id: str, cand_kwargs: Dict[str, Any], lead: str) -> Dict[str, Any]:
    part = _part(session, part_id)
    imp = _impact_block(session, part_id)
    sups = suppliers_of(session, part_id)
    mit = candidates_for(session, part_id, **cand_kwargs)
    out = {"scenario": scenario, "trigger": {"part_id": part_id, "part_name": part.get("part_name"), "family_record": ic.is_family(part)},
           "affected": {"parts": [{"part_id": part_id, "part_name": part.get("part_name")}], **imp},
           "supplier_dependency": _dependency(sups), "mitigation": [mit],
           "provenance": _provenance(sups)}
    out["summary"] = f"{lead} affects {_facts(imp)}. " + mit["explanation"]
    return out


def part_unavailable(session, part_id: str) -> Dict[str, Any]:
    return _scenario_part(session, "part_unavailable", part_id, {}, f"{part_id} unavailable")


def compliance_failure(session, part_id: str, compliance_id: Optional[str] = None) -> Dict[str, Any]:
    req = requirements_of(session, part_id)
    only = [compliance_id] if compliance_id else [r["compliance_id"] for r in req]
    named = [r["name"] for r in req if r["compliance_id"] in only]
    out = _scenario_part(session, "compliance_failure", part_id, {"only_requirements": only},
                         f"Assuming {part_id} fails {', '.join(named) or 'its compliance requirements'}, it")
    out["trigger"]["requirements"] = named
    out["inherited_requirements"] = req
    return out


def stock_shortage(session, part_id: str) -> Dict[str, Any]:
    out = _scenario_part(session, "stock_shortage", part_id, {"need_stock": True}, f"A shortage of {part_id}")
    st = stock_of(session, part_id)
    demand = sum(o["quantity"] or 0 for o in out["affected"]["orders"])
    out["stock"] = {**st, "open_order_demand": demand,
                    "shortfall": None if st["total"] is None else max(demand - st["total"], 0),
                    "note": "Stock is a SYNTHETIC_DEMO snapshot; treat as an illustration of the workflow, not a real position."}
    return out


def supplier_unavailable(session, supplier: str) -> Dict[str, Any]:
    sups = session.run(
        """MATCH (s:Supplier) WHERE s.supplier_id = $q OR toLower(s.name) CONTAINS toLower($q)
           OPTIONAL MATCH (s)<-[l:SUPPLIED_BY]-(:Part)
           RETURN s.supplier_id AS supplier_id, s.name AS name, s.country AS country, count(l) AS links
           ORDER BY links DESC, name LIMIT 5""", q=supplier).data()
    if not sups:
        raise NotFoundError(f"Supplier '{supplier}' not found")
    chosen = sups[0]
    ids = {chosen["supplier_id"]}
    rows = session.run(
        """MATCH (p:Part)-[l:SUPPLIED_BY]->(s:Supplier {supplier_id:$sid}) WHERE p.part_id STARTS WITH 'PT-'
           RETURN p.part_id AS part_id, p.part_name AS part_name, l.role AS role, l.share_pct AS share_pct,
                  coalesce(l.synthetic,false) AS synthetic""", sid=chosen["supplier_id"]).data()
    parts, machines, assemblies, orders, links = [], {}, {}, [], []
    for r in rows:
        allsup = suppliers_of(session, r["part_id"])
        other = [x for x in allsup if x["supplier_id"] not in ids]
        parts.append({**r, "sole_source": r["role"] == "SOLE" or not other, "remaining_suppliers": [x["name"] for x in other]})
        links += allsup
        u = usage(session, r["part_id"])
        machines.update({m["machine_id"]: m for m in u["machines"]})
        for a in u["assemblies"]:
            assemblies.setdefault(a["assembly"], a)
        orders += [{**o, "part_id": r["part_id"]} for o in open_orders(session, r["part_id"])]
    sole = [p for p in parts if p["sole_source"]]
    loaded = similarity._load_parts(session)  # one catalogue read shared by every part below
    mitigation = []
    for p in sorted(sole, key=lambda x: x["part_id"]):  # show the parts that have candidates first; the rest are counted
        m = candidates_for(session, p["part_id"], banned_suppliers=ids, limit=3, loaded=loaded)
        if m["candidates"]:
            mitigation.append(m)
    without = len(sole) - len(mitigation)
    notes = []
    if not parts:
        notes.append(f"'{chosen['name']}' is in the HCME SAP supplier master but has no supplier-to-part link in the data (NOT_CONNECTED: "
                     "SAP purchasing data is required), so part-level impact cannot be calculated.")
    else:
        notes.append("The supplier-to-part links used here are SYNTHETIC_DEMO; no real SAP purchasing data is connected.")
        if without:
            notes.append(f"{without} of the {len(sole)} sole-sourced parts have no candidate at all (nothing else of the same part type is fitted to the same machines): "
                         "they need a second source or a new part qualified with HCME engineering.")
    customers = customers_for(session, list(machines))
    alt_suppliers = sorted({x["name"] for x in links if x["supplier_id"] not in ids})
    summary = (f"If {chosen['name']} is unavailable: {len(parts)} parts are supplied by it ({len(sole)} with no other supplier), "
               f"{len(assemblies)} assemblies (demo BOM), {len(machines)} machine models (source-derived fitment), {len(orders)} open orders."
               if parts else f"{chosen['name']}: no part in the graph is supplied by it, so no part-level impact can be shown.")
    return {"scenario": "supplier_unavailable", "trigger": {"label": chosen["name"], "supplier_id": chosen["supplier_id"], "country": chosen["country"]},
            "affected": {"parts": parts, "assemblies": sorted(assemblies.values(), key=lambda a: a["assembly"]),
                         "machines": sorted(machines.values(), key=lambda m: m["model"] or ""), "customers": customers, "orders": orders,
                         "customers_note": None if customers else NO_INSTALLED_BASE},
            "alternative_suppliers": alt_suppliers, "mitigation": mitigation, "summary": summary, "notes": notes,
            "supplier_dependency": {"sole_source_parts": len(sole), "basis": _provenance(links)["supplier_links"]},
            "provenance": _provenance(links)}


def analyse(session, scenario: str, part_id: Optional[str] = None, supplier: Optional[str] = None,
            compliance_id: Optional[str] = None) -> Dict[str, Any]:
    if scenario == "part_unavailable" and part_id: return part_unavailable(session, part_id)
    if scenario == "supplier_unavailable" and supplier: return supplier_unavailable(session, supplier)
    if scenario == "compliance_failure" and part_id: return compliance_failure(session, part_id, compliance_id)
    if scenario == "stock_shortage" and part_id: return stock_shortage(session, part_id)
    raise ValueError(f"scenario must be one of {SCENARIOS} with its required parameter (part_id / supplier)")
