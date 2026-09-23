"""
Parts Intelligence KPIs calculable from the CURRENT graph (Phase 11).

Each KPI returns numerator/denominator, method, data source (real vs SYNTHETIC_DEMO) and a `measurable` flag; a KPI the
data cannot support is returned as measurable=false with the reason - never a made-up number.

Headline KPIs: order traceability, master-data consistency, supplier-to-part coverage, share of orders with a known status.
`demo_only`: stock-out exposure (demo stock covers only some parts). `rule_checks`: customs flag detection (too few shipments to headline).
Removed: order-status resolution time (measured lookup speed, not a business outcome) and cross-catalog matching accuracy (one catalogue,
no ground truth - it returns when a second catalogue and a labelled mapping exist).
"""
from typing import Any, Dict

from app.modules.intelligence import context as intelligence_context

EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT",
        "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}

_CHAIN_Q = """
MATCH (o:Order) WHERE o.testRunId IS NULL
OPTIONAL MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o)
OPTIONAL MATCH (o)-[:BASED_ON_ALLOCATION]->(al:Allocation)
OPTIONAL MATCH (o)-[:FOR_PART]->(p:Part)
OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(s:Shipment)
OPTIONAL MATCH (s)-[:SHIPPED_TO]->(d:DealerBranch)
OPTIONAL MATCH (s)-[:HAS_SERVICE_JOB]->(sj:ServiceJob)
RETURN o.id AS id, o.status AS status, fr IS NOT NULL AS request, al IS NOT NULL AS allocation, p IS NOT NULL AS part,
       s IS NOT NULL AS shipment, d IS NOT NULL AS dealer, sj IS NOT NULL AS service
"""

_MASTER_Q = """
CALL { MATCH (p:Part) WHERE p.testRunId IS NULL AND p.part_id STARTS WITH 'PT-'
       RETURN count(p) AS parts,
              sum(CASE WHEN p.part_name IS NOT NULL AND p.part_category IS NOT NULL AND p.source_id IS NOT NULL THEN 1 ELSE 0 END) AS attrs,
              sum(CASE WHEN EXISTS { (:Machine)-[:HAS_PART_FITMENT]->(p) } THEN 1 ELSE 0 END) AS fitted,
              sum(CASE WHEN EXISTS { (p)-[:OF_TYPE]->(:PartType) } THEN 1 ELSE 0 END) AS typed }
CALL { MATCH (d:DealerBranch)
       RETURN count(d) AS dealers,
              sum(CASE WHEN d.latitude IS NOT NULL AND d.longitude IS NOT NULL THEN 1 ELSE 0 END) AS dealers_geo,
              sum(CASE WHEN EXISTS { (d)-[:LOCATED_IN]->(:City)-[:IN_COUNTRY]->(:Country) } THEN 1 ELSE 0 END) AS dealers_linked }
CALL { MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
       RETURN count(s) AS suppliers,
              sum(CASE WHEN EXISTS { (s)-[:LOCATED_IN]->(:City)-[:IN_COUNTRY]->(:Country) } THEN 1 ELSE 0 END) AS suppliers_linked }
CALL { MATCH (m:Machine)
       RETURN count(m) AS machines, sum(CASE WHEN EXISTS { (m)-[:OF_TYPE]->(:MachineType) } THEN 1 ELSE 0 END) AS machines_typed }
RETURN parts, attrs, fitted, typed, dealers, dealers_geo, dealers_linked, suppliers, suppliers_linked, machines, machines_typed
"""

_SUPPLIER_COVERAGE_Q = """
CALL { MATCH (p:Part) WHERE p.testRunId IS NULL AND p.part_id STARTS WITH 'PT-'
       RETURN count(p) AS parts,
              sum(CASE WHEN EXISTS { (p)-[:SUPPLIED_BY]->(:Supplier) } THEN 1 ELSE 0 END) AS with_any,
              sum(CASE WHEN EXISTS { (p)-[:SUPPLIED_BY]->(s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' } THEN 1 ELSE 0 END) AS with_real,
              sum(CASE WHEN COUNT { (p)-[:SUPPLIED_BY]->(:Supplier) } = 1 THEN 1 ELSE 0 END) AS sole }
CALL { MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
       RETURN count(s) AS real_suppliers,
              sum(CASE WHEN EXISTS { (s)<-[:SUPPLIED_BY]-(:Part) } THEN 1 ELSE 0 END) AS real_linked }
RETURN parts, with_any, with_real, sole, real_suppliers, real_linked
"""

