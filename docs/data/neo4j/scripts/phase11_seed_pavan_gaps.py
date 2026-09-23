"""
Phase 11 - HCME Parts Intelligence data additions. Scope was deliberately narrowed to what HCME data supports; Pavan's
demo is a reference for the approach only (see docs/research/PHASE_11_HCME_PARTS_INTELLIGENCE_FIT.md).

Steps (idempotent, dry-run by default, --execute writes):
  cleanup     remove the first-pass demo fixtures that HCME does not need: connector parts PT-901..904 (automotive-style pin/IP
              attributes) and the six demo customers + OPERATES edges (no real installed-base data exists), plus any
              tech_* attribute that is not stated in a real part name
  attrs       voltage/current that ARE stated in real HCME part names (PT-054 24V, PT-055 24V, PT-056 24V/100A) -> tech_* fields,
              tech_attrs_source = 'SOURCE_DERIVED'.  Nothing is invented.
  expiry      valid_until on Part -[:HAS_CERTIFICATION]-> so certificate expiry is testable (SYNTHETIC_DEMO, labelled)
  embeddings  local embedding of every catalogue Part (real fields only) + vector index
  all         cleanup, phase-10 bom/compliance/suppliers/inventory reseed, attrs, expiry, embeddings
"""
import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[4]
load_dotenv(ROOT / "backend" / ".env")
sys.path.insert(0, str(ROOT / "backend"))

REAL_NAME_ATTRS = {  # stated in the real HCME part name
    "PT-054": {"voltage_v": 24},
    "PT-055": {"voltage_v": 24},
    "PT-056": {"voltage_v": 24, "current_a": 100},
}
TECH_PROPS = ["tech_voltage_v", "tech_current_a", "tech_pin_count", "tech_ip_rating", "tech_temp_min_c", "tech_temp_max_c",
              "tech_capacity_ah", "tech_material", "tech_connector_type", "tech_attrs_source"]


def bucket(key: str, n: int) -> int:
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16) % n


def cleanup_step(s, execute):
    parts = s.run("MATCH (p:Part) WHERE p.part_id IN ['PT-901','PT-902','PT-903','PT-904'] RETURN count(p) AS n").single()["n"]
    cust = s.run("MATCH (c:Customer) WHERE c.customer_id STARTS WITH 'CUST-DEMO-' RETURN count(c) AS n").single()["n"]
    print(f"cleanup: {parts} demo connector parts, {cust} demo customers to remove; tech_* reset on all parts")
    if not execute:
        return
    s.run("MATCH (p:Part) WHERE p.part_id IN ['PT-901','PT-902','PT-903','PT-904'] DETACH DELETE p").consume()
    s.run("MATCH (c:Customer) WHERE c.customer_id STARTS WITH 'CUST-DEMO-' DETACH DELETE c").consume()
    s.run("MATCH (a:Assembly) WHERE NOT (a)-[:CONTAINS_PART]->(:Part) DETACH DELETE a").consume()
    s.run("MATCH (i:InventorySnapshot) WHERE NOT (:Part)-[:HAS_SYNTHETIC_INVENTORY]->(i) AND i.data_source = 'SYNTHETIC_DEMO' DETACH DELETE i").consume()
    s.run("MATCH (p:Part) REMOVE " + ", ".join(f"p.{k}" for k in TECH_PROPS)).consume()


def attrs_step(s, execute):
    for pid, a in REAL_NAME_ATTRS.items():
        print(f"attrs: {pid} {a} (stated in the real part name)")
        if execute:
            s.run("MATCH (p:Part {part_id:$id}) SET p += $props, p.tech_attrs_source='SOURCE_DERIVED'",
                  id=pid, props={f"tech_{k}": v for k, v in a.items()}).consume()


def expiry_step(s, execute):
    rows = s.run("MATCH (p:Part)-[:HAS_CERTIFICATION]->(c:ComplianceRequirement) RETURN p.part_id AS p, c.compliance_id AS c").data()
    plan = []
    for r in rows:
        b = bucket(r["p"] + r["c"] + ":expiry", 10)
        plan.append((r["p"], r["c"], "2026-03-01" if b == 0 else "2026-11-15" if b == 1 else "2028-06-30"))
    print(f"expiry: {len(plan)} certificates - expired {sum(1 for x in plan if x[2] == '2026-03-01')}, "
          f"expiring {sum(1 for x in plan if x[2] == '2026-11-15')}, rest valid to 2028 (SYNTHETIC_DEMO)")
    if execute:
        s.run("""UNWIND $rows AS x MATCH (p:Part {part_id:x[0]})-[r:HAS_CERTIFICATION]->(c:ComplianceRequirement {compliance_id:x[1]})
                 SET r.valid_until=date(x[2]), r.valid_until_basis='SYNTHETIC_DEMO'""", rows=[list(x) for x in plan]).consume()


def embeddings_step(s, execute):
    from app.modules.intelligence import similarity
    print(f"embeddings: wrote {similarity.write_embeddings(s)} part embeddings + vector index" if execute else "embeddings: would embed every catalogue part")


def rerun_phase10(execute):
    for step in ("bom", "compliance", "suppliers", "inventory"):
        cmd = [sys.executable, str(Path(__file__).with_name("seed_phase10_demo_data.py")), "--step", step] + (["--execute"] if execute else [])
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout.strip().splitlines()
        print(f"phase10 {step}: {out[-1] if out else ''}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["cleanup", "attrs", "expiry", "embeddings", "all"], default="all")
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    d = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with d.session(database=os.environ.get("NEO4J_DATABASE") or None) as s:
        on = lambda name: a.step in (name, "all")
        if on("cleanup"): cleanup_step(s, a.execute)
        if a.step == "all": rerun_phase10(a.execute)
        if on("attrs"): attrs_step(s, a.execute)
        if on("expiry"): expiry_step(s, a.execute)
        if on("embeddings"): embeddings_step(s, a.execute)
    print("APPLIED" if a.execute else "DRY RUN - pass --execute")


if __name__ == "__main__":
    main()
