#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Same correction as relabel_internal_parts.py, for a second batch (PT-049..
PT-053) that reached the live Aura database labelled "OFFICIAL WEBSITE
DATA" / a fabricated Source ID (SRC-041) that never existed in
provenance.csv, via a script (neo4j/scripts/sync_batch2_parts.py, since
removed) that was never reviewed. This one never reached the local CSV
mirror or frontend/data/partsStoreCatalogue.js — verified directly, both
were still clean — so this script only has live Aura to correct; it also
adds PT-049..053 to the local CSV mirror for the first time, since they
were kept (same decision as the first batch) but never actually recorded
there.

Also carries the same machine-link correction as batch 1: 4 of the 7
linked machine_ids did not match the models the parts were described as
fitting (verified against machines.csv):

  claimed model   machine_id used   real model of that machine_id
  ZX210LC-7       MC-027            ZX890LCH-7
  ZX250LC-7       MC-030            ZX135US-7B
  ZX300LC-7       MC-032            ZX180-7
  ZX350LC-7       MC-035            ZX225US-7
  ZW180-7         MC-066            ZW180-7   (already correct)
  ZW220-7         MC-067            ZW220-7   (already correct)
  ZW310-7         MC-069            ZW310-7   (already correct)

Correct machine_id for each intended model, found in machines.csv:
  ZX210LC-7 -> MC-033   ZX300LC-7 -> MC-038
  ZX250LC-7 -> MC-037   ZX350LC-7 -> MC-040
