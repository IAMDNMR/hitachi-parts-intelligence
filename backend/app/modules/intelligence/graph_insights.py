"""
backend/app/modules/intelligence/graph_insights.py

Phase 10 Graph Insights — the four tabs of the Parts Intelligence modal
(Impact · Compliance · Supplier Risk · Mitigation) in ONE response, built
from a handful of graph queries (no per-part round trips).

Every section carries `data_basis`, naming what is HCME source data and what
is SYNTHETIC_DEMO, so the UI and the assistant can state provenance.
"""

from typing import Any, Dict, List, Optional

from app.errors.exceptions import NotFoundError
from app.modules.intelligence import interchangeability
from app.modules.intelligence.scoring import calculate_compatibility_score, calculate_mitigation_score

_IMPACT_Q = """
MATCH (p:Part {part_id: $id})<-[c:CONTAINS_PART]-(a:Assembly)<-[:HAS_ASSEMBLY]-(m:Machine)
RETURN m.machine_id AS machine_id, coalesce(m.official_product_name, m.model) AS name, m.model AS model,
       m.product_family AS family, m.machine_category AS category,
       a.name AS assembly, a.criticality AS criticality, c.quantity AS qty, c.unit AS unit
ORDER BY name
"""

_COMPLIANCE_Q = """
MATCH (p:Part {part_id: $id})<-[:CONTAINS_PART]-(a:Assembly)-[:REQUIRES_COMPLIANCE]->(c:ComplianceRequirement)
OPTIONAL MATCH (c)-[:DEPENDS_ON]->(parent:ComplianceRequirement)
RETURN DISTINCT c.compliance_id AS compliance_id, c.name AS name, c.regulation_standard AS standard,
       a.name AS via, parent.name AS parent, coalesce(c.synthetic, false) AS synthetic,
       EXISTS { (p)-[:HAS_CERTIFICATION|HAS_COMPLIANCE_REQUIREMENT]->(c) } AS held
UNION
MATCH (p:Part {part_id: $id})-[:HAS_COMPLIANCE_REQUIREMENT]->(c:ComplianceRequirement)
OPTIONAL MATCH (c)-[:DEPENDS_ON]->(parent:ComplianceRequirement)
RETURN DISTINCT c.compliance_id AS compliance_id, c.name AS name, c.regulation_standard AS standard,
       'this part' AS via, parent.name AS parent, coalesce(c.synthetic, false) AS synthetic, true AS held
"""

_VERIFIED_PART_SUPPLIERS_Q = """
MATCH (p:Part {part_id: $id})-[l:SUPPLIED_BY]->(s:Supplier)
WHERE coalesce(s.synthetic, false) = false AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
RETURN s.supplier_id AS supplier_id, s.name AS name, s.country AS country, s.region AS region,
       s.tier AS tier, l.share_pct AS share_pct, l.role AS role
ORDER BY l.share_pct DESC
"""

_VERIFIED_CONCENTRATION_Q = """
MATCH (s:Supplier)<-[l:SUPPLIED_BY]-(q:Part)
WHERE coalesce(s.synthetic, false) = false AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
WITH s, q,
     EXISTS { (q)<-[:CONTAINS_PART]-(:Assembly {criticality: 'high'}) } AS critical,
     COUNT { (q)-[:SUPPLIED_BY]->(:Supplier) } AS n_suppliers
WITH s, sum(CASE WHEN critical THEN 1 ELSE 0 END) AS critical_parts,
        sum(CASE WHEN critical AND n_suppliers = 1 THEN 1 ELSE 0 END) AS sole_source_critical,
        count(q) AS parts
RETURN s.supplier_id AS supplier_id, s.name AS name, s.region AS region, s.country AS country,
       parts, critical_parts, sole_source_critical
ORDER BY sole_source_critical DESC, critical_parts DESC, parts DESC
"""

_REAL_SUPPLIER_SUMMARY_Q = """
MATCH (s:Supplier {data_source: 'HCME_SAP_SUPPLIER_MASTER'})
RETURN count(s) AS total
"""

