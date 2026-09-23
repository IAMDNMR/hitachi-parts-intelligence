#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 10 — SYNTHETIC_DEMO seed data for the Parts Intelligence screens and
the Parts Store waterfall.

No verified HCME stock, BOM, supplier or purchase-order data is public, so the
prototype needs demo records. Every node and relationship written here carries
synthetic=true and data_source='SYNTHETIC_DEMO', is generated deterministically
(same input -> same output, safe to re-run), and never overwrites a canonical
source-derived property. It is written only through this script — never from
React components or Python service logic.

    python docs/data/neo4j/scripts/seed_phase10_demo_data.py --step inventory            # dry run
    python docs/data/neo4j/scripts/seed_phase10_demo_data.py --step inventory --execute
"""
import argparse
import hashlib
import io
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[4]
load_dotenv(ROOT / "backend" / ".env")

SEED_NOTE = "Phase 10 synthetic demo record — not HCME operational data (seed_phase10_demo_data.py)."
DEPOT_ID = "DEPOT-OOSTERHOUT"


def bucket(key: str, n: int) -> int:
    """Deterministic 0..n-1 from a string key."""
    return int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % n


# ---------------------------------------------------------------------------
# Task 4b — depot stock for every catalogue part that has a part number
# ---------------------------------------------------------------------------
STOCK_LEVELS = [0, 2, 6, 12, 18, 25, 40]


def plan_inventory(s):
    parts = s.run(
        """MATCH (p:Part) WHERE p.part_number IS NOT NULL
           AND NOT EXISTS { MATCH (p)-[:HAS_SYNTHETIC_INVENTORY]->(:InventorySnapshot {location_id: $depot}) }
           RETURN p.part_id AS id ORDER BY id""", depot=DEPOT_ID).value()
    return [{"part_id": pid, "snapshot_id": f"INV-P10-{pid}-OOSTERHOUT",
             "quantity": STOCK_LEVELS[bucket(pid + ":stock", len(STOCK_LEVELS))]} for pid in parts]


def write_inventory(s, rows):
    return s.run(
        """UNWIND $rows AS r
           MATCH (p:Part {part_id: r.part_id})
           MERGE (i:InventorySnapshot {snapshot_id: r.snapshot_id})
           SET i.location_type = 'DEPOT', i.location_id = $depot, i.quantity = r.quantity,
               i.as_of = date(), i.synthetic = true, i.data_source = 'SYNTHETIC_DEMO',
               i.record_class = 'DEMO_INVENTORY', i.note = $note
           MERGE (p)-[rel:HAS_SYNTHETIC_INVENTORY]->(i)
           SET rel.synthetic = true, rel.data_source = 'SYNTHETIC_DEMO'
           RETURN count(i) AS n""", rows=rows, depot=DEPOT_ID, note=SEED_NOTE).single()["n"]


# ---------------------------------------------------------------------------
# Task 6 — BOM: Machine -[:HAS_ASSEMBLY]-> Assembly -[:CONTAINS_PART {quantity}]-> Part
# Built on the real fitment graph: which machine, which assembly name and which
# part all come from source-derived HAS_PART_FITMENT edges. Only the quantity
# and the assembly criticality are SYNTHETIC_DEMO, set by the rules below.
# ---------------------------------------------------------------------------

# Pieces per machine by part sub-category; one value is picked per machine.
QTY_BY_SUBCATEGORY = {
    "Track Roller": [12, 14, 16], "Carrier Roller": [2, 4], "Drive Sprocket": [2],
    "Battery": [1, 2], "Filter": [1, 2, 3], "Working Lights": [2, 4, 6],
}
FLUID_CATEGORIES = {"Genuine Fluid", "Consumable Fluid"}
# First matching rule wins (checked LOW -> MEDIUM -> HIGH).
CRITICALITY_RULES = [
    ("low", ("exterior", "cab", "light", "attachment", "breaker")),
    ("medium", ("sprocket", "roller", "track", "undercarriage", "electrical", "starter",
                "alternator", "major components", "grease")),
    ("high", ("engine", "hydraulic", "pump", "valve", "ecm", "transmission", "drive",
              "swing", "axle", "fuel", "solenoid", "cooling", "air intake")),
]
CRITICALITY_BASIS = ("SYNTHETIC_DEMO rule: exterior/cab/lights/attachments=low; undercarriage, "
                     "electrical, grease points, major components=medium; engine, hydraulics, drivetrain, "
                     "fuel, cooling, control=high (seed_phase10_demo_data.py)")


def assembly_name(raw: str) -> str:
    return re.sub(r"\s*\(installed.*\)$", "", raw).strip()


def criticality(name: str) -> str:
    n = name.lower()
    for level, words in CRITICALITY_RULES:
        if any(w in n for w in words):
            return level
    return "medium"


def plan_bom(s):
    rows = s.run(
        """MATCH (m:Machine)-[f:HAS_PART_FITMENT]->(p:Part)
           RETURN m.machine_id AS machine_id, f.assembly AS assembly, f.fitment_id AS fitment_id,
                  p.part_id AS part_id, p.part_category AS category, p.part_subcategory AS subcategory
           ORDER BY machine_id, part_id""").data()
    lines = []
    for r in rows:
        name = assembly_name(r["assembly"] or "Unassigned")
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        fluid = r["category"] in FLUID_CATEGORIES
        choices = QTY_BY_SUBCATEGORY.get(r["subcategory"], [1])
        lines.append({
            "machine_id": r["machine_id"], "part_id": r["part_id"], "fitment_id": r["fitment_id"],
            "assembly_id": f"ASM-{r['machine_id']}-{slug}", "assembly_name": name,
            "assembly_name_source": r["assembly"], "criticality": criticality(name),
            "quantity": 1 if fluid else choices[bucket(r["machine_id"] + r["part_id"], len(choices))],
            "unit": "fill" if fluid else "pcs",
        })
    return lines


def write_bom(s, rows):
    s.run("CREATE CONSTRAINT assembly_id_unique IF NOT EXISTS FOR (a:Assembly) REQUIRE a.assembly_id IS UNIQUE").consume()
    return s.run(
        """UNWIND $rows AS r
           MATCH (m:Machine {machine_id: r.machine_id})
               MATCH (p:Part {part_id: r.part_id})
               MERGE (a:Assembly {assembly_id: r.assembly_id})
               SET a.name = r.assembly_name, a.machine_id = r.machine_id,
                   a.name_source = 'HAS_PART_FITMENT.assembly (source-derived): ' + r.assembly_name_source,
                   a.criticality = r.criticality, a.criticality_basis = $basis,
                   a.synthetic = true, a.data_source = 'SYNTHETIC_DEMO', a.note = $note
               MERGE (m)-[h:HAS_ASSEMBLY]->(a)
               SET h.synthetic = true, h.data_source = 'SYNTHETIC_DEMO'
               MERGE (a)-[c:CONTAINS_PART]->(p)
               SET c.quantity = r.quantity, c.unit = r.unit, c.fitment_id = r.fitment_id,
                   c.synthetic = true, c.data_source = 'SYNTHETIC_DEMO'
               RETURN count(c) AS n""", rows=rows, basis=CRITICALITY_BASIS, note=SEED_NOTE).single()["n"]

# ---------------------------------------------------------------------------
# Task 7 — suppliers: Part -[:SUPPLIED_BY {share_pct}]-> Supplier
# No HCME supplier data is public. Fictional, clearly-named demo suppliers are
# used so no real company is attributed an invented supply relationship.
# ---------------------------------------------------------------------------
DEMO_SUPPLIERS = [
    # id, name, country, region, tier
    ("SUP-P10-01", "Demo Hydraulics Supplier A", "DE", "Europe", 1),
    ("SUP-P10-02", "Demo Hydraulics Supplier B", "IT", "Europe", 1),
    ("SUP-P10-03", "Demo Powertrain Supplier", "SE", "Europe", 1),
    ("SUP-P10-04", "Demo Undercarriage Supplier", "IT", "Europe", 1),
    ("SUP-P10-05", "Demo Electrical Supplier", "CZ", "Europe", 2),
    ("SUP-P10-06", "Demo Battery Supplier", "PL", "Europe", 2),
    ("SUP-P10-07", "Demo Lubricants Supplier", "BE", "Europe", 1),
    ("SUP-P10-08", "Demo Filtration & Coatings Supplier", "FR", "Europe", 2),
]
# part_category / part_subcategory keyword -> (primary supplier, optional second source)
# Checked in order — fluids first, so "Hydraulic oil" is a lubricant, not a hydraulic component.
COMMODITY_RULES = [
    (("radiator",), "SUP-P10-03", None),
    (("fluid", "oil", "grease", "coolant", "exhaust"), "SUP-P10-07", "SUP-P10-08"),
    (("battery",), "SUP-P10-06", None),
    (("hydraulic", "control valve", "solenoid", "breaker", "remanufactured"), "SUP-P10-01", "SUP-P10-02"),
    (("engine", "drivetrain", "travel motor", "swing", "axle", "cooling", "radiator", "air"), "SUP-P10-03", None),
    (("undercarriage", "roller", "sprocket"), "SUP-P10-04", "SUP-P10-03"),
    (("electrical", "alternator", "starter", "light", "control module", "performance", "cab"), "SUP-P10-05", None),
    (("filter", "paint", "general", "genuine part"), "SUP-P10-08", None),
]
PRIMARY_SHARES = [60, 70, 75, 85]


def plan_suppliers(s):
    parts = s.run("MATCH (p:Part) RETURN p.part_id AS id, p.part_category AS cat, p.part_subcategory AS sub ORDER BY id").data()
    links = []
    for p in parts:
        text = f"{p['cat']} {p['sub']}".lower()
        primary, second = next(((a, b) for words, a, b in COMMODITY_RULES if any(w in text for w in words)),
                               ("SUP-P10-08", None))
        # Roughly half the parts that have a second source available are dual-sourced.
        if second and bucket(p["id"] + ":dual", 2) == 0:
            share = PRIMARY_SHARES[bucket(p["id"] + ":share", len(PRIMARY_SHARES))]
            links += [{"part_id": p["id"], "supplier_id": primary, "share_pct": share, "role": "PRIMARY"},
                      {"part_id": p["id"], "supplier_id": second, "share_pct": 100 - share, "role": "SECONDARY"}]
        else:
            links.append({"part_id": p["id"], "supplier_id": primary, "share_pct": 100, "role": "SOLE"})
    return links


def write_suppliers(s, rows):
    s.run(
        """UNWIND $sups AS x
           MERGE (su:Supplier {supplier_id: x[0]})
           SET su.name = x[1], su.country = x[2], su.region = x[3], su.tier = x[4],
               su.synthetic = true, su.data_source = 'SYNTHETIC_DEMO',
               su.record_class = 'DEMO_PART_SUPPLIER', su.note = $note""",
        sups=[list(x) for x in DEMO_SUPPLIERS], note=SEED_NOTE).consume()
    # Re-seed cleanly: drop this step's previous links before writing the plan.
    s.run("MATCH (:Part)-[l:SUPPLIED_BY]->(:Supplier {record_class: 'DEMO_PART_SUPPLIER'}) DELETE l").consume()
    return s.run(
        """UNWIND $rows AS r
           MATCH (p:Part {part_id: r.part_id}), (su:Supplier {supplier_id: r.supplier_id})
           MERGE (p)-[l:SUPPLIED_BY]->(su)
           SET l.share_pct = r.share_pct, l.role = r.role,
               l.synthetic = true, l.data_source = 'SYNTHETIC_DEMO'
           RETURN count(l) AS n""", rows=rows).single()["n"]


# ---------------------------------------------------------------------------
# Task 8 — compliance: Assembly -[:REQUIRES_COMPLIANCE]-> ComplianceRequirement,
# Part -[:HAS_CERTIFICATION]-> ComplianceRequirement, and
# ComplianceRequirement -[:DEPENDS_ON]-> ComplianceRequirement.
# The regulations are real EU instruments; WHICH assembly requires which one
# and WHICH part holds which certificate is SYNTHETIC_DEMO. The one source-
# derived link (EU Battery Regulation on PT-001..003, SRC-039) is left untouched
# and counts as held.
# ---------------------------------------------------------------------------
NEW_REQUIREMENTS = [
    ("COMP-P10-REACH", "REACH Substance Compliance", "Regulation (EC) No 1907/2006", "European Commission / ECHA",
     "Registration and restriction of chemical substances in fluids, coatings and articles."),
    ("COMP-P10-CLP", "CLP Hazard Classification & Labelling", "Regulation (EC) No 1272/2008", "European Commission / ECHA",
     "Classification, labelling and packaging of hazardous mixtures such as oils, coolants and paints."),
]
DEPENDS_ON = [("COMP-P10-CLP", "COMP-P10-REACH"), ("COMP-EU-BATT-2023", "COMP-P10-REACH")]
# assembly-name keyword -> requirements that assembly imposes on every part inside it
ASSEMBLY_REQUIREMENTS = [
    (("engine", "fuel", "air intake"), ["COMP-DEMO-STAGE-V"]),
    (("hydraulic", "control valve", "solenoid", "breaker", "swing", "final drive", "axle",
      "undercarriage", "track roller", "carrier roller", "sprocket", "major components"), ["COMP-DEMO-CE-MACHINERY"]),
    (("ecm", "alternator", "starter", "light", "electrical"), ["COMP-DEMO-EMC-24V"]),
    (("electrical",), ["COMP-EU-BATT-2023"]),
    (("hydraulic system", "engine", "axle", "transmission", "grease", "exterior", "cooling"),
     ["COMP-P10-REACH", "COMP-P10-CLP"]),
]


def plan_compliance(s):
    asm = s.run("MATCH (a:Assembly)-[:CONTAINS_PART]->(p:Part) RETURN a.assembly_id AS a, a.name AS name, p.part_id AS p").data()
    requires, needed = set(), set()
    for r in asm:
        n = r["name"].lower()
        for words, reqs in ASSEMBLY_REQUIREMENTS:
            if any(w in n for w in words):
                for c in reqs:
                    requires.add((r["a"], c))
                    needed.add((r["p"], c))
    # ~1 in 6 (part, requirement) pairs has no certificate on record -> a gap.
    certs = sorted((p, c) for p, c in needed if bucket(p + c + ":cert", 6) != 0)
    return {"requires": sorted(requires), "certs": certs}


def write_compliance(s, plan):
    s.run("""UNWIND $reqs AS x
             MERGE (c:ComplianceRequirement {compliance_id: x[0]})
             SET c.name = x[1], c.regulation_standard = x[2], c.issuing_body = x[3], c.description = x[4],
                 c.requirement_type = 'REGULATION', c.synthetic = true, c.data_source = 'SYNTHETIC_DEMO',
                 c.note = 'Real EU regulation; its applicability to parts in this graph is SYNTHETIC_DEMO.'""",
          reqs=[list(x) for x in NEW_REQUIREMENTS]).consume()
    s.run("""UNWIND $deps AS d MATCH (a:ComplianceRequirement {compliance_id: d[0]}), (b:ComplianceRequirement {compliance_id: d[1]})
             MERGE (a)-[r:DEPENDS_ON]->(b) SET r.synthetic = true, r.data_source = 'SYNTHETIC_DEMO'""",
          deps=[list(d) for d in DEPENDS_ON]).consume()
    n = s.run("""UNWIND $rows AS x MATCH (a:Assembly {assembly_id: x[0]}), (c:ComplianceRequirement {compliance_id: x[1]})
                 MERGE (a)-[r:REQUIRES_COMPLIANCE]->(c) SET r.synthetic = true, r.data_source = 'SYNTHETIC_DEMO'
                 RETURN count(r) AS n""", rows=[list(x) for x in plan["requires"]]).single()["n"]
    m = s.run("""UNWIND $rows AS x MATCH (p:Part {part_id: x[0]}), (c:ComplianceRequirement {compliance_id: x[1]})
                 WHERE NOT (p)-[:HAS_COMPLIANCE_REQUIREMENT]->(c)
                 MERGE (p)-[r:HAS_CERTIFICATION]->(c) SET r.synthetic = true, r.data_source = 'SYNTHETIC_DEMO'
                 RETURN count(r) AS n""", rows=[list(x) for x in plan["certs"]]).single()["n"]
    return n + m


STEPS = {"inventory": (plan_inventory, write_inventory), "bom": (plan_bom, write_bom),
         "suppliers": (plan_suppliers, write_suppliers), "compliance": (plan_compliance, write_compliance)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=sorted(STEPS))
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    plan, write = STEPS[args.step]

    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with driver.session(database=os.environ.get("NEO4J_DATABASE") or None) as s:
        rows = plan(s)
        if isinstance(rows, dict):
            print("  ", {k: len(v) for k, v in rows.items()})
        else:
            for r in rows[:8]:
                print("  ", r)
            if len(rows) > 8:
                print(f"   ... {len(rows) - 8} more")
        if args.execute:
            print(f"APPLIED  {write(s, rows)} record(s) for step '{args.step}'")
        else:
            print(f"DRY-RUN  {len(rows)} record(s) would be written for step '{args.step}'")
    driver.close()


if __name__ == "__main__":
    main()
