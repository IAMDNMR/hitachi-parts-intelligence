#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 10 — controlled data fixes against live AuraDB.

Each step is one Phase 10 task. Default is a dry run that prints what would
change; --execute applies it. Re-run phase10_data_audit.py afterwards.

    python docs/data/neo4j/scripts/phase10_fix_data.py --step transport
    python docs/data/neo4j/scripts/phase10_fix_data.py --step transport --execute
"""
import argparse
import io
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[4]
load_dotenv(ROOT / "backend" / ".env")

# step -> list of (description, dry-run count query, write query)
STEPS = {
    # Task 4 — transport values produced by mock routing/rate providers.
    "transport": [
        ("Delete unselected EXPRESS options (unconfirmed service-level duplicates of the STANDARD option)",
         "MATCH (o:FulfilmentOption {serviceLevel:'EXPRESS', isSelected:false}) WHERE o.transportDataStatus IS NULL RETURN count(o) AS n",
         "MATCH (o:FulfilmentOption {serviceLevel:'EXPRESS', isSelected:false}) WHERE o.transportDataStatus IS NULL DETACH DELETE o RETURN count(*) AS n"),
        ("Null unsupported mode/carrier/service/transit/ETA/price and mark NOT_CONNECTED",
         "MATCH (o:FulfilmentOption) WHERE o.transportDataStatus IS NULL RETURN count(o) AS n",
         """MATCH (o:FulfilmentOption) WHERE o.transportDataStatus IS NULL
            SET o.transportMode = null, o.carrierCode = null, o.transitDays = null, o.eta = null,
                o.transportCost = null, o.currency = null,
                o.serviceLevel = CASE WHEN o.serviceLevel = 'SPLIT' THEN 'SPLIT' ELSE null END,
                o.transportDataStatus = 'NOT_CONNECTED'
            RETURN count(o) AS n"""),
    ],
    # Task 4b — stock snapshots written from the hardcoded inventory mock
    # (invented REGIONAL-DEPOT-AMS / -DEFAULT, fake 'HCME_ERP_SAP' provenance).
    # InventoryCache has no relationships and is regenerated on every check.
    "inventory": [
        ("Delete InventoryCache rows produced by the inventory mock (not SYNTHETIC_DEMO)",
         "MATCH (c:InventoryCache) WHERE coalesce(c.synthetic,false) = false AND c.testRunId IS NULL RETURN count(c) AS n",
         "MATCH (c:InventoryCache) WHERE coalesce(c.synthetic,false) = false AND c.testRunId IS NULL DETACH DELETE c RETURN count(*) AS n"),
    ],
    # Task 5 — records left behind by manual API / E2E test runs. Every app-
    # created Order is tagged INTERNAL_TEST_WORKFLOW; all 171 use test part
    # numbers (PN6/7/8/9-*TEST*) or invented destinations (DEALER-BRANCH-NL-01,
    # DEALER-BR-101). The SYNTHETIC_DEMO chain (order-demo-*, ship-demo-*,
    # SJ-DEMO-*) is synthetic=true and is never matched.
    "testdata": [
        ("Delete shipments (+ events) of test orders",
         "MATCH (o:Order {provenance:'INTERNAL_TEST_WORKFLOW'})-[:HAS_SHIPMENT]->(s:Shipment) WHERE coalesce(o.synthetic,false) = false RETURN count(DISTINCT s) AS n",
         """MATCH (o:Order {provenance:'INTERNAL_TEST_WORKFLOW'})-[:HAS_SHIPMENT]->(s:Shipment) WHERE coalesce(o.synthetic,false) = false
            OPTIONAL MATCH (s)-[:HAS_EVENT]->(e:ShipmentEvent)
            WITH collect(DISTINCT s) + collect(DISTINCT e) AS doomed UNWIND doomed AS d DETACH DELETE d RETURN count(*) AS n"""),
        ("Delete test orders",
         "MATCH (o:Order {provenance:'INTERNAL_TEST_WORKFLOW'}) WHERE coalesce(o.synthetic,false) = false RETURN count(o) AS n",
         "MATCH (o:Order {provenance:'INTERNAL_TEST_WORKFLOW'}) WHERE coalesce(o.synthetic,false) = false DETACH DELETE o RETURN count(*) AS n"),
        ("Delete non-synthetic allocations",
         "MATCH (a:Allocation) WHERE coalesce(a.synthetic,false) = false RETURN count(a) AS n",
         "MATCH (a:Allocation) WHERE coalesce(a.synthetic,false) = false DETACH DELETE a RETURN count(*) AS n"),
        ("Delete options of non-synthetic fulfilment requests",
         "MATCH (r:FulfilmentRequest) WHERE coalesce(r.synthetic,false) = false MATCH (o:FulfilmentOption {fulfilmentRequestId: r.id}) RETURN count(o) AS n",
         "MATCH (r:FulfilmentRequest) WHERE coalesce(r.synthetic,false) = false MATCH (o:FulfilmentOption {fulfilmentRequestId: r.id}) DETACH DELETE o RETURN count(*) AS n"),
        ("Delete non-synthetic fulfilment requests",
         "MATCH (r:FulfilmentRequest) WHERE coalesce(r.synthetic,false) = false RETURN count(r) AS n",
         "MATCH (r:FulfilmentRequest) WHERE coalesce(r.synthetic,false) = false DETACH DELETE r RETURN count(*) AS n"),
        ("Delete allocation ledger rows for test part numbers or invented sources",
         "MATCH (l:InventoryLedger) WHERE coalesce(l.synthetic,false) = false RETURN count(l) AS n",
         "MATCH (l:InventoryLedger) WHERE coalesce(l.synthetic,false) = false DETACH DELETE l RETURN count(*) AS n"),
        ("Delete test parts inquiries (test@example.com) and their requested parts",
         "MATCH (i:PartsInquiry) WHERE i.email ENDS WITH '@example.com' RETURN count(i) AS n",
         """MATCH (i:PartsInquiry) WHERE i.email ENDS WITH '@example.com'
            OPTIONAL MATCH (i)-[:REQUESTS]->(rp:RequestedPart)
            WITH collect(DISTINCT i) + collect(DISTINCT rp) AS doomed UNWIND doomed AS d DETACH DELETE d RETURN count(*) AS n"""),
        ("Delete orphan requested parts (no inquiry)",
         "MATCH (rp:RequestedPart) WHERE NOT ()-[:REQUESTS]->(rp) RETURN count(rp) AS n",
         "MATCH (rp:RequestedPart) WHERE NOT ()-[:REQUESTS]->(rp) DETACH DELETE rp RETURN count(*) AS n"),
        ("Delete test customers (@example.com)",
         "MATCH (c:Customer) WHERE c.email ENDS WITH '@example.com' RETURN count(c) AS n",
         "MATCH (c:Customer) WHERE c.email ENDS WITH '@example.com' DETACH DELETE c RETURN count(*) AS n"),
        ("Delete audit records left by aborted test runs (testRunId set)",
         "MATCH (a:AuditRecord) WHERE a.testRunId IS NOT NULL RETURN count(a) AS n",
         "MATCH (a:AuditRecord) WHERE a.testRunId IS NOT NULL DETACH DELETE a RETURN count(*) AS n"),
        ("Fix ServiceJob.order_id casing (ORD-DEMO-00x -> order-demo-00x, the real Order id)",
         "MATCH (j:ServiceJob) WHERE j.order_id STARTS WITH 'ORD-DEMO-' RETURN count(j) AS n",
         "MATCH (j:ServiceJob) WHERE j.order_id STARTS WITH 'ORD-DEMO-' SET j.order_id = toLower(j.order_id) RETURN count(j) AS n"),
    ],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=sorted(STEPS))
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with driver.session(database=os.environ.get("NEO4J_DATABASE") or None) as s:
        for desc, count_q, write_q in STEPS[args.step]:
            if args.execute:
                n = s.run(write_q).single()["n"]
                print(f"APPLIED  {n:5}  {desc}")
            else:
                n = s.run(count_q).single()["n"]
                print(f"DRY-RUN  {n:5}  {desc}")
    driver.close()


if __name__ == "__main__":
    main()