_REAL_SUPPLIER_GEO_Q = """
MATCH (s:Supplier {data_source: 'HCME_SAP_SUPPLIER_MASTER'})-[:LOCATED_IN]->(c:City)-[:IN_COUNTRY]->(co:Country)
RETURN co.code AS code, coalesce(co.name, co.code) AS country, count(DISTINCT s) AS count
ORDER BY count DESC
LIMIT 5
"""

_REAL_SUPPLIER_SAMPLE_Q = """
MATCH (s:Supplier {data_source: 'HCME_SAP_SUPPLIER_MASTER'})-[:LOCATED_IN]->(c:City)-[:IN_COUNTRY]->(co:Country)
RETURN s.supplier_number AS supplier_number, coalesce(s.display_name, s.name) AS name, c.name AS city, coalesce(co.name, co.code) AS country
ORDER BY s.supplier_number
LIMIT 5
"""

_CANDIDATES_Q = """
MATCH (q:Part) WHERE q.part_id <> $id
RETURN q AS part,
       [(m:Machine)-[:HAS_PART_FITMENT]->(q) | m.machine_id] AS machine_ids,
       [(q)-[:SUPPLIED_BY]->(s:Supplier) WHERE coalesce(s.synthetic, false) = false | s.name] AS suppliers,
       [(q)-[:HAS_CERTIFICATION|HAS_COMPLIANCE_REQUIREMENT]->(c:ComplianceRequirement) | c.compliance_id] AS held,
       [(q)-[:HAS_SYNTHETIC_INVENTORY]->(i:InventorySnapshot {location_type: 'DEPOT'}) | i.quantity] AS depot_stock
"""

MITIGATION_STEPS = ["Analyse impact", "Find alternatives", "Validate compliance", "Assess supplier risk", "Rank mitigation"]


def get_part_graph_insights(session, part_id: str) -> Dict[str, Any]:
    row = session.run("MATCH (p:Part {part_id: $id}) RETURN p", id=part_id).single()
    if not row:
        raise NotFoundError(f"Part '{part_id}' not found")
    part = dict(row["p"])

    impact = _impact(session.run(_IMPACT_Q, id=part_id).data())
    compliance = _compliance(session.run(_COMPLIANCE_Q, id=part_id).data())
    
    verified_part_suppliers = session.run(_VERIFIED_PART_SUPPLIERS_Q, id=part_id).data()
    verified_concentration = session.run(_VERIFIED_CONCENTRATION_Q).data() if verified_part_suppliers else []
    total_suppliers = session.run(_REAL_SUPPLIER_SUMMARY_Q).single()["total"]
    geo_dist = session.run(_REAL_SUPPLIER_GEO_Q).data()
    sample_suppliers = session.run(_REAL_SUPPLIER_SAMPLE_Q).data()

    supplier_risk = _supplier_risk(
        verified_part_suppliers,
        verified_concentration,
        impact,
        total_suppliers=total_suppliers,
        geo_dist=geo_dist,
        samples=sample_suppliers,
    )
    mitigation = _mitigation(part, impact, compliance, supplier_risk,
                             session.run(_CANDIDATES_Q, id=part_id).data())
    return {
        "part": {
            "part_id": part["part_id"],
            "part_number": part.get("part_number"),
            "part_name": part.get("part_name"),
            "part_category": part.get("part_category"),
            "part_subcategory": part.get("part_subcategory"),
            "source_id": part.get("source_id"),
            "confidence": part.get("confidence"),
        },
        "impact": impact,
        "compliance": compliance,
        "supplier_risk": supplier_risk,
        "mitigation": mitigation,
    }


