"""
backend/scripts/db_hygiene.py

Neo4j AuraDB Data Hygiene & Cleanup Script (Phase 11)
- Identifies and deletes any orphaned testRunId nodes.
- Audits and verifies node and relationship counts.
"""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)

from app.db.neo4j.connection import get_neo4j_driver

def run_hygiene():
    driver = get_neo4j_driver()
    with driver.session() as s:
        # 1. Delete orphaned testRunId nodes
        res = s.run("MATCH (n) WHERE n.testRunId IS NOT NULL DETACH DELETE n").consume()
        print(f"Deleted orphaned test nodes: {res.counters.nodes_deleted}, Relationships deleted: {res.counters.relationships_deleted}")

        # 2. Count canonical nodes
        parts = s.run("MATCH (p:Part) RETURN count(p) AS cnt").single()["cnt"]
        canonical_parts = s.run("MATCH (p:Part) WHERE p.part_id STARTS WITH 'PT-' RETURN count(p) AS cnt").single()["cnt"]
        demo_parts = s.run("MATCH (p:Part) WHERE NOT p.part_id STARTS WITH 'PT-' RETURN count(p) AS cnt").single()["cnt"]
        dealers = s.run("MATCH (d:DealerBranch) RETURN count(d) AS cnt").single()["cnt"]
        dealers_gps = s.run("MATCH (d:DealerBranch) WHERE d.latitude IS NOT NULL RETURN count(d) AS cnt").single()["cnt"]
        dealers_no_gps = s.run("MATCH (d:DealerBranch) WHERE d.latitude IS NULL RETURN count(d) AS cnt").single()["cnt"]
        depots = s.run("MATCH (dp:Depot) RETURN count(dp) AS cnt").single()["cnt"]
        machines = s.run("MATCH (m:Machine) RETURN count(m) AS cnt").single()["cnt"]
        fitments = s.run("MATCH ()-[r:HAS_PART_FITMENT]->() RETURN count(r) AS cnt").single()["cnt"]
        test_nodes = s.run("MATCH (n) WHERE n.testRunId IS NOT NULL RETURN count(n) AS cnt").single()["cnt"]

        print("=" * 60)
        print("Neo4j AuraDB Hygiene Audit Report:")
        print(f"  Canonical Parts (PT-001..PT-060): {canonical_parts}")
        print(f"  Demo/Fixture Parts: {demo_parts}")
        print(f"  Total Part Nodes: {parts}")
        print(f"  Dealer Branches: {dealers} ({dealers_gps} with GPS, {dealers_no_gps} unmapped)")
        print(f"  Depots: {depots}")
        print(f"  Machines: {machines}")
        print(f"  Machine-Part Fitments: {fitments}")
        print(f"  Remaining testRunId Nodes: {test_nodes}")
        print("=" * 60)

if __name__ == "__main__":
    run_hygiene()
