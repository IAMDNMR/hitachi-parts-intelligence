#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs/data/neo4j/scripts/seed_phase8_service_data.py

Phase 8 Dealer & Service Job Seed Script.
Seeds representative synthetic demo ServiceJob and ServiceEvent nodes attached
to existing canonical Part, Machine, DealerBranch, and demo Order/Shipment entities
in Neo4j AuraDB.

All synthetic records carry:
  synthetic = true
  data_source = "SYNTHETIC_DEMO"
  provenance = "INTERNAL_SERVICE_WORKFLOW"

Idempotent: every write is a MERGE keyed on stable unique IDs.
"""

import argparse
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

SCHEMA_STATEMENTS = [
    "CREATE CONSTRAINT ServiceJob_id IF NOT EXISTS FOR (n:ServiceJob) REQUIRE n.service_job_id IS UNIQUE",
    "CREATE CONSTRAINT ServiceEvent_id IF NOT EXISTS FOR (n:ServiceEvent) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX ServiceJob_orderId IF NOT EXISTS FOR (n:ServiceJob) ON (n.order_id)",
    "CREATE INDEX ServiceJob_dealerId IF NOT EXISTS FOR (n:ServiceJob) ON (n.dealer_id)",
    "CREATE INDEX ServiceJob_status IF NOT EXISTS FOR (n:ServiceJob) ON (n.status)",
]

DEMO_SERVICE_JOBS = [
    {
        "service_job_id": "SJ-DEMO-001",
        "order_id": "ORD-DEMO-001",
        "shipment_id": "ship-demo-001",
        "dealer_id": "DLR-019",
        "part_id": "PT-001",
        "machine_id": "ZX210-7",
        "status": "COMPLETED",
        "service_type": "PARTS_INSTALLATION",
        "work_order_number": "WO-EU-2026-081",
        "notes": "Scheduled heavy-duty 24V starter battery replacement and diagnostic health check.",
        "received_at": "2026-09-15T09:30:00Z",
        "started_at": "2026-09-15T11:00:00Z",
        "installed_at": "2026-09-15T13:45:00Z",
        "completed_at": "2026-09-15T14:30:00Z",
        "events": [
            {
                "id": "sevt-demo-001-1",
                "event_type": "CREATED",
                "description": "Service job created upon parts order acceptance for German branch depot.",
                "technician_role": "SYSTEM",
                "notes": "Awaiting EPC dispatch",
                "timestamp": "2026-09-12T08:00:00Z",
            },
            {
                "id": "sevt-demo-001-2",
                "event_type": "PART_RECEIVED",
                "description": "OEM battery pack received and verified with zero transit damage.",
                "technician_role": "DEALER_PARTS_INSPECTOR",
                "notes": "Condition verified 100%",
                "timestamp": "2026-09-15T09:30:00Z",
            },
            {
                "id": "sevt-demo-001-3",
                "event_type": "IN_PROGRESS",
                "description": "Machine staged in bay 3; technician disconnected old battery terminal group.",
                "technician_role": "CERTIFIED_SERVICE_TECHNICIAN",
                "notes": "Isolation verified",
                "timestamp": "2026-09-15T11:00:00Z",
            },
            {
                "id": "sevt-demo-001-4",
                "event_type": "PART_INSTALLED",
                "description": "Genuine HCME 4654921 battery installed, hold-down bracket torqued to OEM spec.",
                "technician_role": "CERTIFIED_SERVICE_TECHNICIAN",
                "notes": "Terminal grease applied",
                "timestamp": "2026-09-15T13:45:00Z",
            },
            {
                "id": "sevt-demo-001-5",
                "event_type": "COMPLETED",
                "description": "Engine cranking diagnostic test passed; telematics battery voltage confirmed 27.8V; job closed.",
                "technician_role": "WORKSHOP_MANAGER",
                "notes": "Signoff complete",
                "timestamp": "2026-09-15T14:30:00Z",
            },
        ],
    },
    {
        "service_job_id": "SJ-DEMO-002",
        "order_id": "ORD-DEMO-002",
        "shipment_id": "ship-demo-002",
        "dealer_id": "DLR-001",
        "part_id": "PT-055",
        "machine_id": "ZX210-7",
        "status": "IN_PROGRESS",
        "service_type": "EMERGENCY_REPAIR",
        "work_order_number": "WO-EU-2026-082",
        "notes": "Starter motor replacement on high-uptime customer excavator fleet.",
        "received_at": "2026-09-20T10:15:00Z",
        "started_at": "2026-09-20T14:00:00Z",
        "installed_at": None,
        "completed_at": None,
        "events": [
            {
                "id": "sevt-demo-002-1",
                "event_type": "CREATED",
                "description": "Urgent work order registered at Hitachi Construction Machinery Europe (Oosterhout workshop).",
                "technician_role": "SYSTEM",
                "notes": "Priority dispatch",
                "timestamp": "2026-09-18T16:00:00Z",
            },
            {
                "id": "sevt-demo-002-2",
                "event_type": "PART_RECEIVED",
                "description": "Starter motor received from Neovia logistics hub and inspected.",
                "technician_role": "DEALER_PARTS_INSPECTOR",
                "notes": "Bench test passed",
                "timestamp": "2026-09-20T10:15:00Z",
            },
            {
                "id": "sevt-demo-002-3",
                "event_type": "IN_PROGRESS",
                "description": "Technician mounting heavy-duty 24V starter assembly on flywheel housing.",
                "technician_role": "CERTIFIED_SERVICE_TECHNICIAN",
                "notes": "Alignment in progress",
                "timestamp": "2026-09-20T14:00:00Z",
            },
        ],
    },
]

SEED_SERVICE_CYPHER = """
UNWIND $jobs AS job
MERGE (sj:ServiceJob {service_job_id: job.service_job_id})
SET sj.order_id          = job.order_id,
    sj.shipment_id       = job.shipment_id,
    sj.dealer_id         = job.dealer_id,
    sj.status            = job.status,
    sj.service_type      = job.service_type,
    sj.work_order_number = job.work_order_number,
    sj.notes             = job.notes,
    sj.received_at       = CASE WHEN job.received_at IS NOT NULL THEN datetime(job.received_at) ELSE null END,
    sj.started_at        = CASE WHEN job.started_at IS NOT NULL THEN datetime(job.started_at) ELSE null END,
    sj.installed_at      = CASE WHEN job.installed_at IS NOT NULL THEN datetime(job.installed_at) ELSE null END,
    sj.completed_at      = CASE WHEN job.completed_at IS NOT NULL THEN datetime(job.completed_at) ELSE null END,
    sj.synthetic         = true,
    sj.data_source       = 'SYNTHETIC_DEMO',
    sj.provenance        = 'INTERNAL_SERVICE_WORKFLOW',
    sj.createdAt         = datetime(),
    sj.updatedAt         = datetime()

