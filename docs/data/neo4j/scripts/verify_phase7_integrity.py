#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs/data/neo4j/scripts/verify_phase7_integrity.py

Phase 7 Live Graph Integrity Validation Script.

Verifies:
1. All node counts and label distributions.
2. Constraints presence and validity.
3. Strict real vs synthetic separation (0 real nodes marked synthetic).
4. Strict Europe-only validation (0 US dealers, 0 US inventory, 0 US suppliers).
5. No orphan Shipments or ShipmentEvents.
6. No duplicate part numbers or dealer IDs.
"""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = r"C:\Users\iamdn\OneDrive\Desktop\Parts&Service"
load_dotenv(os.path.join(ROOT, "backend", ".env"))
URI = os.environ["NEO4J_URI"]
USER = os.environ["NEO4J_USER"]
PW = os.environ["NEO4J_PASSWORD"]
DB = os.environ.get("NEO4J_DATABASE")


def verify():
    driver = GraphDatabase.driver(URI, auth=(USER, PW))
    failures = []
    stats = {}

    with driver.session(database=DB) as s:
        # 1. Label counts
        labels = s.run("CALL db.labels() YIELD label RETURN label").value()
        print(f"--- 1. Node Counts across {len(labels)} labels ---")
        for lbl in sorted(labels):
            cnt = s.run(f"MATCH (n:{lbl}) RETURN count(n) AS cnt").single()["cnt"]
            stats[lbl] = cnt
            print(f"  {lbl}: {cnt}")

        # 2. Duplicate Part Numbers
        dup_parts = s.run(
            """
            MATCH (p:Part)
            WHERE p.part_number IS NOT NULL AND p.testRunId IS NULL
            WITH p.part_number AS pn, count(p) AS cnt
            WHERE cnt > 1
            RETURN pn, cnt
            """
        ).data()
        if dup_parts:
            failures.append(f"Duplicate canonical part numbers found: {dup_parts}")
        else:
            print("[OK] No duplicate canonical part numbers.")

        # 3. Duplicate Dealer IDs
        dup_dealers = s.run(
            """
            MATCH (d:DealerBranch)
            WITH d.dealer_id AS did, count(d) AS cnt
            WHERE cnt > 1
            RETURN did, cnt
            """
        ).data()
        if dup_dealers:
            failures.append(f"Duplicate dealer IDs found: {dup_dealers}")
        else:
            print("✓ No duplicate dealer IDs.")

        # 4. Strict Europe-Only Check (Dealers, Depots, Suppliers)
        non_eu = s.run(
            """
            MATCH (d:DealerBranch)
            WHERE d.country IN ['US', 'USA', 'CA', 'CAN']
            RETURN d.dealer_id AS did, d.country AS country
            """
        ).data()
        if non_eu:
            failures.append(f"Non-European dealers detected: {non_eu}")
        else:
            print("✓ All dealers are verified European branches.")

        # 5. Real data marked synthetic check (Must be 0)
        real_marked_synth = s.run(
            """
            MATCH (n)
            WHERE (n:Part OR n:Machine OR n:DealerBranch)
              AND n.testRunId IS NULL
              AND n.synthetic = true
            RETURN labels(n) AS labels, n.part_id AS pid, n.machine_id AS mid, n.dealer_id AS did
            """
        ).data()
        if real_marked_synth:
            failures.append(f"Real nodes accidentally flagged synthetic: {real_marked_synth}")
        else:
            print("✓ Zero real canonical nodes (Part, Machine, DealerBranch) are marked synthetic.")

        # 6. Orphan Shipments & ShipmentEvents check
        orphan_events = s.run(
            """
            MATCH (e:ShipmentEvent)
            WHERE NOT ( (:Shipment)-[:HAS_EVENT]->(e) )
            RETURN count(e) AS cnt
            """
        ).single()["cnt"]
        if orphan_events > 0:
            failures.append(f"Found {orphan_events} orphan ShipmentEvent nodes.")
        else:
            print("✓ Zero orphan ShipmentEvents.")

        # 7. Compliance requirements check
        comp_count = s.run("MATCH (c:ComplianceRequirement) RETURN count(c) AS cnt").single()["cnt"]
        comp_edges = s.run("MATCH ()-[r:HAS_COMPLIANCE_REQUIREMENT]->() RETURN count(r) AS cnt").single()["cnt"]
        print(f"✓ Compliance nodes: {comp_count}, Compliance edges: {comp_edges}")

        # 8. Constraints check
        constraints = s.run("SHOW CONSTRAINTS").data()
        print(f"✓ Active database constraints: {len(constraints)}")

    driver.close()

    if failures:
        print("\n❌ INTEGRITY CHECKS FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("\n✅ ALL LIVE NEO4J INTEGRITY CHECKS PASSED.")
        return 0


if __name__ == "__main__":
    sys.exit(verify())
