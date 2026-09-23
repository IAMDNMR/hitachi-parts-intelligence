#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 10B — repair drift in the hand-seeded SYNTHETIC_DEMO order journey
(order-demo-001/002/003, ship-demo-001/002, SJ-DEMO-001/002, fr-demo-001/002/003).

These records were created once, directly in Cypher, rather than by replaying
the real create_shipment()/dispatch_shipment()/confirm_delivery() functions —
so they drifted out of sync with the documented state machine
(docs/business-process/PROCESS_STATES.md) and lost their ShipmentEvent trail
(root cause unknown; not reproducible from any script in this repo).

Fixes (all SYNTHETIC_DEMO, all synthetic=true, nothing invented beyond
restating the shipment's own already-recorded status as its own event log):
  1. Shipment.order_id: was null on both; set from the real HAS_SHIPMENT edge.
  2. ShipmentEvent trail: recreated to match each shipment's OWN recorded
     status (CREATED [+ DISPATCHED [+ DELIVERED]]), using the shipment's own
     shipped_at/eta/carrier — no new fact is introduced.
  3. FulfilmentRequest.status: recomputed from the now-fixed code path
     (Order -> Shipment -> ServiceJob), matching docs/business-process/
     PROCESS_STATES.md's rule (COMPLETED only when Shipment=DELIVERED AND
     ServiceJob=COMPLETED).

Run:
    python docs/data/neo4j/scripts/phase10b_repair_demo_journey.py            # dry run
    python docs/data/neo4j/scripts/phase10b_repair_demo_journey.py --execute
"""
import argparse
import io
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[4]
load_dotenv(ROOT / "backend" / ".env")

FIX_ORDER_ID = """
MATCH (o:Order)-[:HAS_SHIPMENT]->(sh:Shipment)
WHERE sh.order_id IS NULL
SET sh.order_id = o.id
RETURN sh.shipment_id AS shipment_id, o.id AS order_id
"""

# event_type -> (description, uses field on Shipment for timestamp/location)
EVENT_TEMPLATES = [
    ("CREATED", "Shipment created and scheduled for carrier dispatch.", "origin"),
    ("DISPATCHED", "Shipment handed to carrier and dispatched from origin facility.", "origin"),
    ("DELIVERED", "Shipment delivered to destination dealer facility and accepted.", "destination"),
]
STATUS_ORDER = ["CREATED", "DISPATCHED", "SHIPPED", "DELIVERED"]  # SHIPPED == DISPATCHED here


def plan_events(session):
    rows = session.run(
        "MATCH (sh:Shipment) WHERE NOT (sh)-[:HAS_EVENT]->(:ShipmentEvent) "
        "RETURN sh.shipment_id AS id, sh.status AS status, sh.origin AS origin, "
        "sh.destination AS destination, sh.synthetic AS synthetic"
    ).data()
    plan = []
    for r in rows:
        reached = STATUS_ORDER.index("DISPATCHED" if r["status"] == "SHIPPED" else r["status"])
        for etype, desc, loc_field in EVENT_TEMPLATES:
            if STATUS_ORDER.index(etype) > reached:
                continue
            plan.append({
                "shipment_id": r["id"], "event_id": f"evt-{uuid.uuid4()}", "event_type": etype,
                "description": desc, "location": r[loc_field] or "Unknown", "synthetic": bool(r["synthetic"]),
            })
    return plan


WRITE_EVENTS = """
UNWIND $rows AS r
MATCH (sh:Shipment {shipment_id: r.shipment_id})
CREATE (e:ShipmentEvent {
    id: r.event_id, event_type: r.event_type, description: r.description, location: r.location,
    timestamp: datetime(), synthetic: r.synthetic, data_source: 'SYNTHETIC_DEMO'
})
MERGE (sh)-[:HAS_EVENT]->(e)
RETURN count(e) AS n
"""

RECOMPUTE_FR_STATUS = """
MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o:Order)
WHERE fr.status IN ['ORDERED', 'FULFILMENT', 'SHIPPED', 'DELIVERED']
OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
OPTIONAL MATCH (sh)-[:HAS_SERVICE_JOB]->(sj:ServiceJob)
WITH fr, sh, sj,
     CASE
       WHEN sh IS NULL THEN fr.status
       WHEN sh.status = 'DELIVERED' AND sj IS NOT NULL AND sj.status = 'COMPLETED' THEN 'COMPLETED'
       WHEN sh.status = 'DELIVERED' THEN 'DELIVERED'
       WHEN sh.status IN ['DISPATCHED', 'SHIPPED'] THEN 'SHIPPED'
       ELSE fr.status
     END AS new_status
WHERE new_status <> fr.status
SET fr.status = new_status, fr.updatedAt = datetime(),
    fr.completed_at = CASE WHEN new_status = 'COMPLETED' THEN datetime() ELSE fr.completed_at END
RETURN fr.id AS id, new_status AS status
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with driver.session(database=os.environ.get("NEO4J_DATABASE") or None) as s:
        if not args.execute:
            missing = s.run("MATCH (sh:Shipment) WHERE sh.order_id IS NULL RETURN count(sh) AS n").single()["n"]
            events = plan_events(s)
            fr = s.run(RECOMPUTE_FR_STATUS.replace("SET fr.status = new_status, fr.updatedAt = datetime(),\n    fr.completed_at = CASE WHEN new_status = 'COMPLETED' THEN datetime() ELSE fr.completed_at END\nRETURN", "RETURN")).data()
            print(f"DRY-RUN  shipments missing order_id: {missing}")
            print(f"DRY-RUN  ShipmentEvents to create: {len(events)}")
            for e in events:
                print(f"   {e['shipment_id']} {e['event_type']}")
            print(f"DRY-RUN  FulfilmentRequest status changes: {fr}")
            return
        n1 = len(s.run(FIX_ORDER_ID).data())
        events = plan_events(s)
        n2 = s.run(WRITE_EVENTS, rows=events).single()["n"] if events else 0
        fr_changes = s.run(RECOMPUTE_FR_STATUS).data()
        print(f"APPLIED  {n1} Shipment.order_id fixed")
        print(f"APPLIED  {n2} ShipmentEvent restored")
        print(f"APPLIED  {len(fr_changes)} FulfilmentRequest status corrected: {fr_changes}")
    driver.close()


if __name__ == "__main__":
    main()
