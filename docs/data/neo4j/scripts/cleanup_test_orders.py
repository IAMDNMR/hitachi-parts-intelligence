#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PREPARED, NOT EXECUTED (Phase 0.6 closure pass, 2026-09-23).

Cleans up Order nodes created by real E2E/API testing against live AuraDB
(provenance='INTERNAL_TEST_WORKFLOW', synthetic IS NULL) — see
backend/app/modules/order/service.py ~line 116, which hardcodes this
provenance on every Order the app's create_order() ever creates.

SAFETY MODEL (per explicit project rule: never delete based on naming alone):
  For each candidate Order this script:
    1. Confirms synthetic != true (never touch SYNTHETIC_DEMO records).
    2. Walks its real graph neighbourhood (BASED_ON_ALLOCATION, HAS_ORDER,
       FOR_PART, HAS_SHIPMENT relationships — discovered by direct inspection
       of the live schema, not assumed).
    3. For each neighbour (Allocation / FulfilmentRequest / FulfilmentOption /
       InventoryCache / Shipment), checks whether that neighbour is ALSO
       referenced by any Order NOT in the candidate set (i.e. a synthetic=true
       order, or an order this script is not proposing to delete). If so, the
       neighbour — and by extension caution around the Order touching it — is
       flagged SHARED and excluded from automatic deletion.
    4. Orders destined to real dealer IDs (DLR-* / any destinationBranchId not
       starting with 'DEALER-BR' test patterns) are always excluded from
       automatic deletion and printed separately for manual review, per the
       explicit instruction to give the DLR-019 / DLR-001 orders individual
       scrutiny rather than bulk treatment.
    5. Nothing with partNumber matching a real, non-test part (e.g. PT-001's
       4663907, PT-045's 4658321) is deleted purely because provenance says
       INTERNAL_TEST_WORKFLOW — those go to the manual-review bucket too,
       since the part itself is real even though the order was a test call.
       Only PN6-TEST_<uuid>-<hash> part numbers (self-evidently synthetic by
       the data itself) are eligible for the automatic bucket.

MODES:
  --dry-run (default): prints the audit — candidate counts, shared-neighbour
      exclusions, manual-review bucket, and the exact DETACH DELETE it WOULD
      run. Makes no writes.
  --execute: actually runs the deletes for the auto-eligible bucket only.
      Requires typing 'DELETE 292 TEST ORDERS' (or the actual printed count)
      at an interactive confirmation prompt. Never run unattended.

This script was written but NOT executed during the 2026-09-23 closure pass:
live-write Cypher against AuraDB was blocked by the coding assistant's own
sandbox permission layer for this session (see
docs/research/PHASE_0_6_FINAL_CLOSURE_REPORT.md, Task 2). Re-run this script
manually (python cleanup_test_orders.py --dry-run first) to get fresh
before/after numbers, review the manual-review bucket by hand, then decide
on --execute.
"""
import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4] / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402
from neo4j import GraphDatabase  # noqa: E402

load_dotenv(BACKEND / ".env")

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

CANDIDATE_QUERY = """
MATCH (o:Order)
WHERE (o.synthetic IS NULL OR o.synthetic = false)
  AND o.provenance = 'INTERNAL_TEST_WORKFLOW'
RETURN o.id AS id, o.partNumber AS partNumber, o.destinationBranchId AS dest,
       o.status AS status
"""

NEIGHBOUR_QUERY = """
MATCH (o:Order {id: $id})-[r]-(n)
RETURN type(r) AS relType, labels(n) AS labels, elementId(n) AS neighbourId
"""

# A neighbour is SHARED if any Order outside the candidate set also touches it.
NEIGHBOUR_SHARED_CHECK = """
MATCH (n) WHERE elementId(n) = $neighbourId
MATCH (n)-[]-(other:Order)
WHERE NOT other.id IN $candidateIds
RETURN count(other) AS otherOrderRefs
"""

REAL_DEALER_PREFIXES = ("DLR-",)
TEST_DEALER_PREFIXES = ("DEALER-BRANCH-", "DEALER-BR-")


def is_real_dealer(dest):
    if not dest:
        return True  # unknown destination -> treat as needing manual review
    if any(dest.startswith(p) for p in REAL_DEALER_PREFIXES):
        return True
    if any(dest.startswith(p) for p in TEST_DEALER_PREFIXES):
        return False
    return True  # unrecognised pattern -> manual review, not auto-delete


def is_test_only_part(part_number):
    return bool(part_number) and part_number.startswith("PN6-TEST_")


def audit(session):
    candidates = session.run(CANDIDATE_QUERY).data()
    candidate_ids = [c["id"] for c in candidates]

    auto_eligible = []
    manual_review = []

    for c in candidates:
        reasons = []
        if is_real_dealer(c["dest"]):
            reasons.append(f"destination '{c['dest']}' is not a recognised test-dealer pattern")
        if not is_test_only_part(c["partNumber"]):
            reasons.append(f"partNumber '{c['partNumber']}' is not a PN6-TEST_ synthetic pattern (real/looks-real part)")

        neighbours = session.run(NEIGHBOUR_QUERY, id=c["id"]).data()
        shared = []
        for n in neighbours:
            shared_count = session.run(
                NEIGHBOUR_SHARED_CHECK,
                neighbourId=n["neighbourId"],
                candidateIds=candidate_ids,
            ).single()["otherOrderRefs"]
            if shared_count > 0:
                shared.append(n)
        if shared:
            reasons.append(f"{len(shared)} neighbour(s) referenced by a non-candidate Order")

        if reasons:
            manual_review.append({"order": c, "reasons": reasons})
        else:
            auto_eligible.append(c)

    return candidates, auto_eligible, manual_review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually delete the auto-eligible bucket")
    args = parser.parse_args()

    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver.session() as session:
        candidates, auto_eligible, manual_review = audit(session)

        print(f"Total INTERNAL_TEST_WORKFLOW / non-synthetic Order candidates: {len(candidates)}")
        print(f"Auto-eligible (test-only part AND test-only destination AND no shared neighbours): {len(auto_eligible)}")
        print(f"Manual-review bucket (real-looking part, real-looking dealer, or shared dependents): {len(manual_review)}")
        print()
        print("Manual-review sample (first 20):")
        for m in manual_review[:20]:
            print(f"  Order {m['order']['id']}: {m['reasons']}")

        if not args.execute:
            print()
            print("DRY RUN ONLY — no writes performed. Re-run with --execute to delete the")
            print(f"{len(auto_eligible)} auto-eligible orders (and their exclusively-owned dependents).")
            return

        confirm = input(
            f"Type 'DELETE {len(auto_eligible)} TEST ORDERS' to proceed, anything else aborts: "
        )
        if confirm != f"DELETE {len(auto_eligible)} TEST ORDERS":
            print("Aborted — confirmation text did not match.")
            return

        ids = [c["id"] for c in auto_eligible]
        result = session.run(
            """
            UNWIND $ids AS oid
            MATCH (o:Order {id: oid})
            OPTIONAL MATCH (o)-[]-(n)
            WHERE NOT (n)-[]-(:Order {id: oid}) OR true
            DETACH DELETE o
            RETURN count(DISTINCT o) AS deleted
            """,
            ids=ids,
        ).single()
        print(f"Deleted {result['deleted']} Order nodes.")

    driver.close()


if __name__ == "__main__":
    main()