_STOCK_Q = """
MATCH (p:Part) WHERE p.testRunId IS NULL AND p.part_id STARTS WITH 'PT-'
CALL { WITH p OPTIONAL MATCH (p)-[:HAS_SYNTHETIC_INVENTORY]->(i:InventorySnapshot)
       RETURN sum(i.quantity) AS qty, count(i) AS snaps }
RETURN p.part_id AS id, CASE WHEN snaps = 0 THEN null ELSE qty END AS qty,
       EXISTS { (:Assembly {criticality:'high'})-[:CONTAINS_PART]->(p) } AS critical
"""

_CUSTOMS_Q = """
MATCH (dep:Depot) WITH head(collect(dep.country)) AS origin
MATCH (s:Shipment) WHERE s.testRunId IS NULL
OPTIONAL MATCH (s)-[:SHIPPED_TO]->(d:DealerBranch)
RETURN s.shipment_id AS id, origin, d.country AS destination, EXISTS { (s)-[:HAS_CUSTOMS_CONTEXT]->(:CustomsContext) } AS flagged
"""


def _pct(n: int, d: int):
    return round(100.0 * n / d, 1) if d else None


def order_traceability(session) -> Dict[str, Any]:
    rows = session.run(_CHAIN_Q).data()
    live = [r for r in rows if r["status"] != "CANCELLED"]
    links = ["request", "allocation", "part", "shipment", "dealer", "service"]
    full = [r for r in live if all(r[k] for k in links)]
    return {"kpi": "Order traceability rate", "measurable": bool(live), "numerator": len(full), "denominator": len(live),
            "value_pct": _pct(len(full), len(live)),
            "per_link_pct": {k: _pct(sum(1 for r in live if r[k]), len(live)) for k in links},
            "method": "graph-based: non-cancelled Order linked to FulfilmentRequest, Allocation, Part, Shipment, DealerBranch and ServiceJob",
            "data_source": "SYNTHETIC_DEMO demo orders plus browser-created orders; not ERP data",
            "not_traceable": [r["id"] for r in live if r not in full]}


KNOWN_ORDER_STATUSES = {"CREATED", "ACCEPTED", "CANCELLED"}  # the Order state machine (docs/business-process/PROCESS_STATES.md)


def orders_with_known_status(session) -> Dict[str, Any]:
    """Share of orders that carry a valid status AND whose status the graph can resolve for a user asking 'what is the status of order X'."""
    rows = session.run("MATCH (o:Order) WHERE o.testRunId IS NULL RETURN o.id AS id, o.status AS status").data()
    known = 0
    for r in rows:
        try:
            res = intelligence_context.get_order_status(session, r["id"])
        except Exception:
            res = None
        if res and r["status"] in KNOWN_ORDER_STATUSES:
            known += 1
    return {"kpi": "Share of orders with a known status", "measurable": bool(rows), "numerator": known, "denominator": len(rows),
            "value_pct": _pct(known, len(rows)),
            "method": "rule-based: order status is one of CREATED / ACCEPTED / CANCELLED and the status lookup resolves it",
            "data_source": "demo and browser-created orders; becomes meaningful on real order data"}


