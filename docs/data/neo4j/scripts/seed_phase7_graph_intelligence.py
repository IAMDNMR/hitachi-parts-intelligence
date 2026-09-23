#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs/data/neo4j/scripts/seed_phase7_graph_intelligence.py

Phase 7 Graph Intelligence Extension Seed Script.
Seeds compliance requirements and explicit mitigation demo relationships in Neo4j
while maintaining strict provenance boundaries:
- Real compliance facts (e.g. EU Battery Directive / HCME Battery compliance SRC-039)
- Explicit synthetic demo compliance and alternative relationships marked with
  `synthetic = true` and `data_source = "SYNTHETIC_DEMO"`.

Idempotent: every write is a MERGE keyed on a stable id.
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
    "CREATE CONSTRAINT ComplianceRequirement_id IF NOT EXISTS FOR (n:ComplianceRequirement) REQUIRE n.compliance_id IS UNIQUE",
]

# 1. REAL COMPLIANCE NODES (Derived from official HCME publications / EU Regulations)
# SRC-039: HCME European Battery Compliance publication
REAL_COMPLIANCE_CYPHER = """
UNWIND $rows AS row
MERGE (c:ComplianceRequirement {compliance_id: row.compliance_id})
SET c.name = row.name,
    c.regulation_standard = row.regulation_standard,
    c.issuing_body = row.issuing_body,
    c.requirement_type = row.requirement_type,
    c.description = row.description,
    c.source_id = row.source_id,
    c.data_class = row.data_class,
    c.confidence = row.confidence,
    c.source_date = row.source_date,
    c.synthetic = false,
    c.record_class = 'OFFICIAL_COMPLIANCE_REQUIREMENT'
WITH c, row
MATCH (p:Part {part_id: row.part_id})
MERGE (p)-[r:HAS_COMPLIANCE_REQUIREMENT]->(c)
SET r.status = 'COMPLIANT',
    r.evidence_type = 'PUBLISHED_HCME_COMPLIANCE_PAGE',
    r.source_id = row.source_id,
    r.confidence = row.confidence,
    r.synthetic = false
"""

REAL_COMPLIANCE_ROWS = [
    {
        "compliance_id": "COMP-EU-BATT-2023",
        "name": "EU Battery Regulation & Extended Producer Responsibility",
        "regulation_standard": "Regulation (EU) 2023/1542 / Directive 2006/66/EC",
        "issuing_body": "European Commission",
        "requirement_type": "Environmental & Safety Compliance",
        "description": "Compliance for industrial and starter batteries in construction equipment across EU Member States including registration and recycling directives.",
        "source_id": "SRC-039",
        "data_class": "OFFICIAL WEBSITE DATA",
        "confidence": "HIGH",
        "source_date": "2026-09-10",
        "part_id": "PT-001",
    },
    {
        "compliance_id": "COMP-EU-BATT-2023",
        "name": "EU Battery Regulation & Extended Producer Responsibility",
        "regulation_standard": "Regulation (EU) 2023/1542 / Directive 2006/66/EC",
        "issuing_body": "European Commission",
        "requirement_type": "Environmental & Safety Compliance",
        "description": "Compliance for industrial and starter batteries in construction equipment across EU Member States including registration and recycling directives.",
        "source_id": "SRC-039",
        "data_class": "OFFICIAL WEBSITE DATA",
        "confidence": "HIGH",
        "source_date": "2026-09-10",
        "part_id": "PT-002",
    },
    {
        "compliance_id": "COMP-EU-BATT-2023",
        "name": "EU Battery Regulation & Extended Producer Responsibility",
        "regulation_standard": "Regulation (EU) 2023/1542 / Directive 2006/66/EC",
        "issuing_body": "European Commission",
        "requirement_type": "Environmental & Safety Compliance",
        "description": "Compliance for industrial and starter batteries in construction equipment across EU Member States including registration and recycling directives.",
        "source_id": "SRC-039",
        "data_class": "OFFICIAL WEBSITE DATA",
        "confidence": "HIGH",
        "source_date": "2026-09-10",
        "part_id": "PT-003",
    },
]

