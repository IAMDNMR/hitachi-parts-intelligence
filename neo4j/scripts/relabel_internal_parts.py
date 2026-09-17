#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Two corrections for PT-044..PT-048 (5 internally-added, AI-illustrated Parts
Store products — kept at the user's explicit request):

1. PROVENANCE (already applied by an earlier run of this script — re-running
   is a harmless no-op for this part): these 5 parts and their fitment were
   originally written with Data Class "OFFICIAL WEBSITE DATA" and a Source
   ID (SRC-040) that never existed in provenance.csv. Corrected to Data
   Class "INTERNALLY GENERATED DATA", Source ID "SRC-048" (a real,
   honestly-described new provenance.csv row), Confidence "LOW".

2. MACHINE LINKS (this run's actual work): the fitment was originally
   written against machine_ids that do NOT match the models the parts were
   described as fitting. Verified directly against machines.csv:

     claimed model   machine_id used   that machine_id's REAL model
     ZX210LC-7       MC-027            ZX890LCH-7
     ZX225USR-7      MC-029            ZX135-7EB
     ZX250LC-7       MC-030            ZX135US-7B
     ZX300LC-7       MC-032            ZX180-7
     ZX350-7G        MC-033            ZX210LC-7   (this one happens to BE
                                                     a real machine, just not
                                                     the one that was meant)
     ZX375US-7       MC-034            ZX220LC-GI
     ZX350LC-7       MC-035            ZX225US-7

   The correct machine_id for each originally-intended model, found by
   searching machines.csv directly:

     ZX210LC-7  -> MC-033      ZX300LC-7  -> MC-038
     ZX225USR-7 -> MC-036      ZX350-7G   -> MC-039
     ZX250LC-7  -> MC-037      ZX375US-7  -> MC-041
                                ZX350LC-7  -> MC-040

   This script removes the wrong fitment for these 5 parts (both in
   machine_part_fitment.csv and in the live Aura relationships) and
   recreates it against the correct 7 machines, with the same honest
   (non-official) provenance as before. It does not touch any other part,
   any other machine, or the original 45-part catalogue.
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
NEW_SOURCE_ID = "SRC-048"
NEW_CONFIDENCE = "LOW"
TODAY = "2026-09-17"

PART_IDS = ["PT-044", "PT-045", "PT-046", "PT-047", "PT-048"]

PARTS_BY_ID = {
    "PT-044": {"Part Number": "4719002", "Part Name": "Hitachi OEM Main Control Valve Block Assembly",
               "Component / Assembly": "Main Control Valve (installed in Upperstructure)"},
    "PT-045": {"Part Number": "4658321", "Part Name": "Hitachi OEM Dual Axial Piston Main Hydraulic Pump",
               "Component / Assembly": "Main Hydraulic Pump (installed in Upperstructure)"},
    "PT-046": {"Part Number": "4621008", "Part Name": "Hitachi OEM Stage V Industrial Diesel Engine Assembly",
               "Component / Assembly": "Diesel Engine Unit"},
    "PT-047": {"Part Number": "4398110", "Part Name": "Hitachi OEM Slewing Ring / Swing Bearing Assembly",
               "Component / Assembly": "Swing Bearing Assembly"},
    "PT-048": {"Part Number": "9265430", "Part Name": "Hitachi OEM Final Drive Travel Motor & Gearbox",
               "Component / Assembly": "Final Drive Motor"},
}

# The correct machine_id for each originally-intended model — verified
# against neo4j/data/machines.csv, not assumed.
CORRECT_MACHINE_IDS = ["MC-033", "MC-036", "MC-037", "MC-038", "MC-039", "MC-040", "MC-041"]


def real_machine_models():
    with open(DATA / "machines.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["Machine ID"]: r["Model"] for r in rows}


def update_provenance():
    path = DATA / "provenance.csv"
    with open(path, encoding="utf-8") as f:
        existing_ids = {r["Source ID"] for r in csv.DictReader(f)}
    if NEW_SOURCE_ID in existing_ids:
        print(f"{NEW_SOURCE_ID} already present in provenance.csv — skipping.")
        return
    with open(path, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow([
            NEW_SOURCE_ID, "Internal (HCME After-Sales Parts Store)",
            "Internally generated / AI-illustrated — not an HCME publication",
            "N/A — not sourced from a published HCME page", "Zaxis-7 Excavators",
            "Parts catalogue — internally added concept components", TODAY, "No",
        ])
    print(f"Added {NEW_SOURCE_ID} to provenance.csv.")


def fix_fitment_csv():
    path = DATA / "machine_part_fitment.csv"
    models = real_machine_models()
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    kept = [r for r in rows if r["Part ID"] not in PART_IDS]
    removed = len(rows) - len(kept)

    next_idx = max(int(r["Fitment ID"].split("-")[1]) for r in kept) + 1
    new_rows = []
    for pid in PART_IDS:
        p = PARTS_BY_ID[pid]
        for mid in CORRECT_MACHINE_IDS:
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

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)
        writer.writerows(new_rows)
    print(f"machine_part_fitment.csv: removed {removed} incorrect row(s), added {len(new_rows)} correct row(s) "
          f"({len(PART_IDS)} parts x {len(CORRECT_MACHINE_IDS)} machines).")


def fix_aura():
    print("\nConnecting to Neo4j Aura...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    with driver.session(database=DATABASE) as session:
        # Part-level relabel (idempotent if already applied).
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
        print(f"  Deleted {deleted} incorrect HAS_PART_FITMENT relationship(s).")

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
        print(f"  Created {created} correct HAS_PART_FITMENT relationship(s).")

        after = session.run("""
            MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p:Part) WHERE p.part_id IN $ids
            RETURN DISTINCT m.machine_id AS mid, m.model AS model ORDER BY mid
        """, {"ids": PART_IDS}).data()
        print("\n  Verified current machines (after fix):")
        for r in after:
            print(f"    {r['mid']}: {r['model']}")
    driver.close()


if __name__ == "__main__":
    update_provenance()
    fix_fitment_csv()
    fix_aura()