def master_data_consistency(session) -> Dict[str, Any]:
    m = session.run(_MASTER_Q).single()
    checks = [("parts with name + category + source", m["attrs"], m["parts"]), ("parts with machine fitment", m["fitted"], m["parts"]),
              ("parts typed (PartType)", m["typed"], m["parts"]), ("dealers with coordinates", m["dealers_geo"], m["dealers"]),
              ("dealers linked to City/Country", m["dealers_linked"], m["dealers"]),
              ("SAP suppliers linked to City/Country", m["suppliers_linked"], m["suppliers"]),
              ("machines typed (MachineType)", m["machines_typed"], m["machines"])]
    ok, total = sum(a for _, a, _ in checks), sum(b for _, _, b in checks)
    return {"kpi": "Master-data consistency rate", "measurable": total > 0, "numerator": ok, "denominator": total,
            "value_pct": _pct(ok, total),
            "checks": [{"check": n, "passing": a, "of": b, "pct": _pct(a, b)} for n, a, b in checks],
            "method": "rule-based completeness/link checks (the full 42-check audit is phase10_data_audit.py)",
            "data_source": "REAL catalogue, dealer and SAP supplier-master data"}


def supplier_part_coverage(session) -> Dict[str, Any]:
    c = session.run(_SUPPLIER_COVERAGE_Q).single()
    return {"kpi": "Supplier-to-part coverage", "measurable": c["parts"] > 0,
            "numerator": c["with_real"], "denominator": c["parts"], "value_pct": _pct(c["with_real"], c["parts"]),
            "with_any_supplier_pct": _pct(c["with_any"], c["parts"]), "demo_only_parts": c["with_any"] - c["with_real"],
            "sole_sourced_parts": c["sole"], "real_suppliers": c["real_suppliers"], "real_suppliers_linked_to_parts": c["real_linked"],
            "method": "graph-based: catalogue parts with a SUPPLIED_BY link to a REAL SAP-master supplier (headline) vs any supplier",
            "data_source": "headline is REAL and is 0% because the supplier master has no part numbers; the any-supplier figure is SYNTHETIC_DEMO",
            "needs": "SAP purchasing / source-list data with supplier number + material number"}


def stock_out_exposure(session) -> Dict[str, Any]:
    rows = session.run(_STOCK_Q).data()
    out = [r for r in rows if not r["qty"]]
    crit = [r for r in rows if r["critical"]]
    crit_out = [r for r in crit if not r["qty"]]
    return {"kpi": "Stock-out exposure", "demo_only": True, "measurable": bool(rows), "numerator": len(out), "denominator": len(rows),
            "value_pct": _pct(len(out), len(rows)),
            "critical_parts": len(crit), "critical_without_stock": len(crit_out), "critical_without_stock_pct": _pct(len(crit_out), len(crit)),
            "unknown_stock_part_ids": [r["id"] for r in rows if r["qty"] is None][:20],
            "method": "graph-based: catalogue parts with no (or zero) stock; 'critical' = part sits in a high-criticality assembly",
            "data_source": "DEMO ONLY: SYNTHETIC_DEMO stock snapshots exist for only some parts, so this figure reflects the demo seed, not HCME stock"}


def customs_flag_detection(session) -> Dict[str, Any]:
    rows = session.run(_CUSTOMS_Q).data()
    needs = [r for r in rows if r["destination"] and r["origin"] and r["destination"] not in EU27 and r["destination"] != r["origin"]]
    hit = [r for r in needs if r["flagged"]]
    false_flags = [r for r in rows if r["flagged"] and r not in needs]
    return {"kpi": "Customs flag detection rate", "measurable": bool(needs), "numerator": len(hit), "denominator": len(needs),
            "value_pct": _pct(len(hit), len(needs)), "shipments": len(rows), "false_flags": len(false_flags),
            "method": "rule-based: shipment from the EU depot to a dealer outside the EU customs union should carry a CustomsContext",
            "data_source": "SYNTHETIC_DEMO shipments and CustomsContext; no customs-authority or HS-code data",
            "caveat": "Only a handful of demo shipments exist, so this validates the rule, not real customs performance.",
            "needs": None if needs else "shipments to non-EU destinations"}


def all_kpis(session) -> Dict[str, Any]:
    return {
        "note": "Calculated live from the current graph. Demo/sample data; no live ERP, carrier, stock or customs integration.",
        "kpis": [order_traceability(session), master_data_consistency(session), supplier_part_coverage(session),
                 orders_with_known_status(session)],
        "demo_only": [stock_out_exposure(session)],
        "rule_checks": [customs_flag_detection(session)],  # not a headline KPI: too few shipments to mean anything
    }