# 2. SYNTHETIC COMPLIANCE NODES (For demonstrating compliance intelligence on non-battery assemblies)
SYNTHETIC_COMPLIANCE_CYPHER = """
UNWIND $rows AS row
MERGE (c:ComplianceRequirement {compliance_id: row.compliance_id})
SET c.name = row.name,
    c.regulation_standard = row.regulation_standard,
    c.issuing_body = row.issuing_body,
    c.requirement_type = row.requirement_type,
    c.description = row.description,
    c.synthetic = true,
    c.data_source = 'SYNTHETIC_DEMO',
    c.record_class = 'DEMO_COMPLIANCE_REQUIREMENT',
    c.note = 'SYNTHETIC DEMO DATA — demonstrates compliance intelligence graph traversal.'
WITH c, row
MATCH (p:Part {part_id: row.part_id})
MERGE (p)-[r:HAS_COMPLIANCE_REQUIREMENT]->(c)
SET r.status = row.status,
    r.evidence_type = 'SYNTHETIC_CERTIFICATION_RECORD',
    r.synthetic = true,
    r.data_source = 'SYNTHETIC_DEMO'
"""

SYNTHETIC_COMPLIANCE_ROWS = [
    {
        "compliance_id": "COMP-DEMO-STAGE-V",
        "name": "EU Non-Road Mobile Machinery (NRMM) Stage V Emissions",
        "regulation_standard": "Regulation (EU) 2016/1628",
        "issuing_body": "European Union Type Approval Authority",
        "requirement_type": "Exhaust Emissions Limit Compliance",
        "description": "Harmonized emission limits for particulate matter and NOx for industrial diesel engines powering mobile machinery.",
        "status": "COMPLIANT",
        "part_id": "PT-046",
    },
    {
        "compliance_id": "COMP-DEMO-CE-MACHINERY",
        "name": "EU Machinery Directive Safety & Pressure Manifold Standards",
        "regulation_standard": "Directive 2006/42/EC / EN ISO 4413:2010",
        "issuing_body": "CE Conformity Assessment",
        "requirement_type": "Hydraulic Fluid Power Safety Compliance",
        "description": "General rules and safety requirements for hydraulic systems and components in industrial equipment.",
        "status": "COMPLIANT",
        "part_id": "PT-044",
    },
    {
        "compliance_id": "COMP-DEMO-EMC-24V",
        "name": "Automotive & Machinery Electromagnetic Compatibility (EMC)",
        "regulation_standard": "UNECE Regulation 10 / ISO 13766-1:2018",
        "issuing_body": "TÜV Rheinland / CE",
        "requirement_type": "EMC & Electrical Noise Immunity",
        "description": "Immunity and emission limits for electrical and electronic assemblies on earth-moving machinery.",
        "status": "COMPLIANT",
        "part_id": "PT-054",
    },
    {
        "compliance_id": "COMP-DEMO-EMC-24V",
        "name": "Automotive & Machinery Electromagnetic Compatibility (EMC)",
        "regulation_standard": "UNECE Regulation 10 / ISO 13766-1:2018",
        "issuing_body": "TÜV Rheinland / CE",
        "requirement_type": "EMC & Electrical Noise Immunity",
        "description": "Immunity and emission limits for electrical and electronic assemblies on earth-moving machinery.",
        "status": "COMPLIANT",
        "part_id": "PT-056",
    },
]


def run(dry_run: bool = False):
    driver = GraphDatabase.driver(URI, auth=(USER, PW))
    with driver.session(database=DB) as s:
        if dry_run:
            print("DRY RUN — no writes will be made.")
            print(f"Would create constraints and MERGE {len(REAL_COMPLIANCE_ROWS)} real compliance edges and {len(SYNTHETIC_COMPLIANCE_ROWS)} synthetic compliance edges.")
            driver.close()
            return

        for stmt in SCHEMA_STATEMENTS:
            s.run(stmt).consume()
        print("Schema constraints created.")

        s.run(REAL_COMPLIANCE_CYPHER, {"rows": REAL_COMPLIANCE_ROWS}).consume()
        print(f"Real compliance nodes/edges: {len(REAL_COMPLIANCE_ROWS)} MERGEd")

        s.run(SYNTHETIC_COMPLIANCE_CYPHER, {"rows": SYNTHETIC_COMPLIANCE_ROWS}).consume()
        print(f"Synthetic compliance nodes/edges: {len(SYNTHETIC_COMPLIANCE_ROWS)} MERGEd")

    driver.close()
    print("Phase 7 Graph Intelligence seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run))