WITH sj, job
OPTIONAL MATCH (d:DealerBranch {dealer_id: job.dealer_id})
FOREACH (dlr IN CASE WHEN d IS NOT NULL THEN [d] ELSE [] END |
    MERGE (dlr)-[:PERFORMS_SERVICE]->(sj)
)

WITH sj, job
OPTIONAL MATCH (p:Part {part_id: job.part_id})
FOREACH (pt IN CASE WHEN p IS NOT NULL THEN [p] ELSE [] END |
    MERGE (sj)-[:FOR_PART]->(pt)
)

WITH sj, job
OPTIONAL MATCH (m:Machine) WHERE m.machine_id = job.machine_id OR m.model = job.machine_id
FOREACH (mc IN CASE WHEN m IS NOT NULL THEN [m] ELSE [] END |
    MERGE (sj)-[:FOR_MACHINE]->(mc)
)

WITH sj, job
OPTIONAL MATCH (o:Order {id: job.order_id})
FOREACH (ord IN CASE WHEN o IS NOT NULL THEN [o] ELSE [] END |
    MERGE (ord)-[:HAS_SERVICE_JOB]->(sj)
)

WITH sj, job
OPTIONAL MATCH (sh:Shipment {shipment_id: job.shipment_id})
FOREACH (s IN CASE WHEN sh IS NOT NULL THEN [sh] ELSE [] END |
    MERGE (s)-[:HAS_SERVICE_JOB]->(sj)
)

WITH sj, job
UNWIND job.events AS ev
MERGE (e:ServiceEvent {id: ev.id})
SET e.event_type      = ev.event_type,
    e.description     = ev.description,
    e.technician_role = ev.technician_role,
    e.notes           = ev.notes,
    e.timestamp       = datetime(ev.timestamp),
    e.synthetic       = true,
    e.data_source     = 'SYNTHETIC_DEMO'
MERGE (sj)-[:HAS_EVENT]->(e)
"""


def run(dry_run: bool = False):
    driver = GraphDatabase.driver(
        URI,
        auth=(USER, PW),
        max_connection_pool_size=50,
        connection_acquisition_timeout=60,
    )
    session_kwargs = {}
    if DB:
        session_kwargs["database"] = DB

    with driver.session(**session_kwargs) as s:
        if dry_run:
            print("DRY RUN — no writes will be made.")
            print(f"Would create constraints and MERGE {len(DEMO_SERVICE_JOBS)} demo ServiceJobs.")
            driver.close()
            return

        for stmt in SCHEMA_STATEMENTS:
            try:
                s.run(stmt).consume()
            except Exception as e:
                print(f"Constraint notice: {e}")
        print("Schema constraints created.")

        s.run(SEED_SERVICE_CYPHER, {"jobs": DEMO_SERVICE_JOBS}).consume()
        print(f"Seeded {len(DEMO_SERVICE_JOBS)} demo ServiceJob nodes and events into Neo4j AuraDB.")

    driver.close()
    print("Phase 8 Service seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run))