def _impact(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    machines: Dict[str, Dict[str, Any]] = {}
    assemblies: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        machines.setdefault(r["machine_id"], {
            "machine_id": r["machine_id"], "name": r["name"], "model": r["model"],
            "family": r["family"], "category": r["category"],
        })
        a = assemblies.setdefault(r["assembly"], {"name": r["assembly"], "criticality": r["criticality"],
                                                  "qty": 0, "unit": r["unit"], "machines": 0})
        a["qty"] += r["qty"] or 0
        a["machines"] += 1
    ranked = sorted(assemblies.values(), key=lambda a: (["high", "medium", "low"].index(a["criticality"]), -a["qty"]))
    return {
        "affected_machines": len(machines),
        "total_bom_qty": sum(a["qty"] for a in ranked),
        "critical_paths": [a for a in ranked if a["criticality"] == "high"],
        "machines": list(machines.values()),
        "assemblies": ranked,
        "data_basis": "Machines and assembly names: HCME source fitment data. "
                      "BOM quantities and assembly criticality: SYNTHETIC DEMO DATA.",
    }


def _compliance(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = sorted(rows, key=lambda r: (r["via"] != "this part", r["via"], r["name"]))
    gaps = [{"requirement": r["name"], "standard": r["standard"], "required_by": r["via"]}
            for r in rows if not r["held"]]
    return {
        "requirements": rows,
        "gaps": gaps,
        "status": "GAPS_FOUND" if gaps else ("COMPLIANT" if rows else "NO_REQUIREMENTS_RECORDED"),
        "data_basis": "Regulations are real EU instruments. Their assignment to assemblies and the part "
                      "certificates are SYNTHETIC DEMO DATA, except the EU Battery Regulation on "
                      "HCME-published batteries (source SRC-039).",
    }


def _supplier_risk(part_suppliers, concentration, impact, total_suppliers: int = 1720,
                   geo_dist: Optional[List[Dict[str, Any]]] = None,
                   samples: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    if part_suppliers:
        # STATE A: Verified Supplier -> Part relationships exist
        sole = len(part_suppliers) == 1
        critical = bool(impact["critical_paths"])
        if sole and critical:
            spof = {"is_spof": True,
                    "reason": f"Sole-sourced from {part_suppliers[0]['name']} and used in high-criticality "
                              f"assemblies ({', '.join(a['name'] for a in impact['critical_paths'])})."}
        elif sole:
            spof = {"is_spof": False, "reason": "Sole-sourced, but not used in any high-criticality assembly."}
        else:
            spof = {"is_spof": False, "reason": "Dual-sourced — not a single point of failure."}
        return {
            "status": "CONNECTED",
            "connected": True,
            "part_suppliers": part_suppliers,
            "dual_source": len(part_suppliers) >= 2,
            "concentration": [c for c in concentration if c["critical_parts"]][:5],
            "spof": spof,
            "supplier_master_count": total_suppliers,
            "geographic_distribution": geo_dist or [],
            "sample_suppliers": samples or [],
            "data_basis": ("SYNTHETIC DEMO DATA — supplier-to-part links, shares and tiers are demonstration data. "
                           "The HCME SAP supplier master (real) has no part numbers yet."
                           if all(s.get("synthetic") for s in part_suppliers)
                           else "SOURCE_DERIVED — Verified HCME supplier-to-part sourcing records."),
            "provenance": "SYNTHETIC_DEMO" if all(s.get("synthetic") for s in part_suppliers) else "SOURCE_DERIVED",
        }

    # STATE B: Supplier master exists, but Supplier -> Part mapping is not available in current source data
    return {
        "status": "NOT_CONNECTED",
        "connected": False,
        "reason": ("Supplier master data is available, but supplier-to-part sourcing relationships are not "
                   "available in current HCME source data. Critical-part concentration and sole-source "
                   "analysis cannot be calculated from verified supplier data."),
        "supplier_master_count": total_suppliers,
        "available_dimensions": ["Supplier", "City", "Country"],
        "missing_relationship": "Supplier → Part",
        "required_source": "SAP purchasing/source-list/PO data containing supplier number + material/part number.",
        "risk_calculations": "UNAVAILABLE",
        "part_suppliers": [],
        "dual_source": False,
        "concentration": [],
        "spof": {
            "is_spof": False,
            "reason": "Supplier-to-part sourcing relationship is not recorded in current HCME source data.",
        },
        "geographic_distribution": geo_dist or [],
        "sample_suppliers": samples or [],
        "data_basis": f"HCME supplier master ({total_suppliers:,} records): supplier number, name, city and country. "
                      "The source has no supplier-to-part sourcing records, so none is shown.",
        "provenance": "SOURCE_DERIVED / NOT_CONNECTED",
    }


def _mitigation(part, impact, compliance, supplier_risk, candidates) -> Dict[str, Any]:
    required = {r["compliance_id"] for r in compliance["requirements"]}
    required_names = {r["compliance_id"]: r["name"] for r in compliance["requirements"]}
    target_machines = {m["machine_id"] for m in impact["machines"]}

    options = []
    for c in candidates:
        cand = dict(c["part"])
        # Hard filters: orderable part, same specific type (oil filter != fuel filter), shared machine fitment.
        if not interchangeability.gate(part, cand, target_machines, set(c["machine_ids"]))[0]:
            continue
        similarity, _ = calculate_compatibility_score(part, cand, target_machines, set(c["machine_ids"]))
        if similarity < 0.5:  # below this the part is a different kind of component
            continue
        gaps = sorted(required_names[r] for r in required - set(c["held"]))
        stock = sum(c["depot_stock"]) if c["depot_stock"] else None
        availability = "UNKNOWN" if stock is None else ("AVAILABLE" if stock > 0 else "OUT_OF_STOCK")
        risk = "LOW" if len(c["suppliers"]) >= 2 else ("HIGH" if c["suppliers"] else "UNKNOWN")
        score, _ = calculate_mitigation_score(similarity, availability,
                                              "COMPLIANT" if not gaps else "UNKNOWN", risk, cand.get("confidence"))
        options.append({
            "part_id": cand["part_id"], "part_number": cand.get("part_number"), "part_name": cand.get("part_name"),
            "similarity_pct": round(similarity * 100), "mitigation_score": round(score * 100),
            "suppliers": c["suppliers"], "compliance_gaps": gaps,
            "depot_stock": stock, "availability": availability,
        })
    options.sort(key=lambda o: (-o["mitigation_score"], -o["similarity_pct"]))
    options = options[:5]
    preferred = [o for o in options if o["similarity_pct"] >= 70 and not o["compliance_gaps"]]

    name = f"{part['part_id']} ({part.get('part_name')})"
    if impact["affected_machines"] == 0:
        summary = f"{name} is not fitted to any machine in the graph, so no machine is directly affected if it becomes unavailable."
    else:
        summary = (f"If {name} becomes unavailable, {impact['affected_machines']} machine model(s) are affected"
                   f"{' on high-criticality paths' if impact['critical_paths'] else ''}.")
    sups = supplier_risk.get("part_suppliers") or []
    if supplier_risk.get("connected") and sups:
        summary += (f" It is {'dual' if supplier_risk['dual_source'] else 'sole'}-sourced"
                    f"{' from ' + sups[0]['name'] if sups else ''}.")
    else:
        summary += " Supplier-to-part sourcing relationship is not connected in current HCME supplier master."
    if options:
        best = options[0]
        summary += (f" {len(options)} candidate(s) for engineering review (not approved replacements); first is {best['part_id']} "
                    f"(similarity {best['similarity_pct']}%, mitigation score {best['mitigation_score']}"
                    f"{', compliance gaps: ' + ', '.join(best['compliance_gaps']) if best['compliance_gaps'] else ', no compliance gaps'}).")
    else:
        summary += " No candidate of the same part type with shared machine fitment exists in the catalogue."

    return {
        "executive_summary": summary.strip(),
        "affected_machines": impact["affected_machines"],
        "preferred_substitutes_exist": bool(preferred),
        "steps": MITIGATION_STEPS,
        "alternatives": options,
        "data_basis": "Similarity is computed from HCME catalogue taxonomy and source fitment. Stock and "
                      "certificates used in the mitigation score are SYNTHETIC DEMO DATA; supplier-to-part "
                      "sourcing relationships are NOT CONNECTED.",
    }