"""

import csv
import os
from pathlib import Path
from dotenv import load_dotenv
import certifi
from neo4j import GraphDatabase

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "neo4j" / "data"
ENV = ROOT / "neo4j" / ".env"

load_dotenv(ENV)
URI = os.environ["NEO4J_URI"]
USERNAME = os.environ["NEO4J_USERNAME"]
PASSWORD = os.environ["NEO4J_PASSWORD"]
DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

NEW_DATA_CLASS = "INTERNALLY GENERATED DATA"
NEW_SOURCE_ID = "SRC-048"  # same real provenance row batch 1 added
NEW_CONFIDENCE = "LOW"
TODAY = "2026-09-18"

PART_IDS = ["PT-049", "PT-050", "PT-051", "PT-052", "PT-053"]

PARTS_BY_ID = {
    "PT-049": {"Part Number": "4683058", "Part Name": "Hitachi OEM Electronic Control Module (ECM / Main Controller)",
               "Part Category": "Electrical", "Part Subcategory": "Electronic Control Module",
               "Component / Assembly": "Main ECM Unit (installed in Cab / Upperstructure)",
               "Description": "Heavy aluminum heatsink sealed main engine and machine control unit with multi-pin waterproof Deutsch harness connectors. Runs Z-7 control software and ConSite telematics processing.",
               "Wear Part": "No"},
    "PT-050": {"Part Number": "4679860", "Part Name": "Hitachi OEM Multi-Station Solenoid Valve Manifold Bank",
               "Part Category": "Electrical", "Part Subcategory": "Solenoid Valve",
               "Component / Assembly": "Solenoid Valve Manifold (installed in Upperstructure)",
               "Description": "Precision machined electro-hydraulic solenoid valve block with 24V gold-plated coils and auxiliary pilot control lines. Regulates pilot signal pressures for boom, arm, and hydraulic quick coupler.",
               "Wear Part": "No"},
    "PT-051": {"Part Number": "4465700", "Part Name": "Hitachi OEM Forged Dual-Flange Lower Track Roller Assembly",
               "Part Category": "Undercarriage", "Part Subcategory": "Track Roller",
               "Component / Assembly": "Lower Track Roller (installed in Track Frame)",
               "Description": "Forged alloy steel dual-flange track roller with induction-hardened tread surfaces and lifetime duo-cone seals. Supports excavator machine weight across crawler track links.",
               "Wear Part": "Yes"},
    "PT-052": {"Part Number": "4600500", "Part Name": "Hitachi OEM Heavy Hydraulic Demolition Breaker Attachment",
               "Part Category": "Attachments", "Part Subcategory": "Hydraulic Breaker",
               "Component / Assembly": "Demolition Breaker Attachment",
               "Description": "Heavy hydraulic rock and concrete demolition hammer featuring noise-dampened orange housing, forged steel chisel tool bit, and high-impact energy cell.",
               "Wear Part": "Yes"},
    "PT-053": {"Part Number": "3065785", "Part Name": "Hitachi OEM ZW-Series Heavy Wheel Loader Axle Assembly",
               "Part Category": "Drivetrain", "Part Subcategory": "Axle Assembly",
               "Component / Assembly": "Front Axle Assembly (installed in Frame)",
               "Description": "Heavy-duty front drive axle with internal torque-proportioning differential and wet multi-disc brake system. Engineered for high breakout force on ZW wheel loaders.",
               "Wear Part": "Yes"},
}

CORRECT_MACHINE_IDS = ["MC-033", "MC-037", "MC-038", "MC-040", "MC-066", "MC-067", "MC-069"]


def real_machine_models():
    with open(DATA / "machines.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["Machine ID"]: r["Model"] for r in rows}


def add_parts_csv():
    path = DATA / "parts.csv"
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        existing_ids = {r["Part ID"] for r in reader}
    to_add = [pid for pid in PART_IDS if pid not in existing_ids]
    if not to_add:
        print("parts.csv already has PT-049..053 — skipping.")
        return
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for pid in to_add:
            p = PARTS_BY_ID[pid]
            writer.writerow({
                "Part ID": pid, "Part Number": p["Part Number"], "Part Name": p["Part Name"],
                "Part Category": p["Part Category"], "Part Subcategory": p["Part Subcategory"],
                "Component / Assembly": p["Component / Assembly"],
                "Genuine Hitachi Part": "Yes", "Consumable": "No", "Wear Part": p["Wear Part"],
                "Replacement Part": "Yes", "Service Part": "Yes", "Attachment Part": "No",
                "Description": p["Description"], "Supersedes Part Number": "", "Superseded By": "",
                "Data Class": NEW_DATA_CLASS, "Source ID": NEW_SOURCE_ID, "Confidence": NEW_CONFIDENCE,
                "Source Date": TODAY, "record_class": "ORDERABLE_OEM_PART",
            })
    print(f"Added {len(to_add)} part(s) to parts.csv.")


def add_fitment_csv():
    path = DATA / "machine_part_fitment.csv"
    models = real_machine_models()
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    existing_pairs = {(r["Machine ID"], r["Part ID"]) for r in rows}
    next_idx = max(int(r["Fitment ID"].split("-")[1]) for r in rows) + 1

    new_rows = []
    for pid in PART_IDS:
        p = PARTS_BY_ID[pid]
        for mid in CORRECT_MACHINE_IDS:
            if (mid, pid) in existing_pairs:
                continue
            model = models[mid]
            new_rows.append({
                "Fitment ID": f"FIT-{next_idx:04d}", "Machine ID": mid, "Machine Model": model,
                "Part ID": pid, "Part Number": p["Part Number"], "Part Name": p["Part Name"],
                "Assembly": p["Component / Assembly"], "Fitment Type": "Replacement",
                "Compatibility": "Model range (internally added)",
                "Installation Context": "Machine build / replacement",
                "Position / Location": p["Component / Assembly"],
                "Data Class": NEW_DATA_CLASS, "Source ID": NEW_SOURCE_ID, "Confidence": NEW_CONFIDENCE,
                "Source Date": TODAY,
                "evidence_original": f"Internally added fitment for {model} (not independently verified, not officially sourced)",
                "evidence": "MODEL_RANGE",
            })
            next_idx += 1

    if not new_rows:
        print("machine_part_fitment.csv already has these rows — skipping.")
        return
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerows(new_rows)
    print(f"Added {len(new_rows)} fitment row(s) to machine_part_fitment.csv.")


def fix_aura():
    print("\nConnecting to Neo4j Aura...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    with driver.session(database=DATABASE) as session:
        session.run("""
            MATCH (p:Part) WHERE p.part_id IN $ids
            SET p.data_class = $dc, p.source_id = $src, p.confidence = $conf
        """, {"ids": PART_IDS, "dc": NEW_DATA_CLASS, "src": NEW_SOURCE_ID, "conf": NEW_CONFIDENCE})

        before = session.run("""
            MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p:Part) WHERE p.part_id IN $ids
            RETURN DISTINCT m.machine_id AS mid, m.model AS model ORDER BY mid
        """, {"ids": PART_IDS}).data()
        print("  Currently linked machines (before fix):")
        for r in before:
            print(f"    {r['mid']}: {r['model']}")

        deleted = session.run("""
            MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p:Part) WHERE p.part_id IN $ids
            DELETE r RETURN count(r) AS n
        """, {"ids": PART_IDS}).single()["n"]
        print(f"  Deleted {deleted} relationship(s).")

        created = 0
        for pid in PART_IDS:
            p = PARTS_BY_ID[pid]
            for mid in CORRECT_MACHINE_IDS:
                session.run("""
                    MATCH (m:Machine {machine_id: $mid})
                    MATCH (p:Part {part_id: $pid})
                    MERGE (m)-[r:HAS_PART_FITMENT {fitment_id: $fit_id}]->(p)
                    SET r.evidence = 'MODEL_RANGE',
                        r.evidence_original = $evidence_orig,
                        r.fitment_type = 'Replacement',
                        r.assembly = $assembly,
                        r.data_class = $dc,
                        r.source_id = $src,
                        r.confidence = $conf
                """, {
                    "mid": mid, "pid": pid, "fit_id": f"FIT_INTERNAL_{mid}_{pid}",
                    "evidence_orig": f"Internally added fitment for {mid} (not independently verified, not officially sourced)",
                    "assembly": p["Component / Assembly"],
                    "dc": NEW_DATA_CLASS, "src": NEW_SOURCE_ID, "conf": NEW_CONFIDENCE,
                })
                created += 1
        print(f"  Created {created} correct relationship(s).")

        after = session.run("""
            MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p:Part) WHERE p.part_id IN $ids
            RETURN DISTINCT m.machine_id AS mid, m.model AS model ORDER BY mid
        """, {"ids": PART_IDS}).data()
        print("\n  Verified current machines (after fix):")
        for r in after:
            print(f"    {r['mid']}: {r['model']}")

        after_parts = session.run("""
            MATCH (p:Part) WHERE p.part_id IN $ids
            RETURN p.part_id AS id, p.data_class AS dc, p.source_id AS src, p.confidence AS conf ORDER BY id
        """, {"ids": PART_IDS}).data()
        print("\n  Verified current Part labels:")
        for r in after_parts:
            print(f"    {r['id']}: data_class={r['dc']!r} source_id={r['src']!r} confidence={r['conf']!r}")
    driver.close()


if __name__ == "__main__":
    add_parts_csv()
    add_fitment_csv()
    fix_aura()
