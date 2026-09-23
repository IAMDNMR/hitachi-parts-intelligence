"""
Phase 10F - fill category-level fitment gaps from each part's OWN published applicability text.

Eight catalogue parts had no HAS_PART_FITMENT edge although their source description states which machines
they serve (e.g. PT-030 "Zaxis-3 and older models", PT-037 "Hitachi construction machinery"). The existing
fitment pattern for product-line parts (PT-029, PT-031) is a CATEGORY-level edge, so the same is applied here.
Nothing is invented: every edge cites the part's own source_id and states the applicability it was derived from.

Dry-run by default; --execute writes. Idempotent (MERGE on part+machine).
"""
import argparse, os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parents[4] / "backend" / ".env")

RULES = {  # part_id: (machine filter, stated applicability)
    "PT-021": ("true", "All Hitachi machines"),
    "PT-034": ("true", "Hitachi construction machinery"),
    "PT-037": ("true", "Hitachi construction machinery"),
    "PT-038": ("true", "Hitachi construction machinery"),
    "PT-039": ("true", "Hitachi construction machinery"),
    "PT-030": ("m.generation_series = 'Dash-3 series'", "Zaxis-3 and older models"),
    "PT-022": ("m.generation_series IN ['Dash-3 series','Dash-5 series']", "Older Hitachi machines"),
    "PT-041": ("m.power_source = 'Diesel' AND m.generation_series IN ['Dash-5 series','Dash-6 series','Dash-7 series']",
               "Machines with SCR systems (EU Stage IV / V)"),
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--execute", action="store_true"); a = ap.parse_args()
    d = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with d.session(database=os.environ.get("NEO4J_DATABASE") or None) as s:
        nxt = s.run("MATCH ()-[r:HAS_PART_FITMENT]->() RETURN max(toInteger(substring(r.fitment_id,4))) AS mx").single()["mx"] + 1
        for pid, (flt, stated) in RULES.items():
            ms = s.run(f"MATCH (m:Machine) WHERE {flt} RETURN m.machine_id AS id ORDER BY id").value()
            print(f"{pid}: {len(ms)} machines ({stated})")
            if not a.execute:
                continue
            for mid in ms:
                s.run("""MATCH (p:Part {part_id:$p}), (m:Machine {machine_id:$m})
                         MERGE (m)-[r:HAS_PART_FITMENT]->(p)
                         ON CREATE SET r.fitment_id=$fid, r.evidence='CATEGORY', r.confidence='MEDIUM',
                           r.data_class='DERIVED FROM OFFICIAL SOURCE', r.source_id=p.source_id,
                           r.evidence_original='Category-level (derived from stated applicability: '+$st+'; no per-model fitment is published)',
                           r.fitment_type='Maintenance', r.installation_context='Scheduled maintenance / service',
                           r.assembly=coalesce(p.component_assembly,'General')""",
                      p=pid, m=mid, fid=f"FIT-{nxt:04d}", st=stated).consume()
                nxt += 1
        if a.execute:
            s.run("MATCH (p:Part {part_id:'PT-022'}) SET p.part_name='Hitachi Genuine Parts (older machines)'").consume()
            print("APPLIED")
        else:
            print("DRY RUN - pass --execute")

if __name__ == "__main__":
    main()
