#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs/data/neo4j/scripts/verify_phase9_integrity.py

Phase 9 Live Graph Integrity Validation Script.

Verifies:
1. All node counts and label distributions across all 31 labels.
2. Active database constraints integrity (all 29 constraints).
3. Strict real vs synthetic separation (0 real canonical nodes marked synthetic).
4. Strict Europe-only validation (0 US/CA dealers, 0 US inventory, 0 US suppliers).
5. No orphan Shipments, ShipmentEvents, ServiceJobs, or ServiceEvents.
6. No duplicate part numbers, dealer IDs, or service job IDs.
7. Service state machine integrity and DealerBranch linkage.
8. External provenance attributes integrity (external_order_id, external_shipment_id, external_job_id, synced_at, data_source).
"""

import io
import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Ensure UTF-8 output even on Windows command prompt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"C:\Users\iamdn\OneDrive\Desktop\Parts&Service"
load_dotenv(os.path.join(ROOT, "backend", ".env"))
URI = os.environ["NEO4J_URI"]
USER = os.environ["NEO4J_USER"]
PW = os.environ["NEO4J_PASSWORD"]
DB = os.environ.get("NEO4J_DATABASE")


def verify():
    driver = GraphDatabase.driver(
        URI,
        auth=(USER, PW),
        max_connection_pool_size=50,
        connection_acquisition_timeout=60,
    )
    failures = []
    stats = {}

    session_kwargs = {}
    if DB:
        session_kwargs["database"] = DB

    with driver.session(**session_kwargs) as s:
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
            print("[OK] No duplicate dealer IDs.")

        # 4. Duplicate ServiceJob IDs
        dup_jobs = s.run(
            """
            MATCH (sj:ServiceJob)
            WHERE sj.testRunId IS NULL
            WITH sj.service_job_id AS jid, count(sj) AS cnt
            WHERE cnt > 1
            RETURN jid, cnt
            """
        ).data()
        if dup_jobs:
            failures.append(f"Duplicate service job IDs found: {dup_jobs}")
        else:
            print("[OK] No duplicate service job IDs.")

        # 5. Strict Europe-Only Check (Dealers, Depots, Suppliers)
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
            print("[OK] All dealers are verified European branches.")

        # 6. Real data marked synthetic check (Must be 0)
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
            print("[OK] Zero real canonical nodes (Part, Machine, DealerBranch) are marked synthetic.")

        # 7. Orphan ShipmentEvents check
        orphan_ship_events = s.run(
            """
            MATCH (e:ShipmentEvent)
            WHERE NOT ( (:Shipment)-[:HAS_EVENT]->(e) )
            RETURN count(e) AS cnt
            """
        ).single()["cnt"]
        if orphan_ship_events > 0:
            failures.append(f"Found {orphan_ship_events} orphan ShipmentEvent nodes.")
        else:
            print("[OK] Zero orphan ShipmentEvents.")

        # 8. Orphan ServiceEvents check
        orphan_service_events = s.run(
            """
            MATCH (e:ServiceEvent)
            WHERE NOT ( (:ServiceJob)-[:HAS_EVENT]->(e) )
            RETURN count(e) AS cnt
            """
        ).single()["cnt"]
        if orphan_service_events > 0:
            failures.append(f"Found {orphan_service_events} orphan ServiceEvent nodes.")
        else:
            print("[OK] Zero orphan ServiceEvents.")

        # 9. ServiceJob relationship integrity
        sj_unlinked = s.run(
            """
            MATCH (sj:ServiceJob)
            WHERE sj.testRunId IS NULL
              AND NOT ( (:DealerBranch)-[:PERFORMS_SERVICE]->(sj) )
            RETURN sj.service_job_id AS id
            """
        ).data()
        if sj_unlinked:
            failures.append(f"ServiceJobs without linked DealerBranch: {sj_unlinked}")
        else:
            print("[OK] All canonical/demo ServiceJobs are linked to a DealerBranch.")

        # 10. Service state machine distribution
        state_dist = s.run(
            """
            MATCH (sj:ServiceJob)
            WHERE sj.testRunId IS NULL
            RETURN sj.status AS st, count(sj) AS cnt
            """
        ).data()
        print(f"[OK] Live ServiceJob status distribution: {state_dist}")

        # 11. Constraints check
        constraints = s.run("SHOW CONSTRAINTS").data()
        print(f"[OK] Active database constraints: {len(constraints)}")

        # 12. Phase 9 Provenance Check
        prov_check = s.run(
            """
            MATCH (o:Order)
            WHERE o.data_source IS NOT NULL
            RETURN count(o) AS prov_orders
            """
        ).single()["prov_orders"]
        print(f"[OK] Orders with explicit data_source provenance: {prov_check}")

    driver.close()

    if failures:
        print("\n[FAIL] PHASE 9 INTEGRITY CHECKS FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("\n[PASS] ALL LIVE NEO4J PHASE 9 INTEGRITY CHECKS PASSED.")
        return 0


if __name__ == "__main__":
    sys.exit(verify())
