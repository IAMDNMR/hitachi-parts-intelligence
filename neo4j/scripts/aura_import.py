#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HCME After-Sales Neo4j Aura Import Script
==========================================
Loads the full graph into Neo4j Aura using the Python driver (parameterised
Cypher) — NOT file:/// LOAD CSV, which Aura does not support.

Reads credentials from neo4j/.env (never prints them).

Import order mirrors neo4j/IMPORT_DESIGN_REPORT.md §6 exactly:
  1.  Constraints
  2-10. Node files (categories, machines, specs, applications, attachments,
        parts, services, digital_services, channels)
  11-20. Relationship files (machine_category, machine_specification,
         machine_application, machine_attachment, machine_part_fitment,
         machine_service, service_part_requirement, machine_digital_service,
         channel_relationships, maintenance)
  21.  Indexes

Run:
    python neo4j/scripts/aura_import.py
    python neo4j/scripts/aura_import.py --dry-run   # count-only, no writes
"""

import csv
import sys
import re
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import certifi
import ssl
from neo4j import GraphDatabase

# SSL fix: point Python's SSL to certifi's CA bundle (Aura's cert is signed
# by a CA that Windows' built-in root store may not include).
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT   = Path(__file__).resolve().parent.parent.parent
DATA   = ROOT / "neo4j" / "data"
REPORTS = ROOT / "neo4j" / "reports"
ENV    = ROOT / "neo4j" / ".env"

# ---------------------------------------------------------------------------
# Credentials (never printed)
# ---------------------------------------------------------------------------
load_dotenv(ENV)
URI      = os.environ["NEO4J_URI"]
USERNAME = os.environ["NEO4J_USERNAME"]
PASSWORD = os.environ["NEO4J_PASSWORD"]
DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load(fname, base=DATA):
    with open(base / fname, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run(session, query, params=None, label=""):
    try:
        result = session.run(query, params or {})
        counters = result.consume().counters
        return counters
    except Exception as e:
        print(f"  [ERROR] {label}: {e}")
        raise


def batch(session, query, rows, batch_size=500, label=""):
    """Run a parameterised query in batches using UNWIND."""
    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        result = session.run(
            f"UNWIND $rows AS row\n{query}",
            {"rows": chunk}
        )
        c = result.consume().counters
        total += c.nodes_created + c.relationships_created + c.properties_set
    return total


def nv(val):
    """Return None if val is empty/whitespace, else strip it."""
    if val is None:
        return None
    v = str(val).strip()
    return v if v else None


def ni(val):
    """nv + int conversion."""
    v = nv(val)
    return int(v) if v is not None else None


def nf(val):
    """nv + float conversion."""
    v = nv(val)
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


def nb(val):
    """nv + bool conversion (True/False/true/false)."""
    v = nv(val)
    if v is None:
        return None
    return v.lower() == "true"

# ---------------------------------------------------------------------------
# Step 1: Constraints
# ---------------------------------------------------------------------------

CONSTRAINTS = [
    "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (n:Category) REQUIRE n.category_id IS UNIQUE",
    "CREATE CONSTRAINT machine_id_unique IF NOT EXISTS FOR (n:Machine) REQUIRE n.machine_id IS UNIQUE",
    "CREATE CONSTRAINT spec_id_unique IF NOT EXISTS FOR (n:Specification) REQUIRE n.spec_id IS UNIQUE",
    "CREATE CONSTRAINT application_name_unique IF NOT EXISTS FOR (n:Application) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT part_id_unique IF NOT EXISTS FOR (n:Part) REQUIRE n.part_id IS UNIQUE",
    "CREATE CONSTRAINT attachment_id_unique IF NOT EXISTS FOR (n:Attachment) REQUIRE n.attachment_id IS UNIQUE",
    "CREATE CONSTRAINT service_id_unique IF NOT EXISTS FOR (n:Service) REQUIRE n.service_id IS UNIQUE",
    "CREATE CONSTRAINT digital_service_id_unique IF NOT EXISTS FOR (n:DigitalService) REQUIRE n.digital_service_id IS UNIQUE",
    "CREATE CONSTRAINT channel_id_unique IF NOT EXISTS FOR (n:Channel) REQUIRE n.channel_id IS UNIQUE",
]

# ---------------------------------------------------------------------------
# Step 2: Categories (17 nodes)
# ---------------------------------------------------------------------------

def import_categories(session):
    rows = load("categories.csv")
    print(f"  categories.csv: {len(rows)} rows")
    q = """
    MATCH (row_dummy) WHERE false RETURN 1  // ensure query is in context
    """
    # inline batch
    data = [
        {
            "category_id":          nv(r["Category ID"]),
            "parent_category":       nv(r["Parent Category"]),
            "category_name":         nv(r["Category Name"]),
            "official_category_name": nv(r["Official Category Name"]),
            "category_description":  nv(r["Category Description"]),
            "product_type":          nv(r["Product Type"]),
            "machine_configuration": nv(r["Machine Configuration"]),
            "on_road_off_road":      nv(r["On-road / Off-road"]),
            "primary_application":   nv(r["Primary Application"]),
            "source_id":             nv(r["Source ID"]),
            "source_date":           nv(r["Source Date"]),
        }
        for r in rows
    ]
    cypher = """
    MERGE (c:Category {category_id: row.category_id})
    SET c.parent_category        = row.parent_category,
        c.category_name          = row.category_name,
        c.official_category_name = row.official_category_name,
        c.category_description   = row.category_description,
        c.product_type            = row.product_type,
        c.machine_configuration   = row.machine_configuration,
        c.on_road_off_road        = row.on_road_off_road,
        c.primary_application     = row.primary_application,
        c.source_id               = row.source_id,
        c.source_date             = row.source_date
    """
    total = batch(session, cypher, data, label="categories")
    print(f"  -> categories: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 3: Machines (77 nodes)
# ---------------------------------------------------------------------------

def import_machines(session):
    rows = load("machines.csv")
    print(f"  machines.csv: {len(rows)} rows")
    data = [
        {
            "machine_id":              nv(r["Machine ID"]),
            "manufacturer":            nv(r["Manufacturer"]),
            "brand":                   nv(r["Brand"]),
            "machine_category":        nv(r["Machine Category"]),
            "machine_subcategory":     nv(r["Machine Subcategory"]),
            "category_id":             nv(r["Category ID"]),
            "product_family":          nv(r["Product Family"]),
            "model":                   nv(r["Model"]),
            "models_covered":          [x.strip() for x in nv(r["Models Covered"]).split("|")] if nv(r["Models Covered"]) else [],
            "model_count":             ni(r["Model Count"]),
            "generation_series":       nv(r["Generation / Series"]),
            "machine_type":            nv(r["Machine Type"]),
            "configuration":           nv(r["Configuration"]),
            "power_source":            nv(r["Power Source"]),
            "official_product_name":   nv(r["Official Product Name"]),
            "available_in":            nv(r["Available In"]),
            "engine_rated_power":      nv(r["Engine / Motor Rated Power"]),
            "operating_weight_published": nv(r["Operating Weight (as published)"]),
            "operating_weight_kg":     nf(r["Operating Weight (kg, normalised)"]),
            "bucket_capacity_published": nv(r["Bucket Capacity (as published)"]),
            "battery_capacity":        nv(r["Battery Capacity"]),
            "nominal_payload":         nv(r["Nominal Payload"]),
            "max_digging_depth":       nv(r["Max. Digging Depth"]),
            "max_digging_reach":       nv(r["Max. Digging Reach"]),
            "overall_width":           nv(r["Overall Width"]),
            "overall_height_of_cab":   nv(r["Overall Height of Cab"]),
            "fuel_tank_capacity":      nv(r["Fuel Tank Capacity"]),
            "official_overview_text":  nv(r["Official Overview Text"]),
            "data_class":              nv(r["Data Class"]),
            "source_id":               nv(r["Source ID"]),
            "source_date":             nv(r["Source Date"]),
        }
        for r in rows
    ]
    cypher = """
    MERGE (m:Machine {machine_id: row.machine_id})
    SET m.manufacturer           = row.manufacturer,
        m.brand                  = row.brand,
        m.machine_category       = row.machine_category,
        m.machine_subcategory    = row.machine_subcategory,
        m.category_id            = row.category_id,
        m.product_family         = row.product_family,
        m.model                  = row.model,
        m.models_covered         = row.models_covered,
        m.model_count            = row.model_count,
        m.generation_series       = row.generation_series,
        m.machine_type            = row.machine_type,
        m.configuration           = row.configuration,
        m.power_source            = row.power_source,
        m.official_product_name   = row.official_product_name,
        m.available_in            = row.available_in,
        m.engine_rated_power      = row.engine_rated_power,
        m.operating_weight_published = row.operating_weight_published,
        m.operating_weight_kg     = row.operating_weight_kg,
        m.bucket_capacity_published = row.bucket_capacity_published,
        m.battery_capacity        = row.battery_capacity,
        m.nominal_payload         = row.nominal_payload,
        m.max_digging_depth       = row.max_digging_depth,
        m.max_digging_reach       = row.max_digging_reach,
        m.overall_width           = row.overall_width,
        m.overall_height_of_cab   = row.overall_height_of_cab,
        m.fuel_tank_capacity      = row.fuel_tank_capacity,
        m.official_overview_text  = row.official_overview_text,
        m.data_class              = row.data_class,
        m.source_id               = row.source_id,
        m.source_date             = row.source_date
    """
    total = batch(session, cypher, data, label="machines")
    print(f"  -> machines: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 4: Specifications (1635 nodes)
# ---------------------------------------------------------------------------

def import_specifications(session):
    rows = load("specifications.csv")
    print(f"  specifications.csv: {len(rows)} rows")
    data = [
        {
            "spec_id":             nv(r["Spec ID"]),
            "machine_id":          nv(r["Machine ID"]),
            "specification_group": nv(r["Specification Group"]),
            "specification_name":  nv(r["Specification Name"]),
            "specification_value": nv(r["Specification Value"]),
            "unit":                nv(r["Unit"]),
            "normalised_value":    nv(r["Normalised Value"]),
            "value_stated":        nb(r.get("value_stated")),
            "data_class":          nv(r["Data Class"]),
            "source_id":           nv(r["Source ID"]),
            "source_date":         nv(r["Source Date"]),
        }
        for r in rows
    ]
    cypher = """
    MERGE (s:Specification {spec_id: row.spec_id})
    SET s.machine_id           = row.machine_id,
        s.specification_group  = row.specification_group,
        s.specification_name   = row.specification_name,
        s.specification_value  = row.specification_value,
        s.unit                 = row.unit,
        s.normalised_value     = row.normalised_value,
        s.value_stated         = row.value_stated,
        s.data_class           = row.data_class,
        s.source_id            = row.source_id,
        s.source_date          = row.source_date
    """
    total = batch(session, cypher, data, label="specifications")
    print(f"  -> specifications: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 5: Applications (29 distinct nodes from 328 rows)
# ---------------------------------------------------------------------------

def import_applications(session):
    rows = load("applications.csv")
    print(f"  applications.csv: {len(rows)} rows -> 29 distinct Application nodes")
    # deduplicate for node creation
    seen = {}
    for r in rows:
        name = nv(r["Application"])
        if name and name not in seen:
            seen[name] = nv(r["Application Type"])
    data = [{"name": k, "application_type": v} for k, v in seen.items()]
    cypher = """
    MERGE (a:Application {name: row.name})
    SET a.application_type = row.application_type
    """
    total = batch(session, cypher, data, label="applications")
    print(f"  -> applications: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 6: Attachments (17 nodes)
# ---------------------------------------------------------------------------

def import_attachments(session):
    rows = load("attachments.csv")
    print(f"  attachments.csv: {len(rows)} rows")
    data = [
        {
            "attachment_id":          nv(r["Attachment ID"]),
            "attachment_name":        nv(r["Attachment Name"]),
            "attachment_type":        nv(r["Attachment Type"]),
            "attachment_category":    nv(r["Attachment Category"]),
            "compatible_machine_model":    nv(r["Compatible Machine Model"]),
            "compatible_machine_category": nv(r["Compatible Machine Category"]),
            "mounting_coupling_type": nv(r["Mounting / Coupling Type"]),
            "hydraulic_requirement":  nv(r["Hydraulic Requirement"]),
            "weight":                 nv(r["Weight"]),
            "dimensions":             nv(r["Dimensions"]),
            "capacity":               nv(r["Capacity"]),
            "purpose_application":    nv(r["Purpose / Application"]),
            "detachable_fixed":       nv(r["Detachable / Fixed"]),
            "data_class":             nv(r["Data Class"]),
            "source_id":              nv(r["Source ID"]),
            "confidence":             nv(r["Confidence"]),
            "source_date":            nv(r["Source Date"]),
        }
        for r in rows
    ]
    cypher = """
    MERGE (a:Attachment {attachment_id: row.attachment_id})
    SET a.attachment_name              = row.attachment_name,
        a.attachment_type              = row.attachment_type,
        a.attachment_category          = row.attachment_category,
        a.compatible_machine_model     = row.compatible_machine_model,
        a.compatible_machine_category  = row.compatible_machine_category,
        a.mounting_coupling_type       = row.mounting_coupling_type,
        a.hydraulic_requirement        = row.hydraulic_requirement,
        a.weight                       = row.weight,
        a.dimensions                   = row.dimensions,
        a.capacity                     = row.capacity,
        a.purpose_application          = row.purpose_application,
        a.detachable_fixed             = row.detachable_fixed,
        a.data_class                   = row.data_class,
        a.source_id                    = row.source_id,
        a.confidence                   = row.confidence,
        a.source_date                  = row.source_date
    """
    total = batch(session, cypher, data, label="attachments")
    print(f"  -> attachments: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 7: Parts (43 nodes)
# ---------------------------------------------------------------------------

def import_parts(session):
    rows = load("parts.csv")
    print(f"  parts.csv: {len(rows)} rows")
    data = [
        {
            "part_id":              nv(r["Part ID"]),
            "part_number":          nv(r["Part Number"]),
            "part_name":            nv(r["Part Name"]),
            "part_category":        nv(r["Part Category"]),
            "part_subcategory":     nv(r["Part Subcategory"]),
            "component_assembly":   nv(r["Component / Assembly"]),
            "genuine_hitachi_part": nv(r["Genuine Hitachi Part"]),
            "consumable":           nv(r["Consumable"]),
            "wear_part":            nv(r["Wear Part"]),
            "replacement_part":     nv(r["Replacement Part"]),
            "service_part":         nv(r["Service Part"]),
            "attachment_part":      nv(r["Attachment Part"]),
            "description":          nv(r["Description"]),
            "supersedes_part_number": nv(r["Supersedes Part Number"]),
            "superseded_by":        nv(r["Superseded By"]),
            "record_class":         nv(r["record_class"]),
            "data_class":           nv(r["Data Class"]),
            "source_id":            nv(r["Source ID"]),
            "confidence":           nv(r["Confidence"]),
            "source_date":          nv(r["Source Date"]),
        }
        for r in rows
    ]
    cypher = """
    MERGE (p:Part {part_id: row.part_id})
    SET p.part_number          = row.part_number,
        p.part_name            = row.part_name,
        p.part_category        = row.part_category,
        p.part_subcategory     = row.part_subcategory,
        p.component_assembly   = row.component_assembly,
        p.genuine_hitachi_part = row.genuine_hitachi_part,
        p.consumable           = row.consumable,
        p.wear_part            = row.wear_part,
        p.replacement_part     = row.replacement_part,
        p.service_part         = row.service_part,
        p.attachment_part      = row.attachment_part,
        p.description          = row.description,
        p.supersedes_part_number = row.supersedes_part_number,
        p.superseded_by        = row.superseded_by,
        p.record_class         = row.record_class,
        p.data_class           = row.data_class,
        p.source_id            = row.source_id,
        p.confidence           = row.confidence,
        p.source_date          = row.source_date
    """
    total = batch(session, cypher, data, label="parts")
    print(f"  -> parts: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 8: Services (22 nodes)
# ---------------------------------------------------------------------------

def import_services(session):
    rows = load("services.csv")
    print(f"  services.csv: {len(rows)} rows")
    data = [
        {
            "service_id":          nv(r["Service ID"]),
            "service_name":        nv(r["Service Name"]),
            "service_category":    nv(r["Service Category"]),
            "description":         nv(r["Description"]),
            "applies_to_category": nv(r["Applies To Machine Category"]),
            "applies_to_model":    nv(r["Applies To Machine Model"]),
            "customer_site":       nv(r["Customer Site"]),
            "dealer_workshop":     nv(r["Dealer Workshop"]),
            "other_location":      nv(r["Other Location"]),
            "dealer_delivered":    nv(r["Dealer Delivered"]),
            "external_authorised_provider": nv(r["External Authorised Provider"]),
            "related_parts":       nv(r["Related Parts"]),
            "related_machine_data": nv(r["Related Machine Data"]),
            "official_or_derived": nv(r["Official / Derived"]),
            "source_id":           nv(r["Source ID"]),
            "source_date":         nv(r["Source Date"]),
        }
        for r in rows
    ]
    cypher = """
    MERGE (s:Service {service_id: row.service_id})
    SET s.service_name              = row.service_name,
        s.service_category          = row.service_category,
        s.description               = row.description,
        s.applies_to_category       = row.applies_to_category,
        s.applies_to_model          = row.applies_to_model,
        s.customer_site             = row.customer_site,
        s.dealer_workshop           = row.dealer_workshop,
        s.other_location            = row.other_location,
        s.dealer_delivered          = row.dealer_delivered,
        s.external_authorised_provider = row.external_authorised_provider,
        s.related_parts             = row.related_parts,
        s.related_machine_data      = row.related_machine_data,
        s.official_or_derived       = row.official_or_derived,
        s.source_id                 = row.source_id,
        s.source_date               = row.source_date
    """
    total = batch(session, cypher, data, label="services")
    print(f"  -> services: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 9: DigitalServices (8 distinct nodes from 616 rows)
# ---------------------------------------------------------------------------

def import_digital_services(session):
    rows = load("digital_services.csv")
    print(f"  digital_services.csv: {len(rows)} rows -> 8 distinct DigitalService nodes")
    seen = {}
    for r in rows:
        ds_id = nv(r["Digital Service ID"])
        if ds_id and ds_id not in seen:
            seen[ds_id] = {
                "digital_service_id": ds_id,
                "service_name":       nv(r["Service Name"]),
                "capability":         nv(r["Capability"]),
                "machine_data":       nv(r["Machine Data"]),
                "alert_monitoring":   nv(r["Alert / Monitoring"]),
                "maintenance_support": nv(r["Maintenance Support"]),
                "diagnostic_support": nv(r["Diagnostic Support"]),
                "parts_support":      nv(r["Parts Support"]),
                "dealer_support":     nv(r["Dealer Support"]),
                "description":        nv(r["Description"]),
                "data_class":         nv(r["Data Class"]),
                "source_id":          nv(r["Source ID"]),
                "source_date":        nv(r["Source Date"]),
            }
    data = list(seen.values())
    cypher = """
    MERGE (d:DigitalService {digital_service_id: row.digital_service_id})
    SET d.service_name        = row.service_name,
        d.capability          = row.capability,
        d.machine_data        = row.machine_data,
        d.alert_monitoring    = row.alert_monitoring,
        d.maintenance_support = row.maintenance_support,
        d.diagnostic_support  = row.diagnostic_support,
        d.parts_support       = row.parts_support,
        d.dealer_support      = row.dealer_support,
        d.description         = row.description,
        d.data_class          = row.data_class,
        d.source_id           = row.source_id,
        d.source_date         = row.source_date
    """
    total = batch(session, cypher, data, label="digital_services")
    print(f"  -> digital_services: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 10: Channels (2 nodes — derived from relationships.csv)
# ---------------------------------------------------------------------------

def import_channels(session):
    rows = load("relationships.csv")
    channel_rows = [r for r in rows if nv(r.get("To Entity Type")) == "Channel"]
    channel_ids = list({nv(r["To ID"]) for r in channel_rows if nv(r.get("To ID"))})
    print(f"  channels derived from relationships.csv: {len(channel_ids)} distinct IDs")
    label_map = {
        "CH-DEALER":   "HCME authorised dealer network",
        "CH-EXTERNAL": "External authorised provider (varies by service — see provider_detail on each DELIVERED_BY relationship)",
    }
    data = [{"channel_id": cid, "label": label_map.get(cid)} for cid in channel_ids]
    cypher = """
    MERGE (c:Channel {channel_id: row.channel_id})
    SET c.label = row.label
    """
    total = batch(session, cypher, data, label="channels")
    print(f"  -> channels: {len(data)} nodes merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 11: Machine→Category BELONGS_TO + Category→Category CHILD_OF
# ---------------------------------------------------------------------------

def import_machine_category(session):
    machines = load("machines.csv")
    categories = load("categories.csv")

    # BELONGS_TO (77)
    data_bt = [
        {
            "machine_id":  nv(r["Machine ID"]),
            "category_id": nv(r["Category ID"]),
            "source_id":   nv(r["Source ID"]),
        }
        for r in machines if nv(r.get("Category ID"))
    ]
    cypher_bt = """
    MATCH (m:Machine {machine_id: row.machine_id})
    MATCH (c:Category {category_id: row.category_id})
    MERGE (m)-[r:BELONGS_TO]->(c)
    SET r.source_id = row.source_id
    """
    total = batch(session, cypher_bt, data_bt, label="BELONGS_TO")
    print(f"  -> BELONGS_TO: {len(data_bt)} rels merged ({total} writes)")

    # CHILD_OF (16 — exclude root sentinel)
    data_co = [
        {
            "child_id":  nv(r["Category ID"]),
            "parent_id": nv(r["Parent Category"]),
            "source_id": nv(r["Source ID"]),
        }
        for r in categories
        if nv(r.get("Parent Category")) and nv(r["Parent Category"]) not in ("(root)", "")
    ]
    cypher_co = """
    MATCH (child:Category {category_id: row.child_id})
    MATCH (parent:Category {category_id: row.parent_id})
    MERGE (child)-[r:CHILD_OF]->(parent)
    SET r.source_id = row.source_id
    """
    total = batch(session, cypher_co, data_co, label="CHILD_OF")
    print(f"  -> CHILD_OF: {len(data_co)} rels merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 12: Machine→Specification HAS_SPECIFICATION (1635)
# ---------------------------------------------------------------------------

def import_machine_specification(session):
    rows = load("specifications.csv")
    data = [
        {
            "machine_id": nv(r["Machine ID"]),
            "spec_id":    nv(r["Spec ID"]),
            "data_class": nv(r["Data Class"]),
        }
        for r in rows
    ]
    cypher = """
    MATCH (m:Machine {machine_id: row.machine_id})
    MATCH (s:Specification {spec_id: row.spec_id})
    MERGE (m)-[r:HAS_SPECIFICATION]->(s)
    SET r.data_class = row.data_class
    """
    total = batch(session, cypher, data, label="HAS_SPECIFICATION")
    print(f"  -> HAS_SPECIFICATION: {len(data)} rels merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 13: Machine→Application HAS_APPLICATION (328)
# ---------------------------------------------------------------------------

def import_machine_application(session):
    rows = load("applications.csv")
    data = [
        {
            "machine_id":  nv(r["Machine ID"]),
            "application": nv(r["Application"]),
            "data_class":  nv(r["Data Class"]),
            "confidence":  nv(r["Confidence"]),
            "source_id":   nv(r["Source ID"]),
        }
        for r in rows if nv(r.get("Application"))
    ]
    cypher = """
    MATCH (m:Machine {machine_id: row.machine_id})
    MATCH (a:Application {name: row.application})
    MERGE (m)-[r:HAS_APPLICATION]->(a)
    SET r.data_class = row.data_class,
        r.confidence = row.confidence,
        r.source_id  = row.source_id
    """
    total = batch(session, cypher, data, label="HAS_APPLICATION")
    print(f"  -> HAS_APPLICATION: {len(data)} rels merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 14: Attachment→Machine FITS (14 resolved model-level edges)
# ---------------------------------------------------------------------------

def import_machine_attachment(session):
    # Load the model-code inventory (reports/MODEL_CODE_INVENTORY.csv)
    try:
        inventory = load("MODEL_CODE_INVENTORY.csv", base=REPORTS)
    except FileNotFoundError:
        print("  [WARN] MODEL_CODE_INVENTORY.csv not found in reports/ — skipping FITS edges")
        return

    # Build code -> machine_id lookup
    code_to_machine = {}
    for r in inventory:
        code = nv(r.get("parsed_model_code"))
        mid  = nv(r.get("machine_id"))
        if code and mid:
            code_to_machine[code] = mid

    attachments = load("attachments.csv")
    fits_data = []
    for r in attachments:
        att_id = nv(r["Attachment ID"])
        compat  = nv(r.get("Compatible Machine Model"))
        conf    = nv(r.get("Confidence"))
        src_id  = nv(r.get("Source ID"))
        if not compat:
            continue
        # split on comma/semicolon, trim
        fragments = [x.strip() for x in re.split(r"[,;]", compat)]
        for frag in fragments:
            if frag in code_to_machine:
                fits_data.append({
                    "attachment_id": att_id,
                    "machine_id":    code_to_machine[frag],
                    "evidence":      "MODEL",
                    "confidence":    conf,
                    "source_id":     src_id,
                })

    cypher = """
    MATCH (a:Attachment {attachment_id: row.attachment_id})
    MATCH (m:Machine {machine_id: row.machine_id})
    MERGE (a)-[r:FITS]->(m)
    SET r.evidence   = row.evidence,
        r.confidence = row.confidence,
        r.source_id  = row.source_id
    """
    total = batch(session, cypher, fits_data, label="FITS")
    print(f"  -> FITS: {len(fits_data)} rels merged ({total} writes) [14 expected]")

# ---------------------------------------------------------------------------
# Step 15: Machine→Part HAS_PART_FITMENT (943 valid)
# ---------------------------------------------------------------------------

def import_machine_part_fitment(session):
    rows = load("machine_part_fitment.csv")
    # Exclude sentinel
    data = [
        {
            "machine_id":           nv(r["Machine ID"]),
            "part_id":              nv(r["Part ID"]),
            "fitment_id":           nv(r["Fitment ID"]),
            "evidence":             nv(r.get("evidence")),
            "evidence_original":    nv(r.get("evidence_original")),
            "fitment_type":         nv(r.get("Fitment Type")),
            "assembly":             nv(r.get("Assembly")),
            "installation_context": nv(r.get("Installation Context")),
            "position_location":    nv(r.get("Position / Location")),
            "data_class":           nv(r.get("Data Class")),
            "source_id":            nv(r.get("Source ID")),
            "confidence":           nv(r.get("Confidence")),
        }
        for r in rows
        if nv(r.get("Machine ID")) != "NOT IN CURRENT CATALOGUE"
    ]
    cypher = """
    MATCH (m:Machine {machine_id: row.machine_id})
    MATCH (p:Part {part_id: row.part_id})
    MERGE (m)-[r:HAS_PART_FITMENT {fitment_id: row.fitment_id}]->(p)
    SET r.evidence            = row.evidence,
        r.evidence_original   = row.evidence_original,
        r.fitment_type        = row.fitment_type,
        r.assembly            = row.assembly,
        r.installation_context = row.installation_context,
        r.position_location   = row.position_location,
        r.data_class          = row.data_class,
        r.source_id           = row.source_id,
        r.confidence          = row.confidence
    """
    total = batch(session, cypher, data, label="HAS_PART_FITMENT")
    print(f"  -> HAS_PART_FITMENT: {len(data)} rels merged ({total} writes) [943 expected]")

# ---------------------------------------------------------------------------
# Step 16: Machine→Service HAS_SERVICE (1694)
# ---------------------------------------------------------------------------

def import_machine_service(session):
    rows = load("machine_service.csv")
    data = [
        {
            "machine_id":             nv(r["Machine ID"]),
            "service_id":             nv(r["Service ID"]),
            "applicability":          nv(r.get("applicability")),
            "applicability_original": nv(r.get("applicability_original")),
            "service_type":           nv(r.get("Service Type")),
            "service_location":       nv(r.get("Service Location")),
            "trigger":                nv(r.get("Trigger")),
            "interval_officially_stated": nv(r.get("Interval (officially stated)")),
            "data_class":             nv(r.get("Data Class")),
            "source_id":              nv(r.get("Source ID")),
            "confidence":             nv(r.get("Confidence")),
        }
        for r in rows
    ]
    cypher = """
    MATCH (m:Machine {machine_id: row.machine_id})
    MATCH (s:Service {service_id: row.service_id})
    MERGE (m)-[r:HAS_SERVICE]->(s)
    SET r.applicability              = row.applicability,
        r.applicability_original     = row.applicability_original,
        r.service_type               = row.service_type,
        r.service_location           = row.service_location,
        r.trigger                    = row.trigger,
        r.interval_officially_stated = row.interval_officially_stated,
        r.data_class                 = row.data_class,
        r.source_id                  = row.source_id,
        r.confidence                 = row.confidence
    """
    total = batch(session, cypher, data, label="HAS_SERVICE")
    print(f"  -> HAS_SERVICE: {len(data)} rels merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 17: Service→Part REQUIRES_PART (11)
# ---------------------------------------------------------------------------

def import_service_part_requirement(session):
    rows = load("service_part_requirements.csv")
    data = [
        {
            "service_id":         nv(r["Service ID"]),
            "part_id":            nv(r["Part ID"]),
            "requirement_id":     nv(r["Requirement ID"]),
            "quantity":           nv(r.get("Quantity")),
            "mandatory_optional": nv(r.get("Mandatory / Optional")),
            "consumable_wear_replacement": nv(r.get("Consumable / Wear / Replacement")),
            "data_class":         nv(r.get("Data Class")),
            "source_id":          nv(r.get("Source ID")),
            "confidence":         nv(r.get("Confidence")),
        }
        for r in rows
    ]
    cypher = """
    MATCH (s:Service {service_id: row.service_id})
    MATCH (p:Part {part_id: row.part_id})
    MERGE (s)-[r:REQUIRES_PART {requirement_id: row.requirement_id}]->(p)
    SET r.quantity                    = row.quantity,
        r.mandatory_optional          = row.mandatory_optional,
        r.consumable_wear_replacement = row.consumable_wear_replacement,
        r.data_class                  = row.data_class,
        r.source_id                   = row.source_id,
        r.confidence                  = row.confidence
    """
    total = batch(session, cypher, data, label="REQUIRES_PART")
    print(f"  -> REQUIRES_PART: {len(data)} rels merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 18: Machine→DigitalService HAS_DIGITAL_SERVICE (616)
# ---------------------------------------------------------------------------

def import_machine_digital_service(session):
    rows = load("digital_services.csv")
    data = [
        {
            "machine_id":       nv(r["Machine ID"]),
            "digital_service_id": nv(r["Digital Service ID"]),
            "applicability":    nv(r.get("Applicability")),
            "data_class":       nv(r.get("Data Class")),
            "source_id":        nv(r.get("Source ID")),
        }
        for r in rows
    ]
    cypher = """
    MATCH (m:Machine {machine_id: row.machine_id})
    MATCH (d:DigitalService {digital_service_id: row.digital_service_id})
    MERGE (m)-[r:HAS_DIGITAL_SERVICE]->(d)
    SET r.applicability = row.applicability,
        r.data_class    = row.data_class,
        r.source_id     = row.source_id
    """
    total = batch(session, cypher, data, label="HAS_DIGITAL_SERVICE")
    print(f"  -> HAS_DIGITAL_SERVICE: {len(data)} rels merged ({total} writes)")

# ---------------------------------------------------------------------------
# Step 19: Channel relationships (DELIVERED_BY 23, NOTIFIES 2, SUPPORTS 2,
#           INTEGRATES 1, AFFECTS_MAINTENANCE_OF 1)
# ---------------------------------------------------------------------------

def import_channel_relationships(session):
    rows = load("relationships.csv")

    # DELIVERED_BY — Service→Channel
    def_rows = [
        {
            "from_id":            nv(r["From ID"]),
            "to_id":              nv(r["To ID"]),
            "relationship_class": nv(r.get("relationship_class")),
            "provider_detail":    nv(r.get("To Name")),
            "data_class":         nv(r.get("Data Class")),
            "source_id":          nv(r.get("Source ID")),
        }
        for r in rows if nv(r.get("Relationship")) == "DELIVERED_BY"
    ]
    c = batch(session, """
    MATCH (s:Service {service_id: row.from_id})
    MATCH (c:Channel {channel_id: row.to_id})
    MERGE (s)-[r:DELIVERED_BY]->(c)
    SET r.relationship_class = row.relationship_class,
        r.provider_detail    = row.provider_detail,
        r.data_class         = row.data_class,
        r.source_id          = row.source_id
    """, def_rows, label="DELIVERED_BY")
    print(f"  -> DELIVERED_BY: {len(def_rows)} rels merged ({c} writes) [23 expected]")

    # NOTIFIES — DigitalService→Channel
    not_rows = [
        {
            "from_id":            nv(r["From ID"]),
            "to_id":              nv(r["To ID"]),
            "relationship_class": nv(r.get("relationship_class")),
            "data_class":         nv(r.get("Data Class")),
            "source_id":          nv(r.get("Source ID")),
        }
        for r in rows if nv(r.get("Relationship")) == "NOTIFIES"
    ]
    c = batch(session, """
    MATCH (d:DigitalService {digital_service_id: row.from_id})
    MATCH (c:Channel {channel_id: row.to_id})
    MERGE (d)-[r:NOTIFIES]->(c)
    SET r.relationship_class = row.relationship_class,
        r.data_class         = row.data_class,
        r.source_id          = row.source_id
    """, not_rows, label="NOTIFIES")
    print(f"  -> NOTIFIES: {len(not_rows)} rels merged ({c} writes) [2 expected]")

    # SUPPORTS — DigitalService→Service
    sup_rows = [
        {
            "from_id":            nv(r["From ID"]),
            "to_id":              nv(r["To ID"]),
            "relationship_class": nv(r.get("relationship_class")),
            "data_class":         nv(r.get("Data Class")),
            "source_id":          nv(r.get("Source ID")),
        }
        for r in rows if nv(r.get("Relationship")) == "SUPPORTS"
    ]
    c = batch(session, """
    MATCH (d:DigitalService {digital_service_id: row.from_id})
    MATCH (s:Service {service_id: row.to_id})
    MERGE (d)-[r:SUPPORTS]->(s)
    SET r.relationship_class = row.relationship_class,
        r.data_class         = row.data_class,
        r.source_id          = row.source_id
    """, sup_rows, label="SUPPORTS")
    print(f"  -> SUPPORTS: {len(sup_rows)} rels merged ({c} writes) [2 expected]")

    # INTEGRATES — DigitalService→DigitalService
    int_rows = [
        {
            "from_id":            nv(r["From ID"]),
            "to_id":              nv(r["To ID"]),
            "relationship_class": nv(r.get("relationship_class")),
            "data_class":         nv(r.get("Data Class")),
            "source_id":          nv(r.get("Source ID")),
        }
        for r in rows if nv(r.get("Relationship")) == "INTEGRATES"
    ]
    c = batch(session, """
    MATCH (from:DigitalService {digital_service_id: row.from_id})
    MATCH (to:DigitalService {digital_service_id: row.to_id})
    MERGE (from)-[r:INTEGRATES]->(to)
    SET r.relationship_class = row.relationship_class,
        r.data_class         = row.data_class,
        r.source_id          = row.source_id
    """, int_rows, label="INTEGRATES")
    print(f"  -> INTEGRATES: {len(int_rows)} rels merged ({c} writes) [1 expected]")

    # AFFECTS_MAINTENANCE_OF — Attachment→Part
    aff_rows = [
        {
            "from_id":            nv(r["From ID"]),
            "to_id":              nv(r["To ID"]),
            "relationship_class": nv(r.get("relationship_class")),
            "data_class":         nv(r.get("Data Class")),
            "source_id":          nv(r.get("Source ID")),
        }
        for r in rows if nv(r.get("Relationship")) == "AFFECTS_MAINTENANCE_OF"
    ]
    c = batch(session, """
    MATCH (a:Attachment {attachment_id: row.from_id})
    MATCH (p:Part {part_id: row.to_id})
    MERGE (a)-[r:AFFECTS_MAINTENANCE_OF]->(p)
    SET r.relationship_class = row.relationship_class,
        r.data_class         = row.data_class,
        r.source_id          = row.source_id
    """, aff_rows, label="AFFECTS_MAINTENANCE_OF")
    print(f"  -> AFFECTS_MAINTENANCE_OF: {len(aff_rows)} rels merged ({c} writes) [1 expected]")

# ---------------------------------------------------------------------------
# Step 20: Maintenance list properties on Part
# WARNING: NOT idempotent — re-running duplicates list entries.
# ---------------------------------------------------------------------------

def import_maintenance(session):
    rows = load("maintenance.csv")
    # Build (part_name_fragment, maintenance_data) pairs
    part_updates = []
    for r in rows:
        req = nv(r.get("Required Part"))
        if not req:
            continue
        # split on semicolons, strip trailing parenthetical qualifiers
        fragments = [re.split(r"\(", trim_x)[0].strip()
                     for trim_x in (x.strip() for x in req.split(";"))
                     if trim_x]
        for frag in fragments:
            if frag:
                part_updates.append({
                    "part_name_fragment":   frag.lower(),
                    "maintenance_id":        nv(r.get("Maintenance ID")),
                    "maintenance_activity":  nv(r.get("Maintenance Activity")),
                    "interval":              nv(r.get("Interval")),
                    "interval_unit":         nv(r.get("Interval Unit")),
                    "applies_to":            nv(r.get("Applies To (as stated)")),
                    "component":             nv(r.get("Component")),
                    "data_class":            nv(r.get("Data Class")),
                    "source_id":             nv(r.get("Source ID")),
                    "confidence":            nv(r.get("Confidence")),
                })

    # Process one at a time (each needs a fuzzy CONTAINS match)
    total_writes = 0
    matched_parts = set()
    for upd in part_updates:
        result = session.run("""
        MATCH (p:Part) WHERE toLower(p.part_name) CONTAINS $frag
        SET p.maintenance_ids              = coalesce(p.maintenance_ids, [])           + $maintenance_id,
            p.maintenance_activities       = coalesce(p.maintenance_activities, [])    + $maintenance_activity,
            p.maintenance_intervals        = coalesce(p.maintenance_intervals, [])     + $interval,
            p.maintenance_interval_units   = coalesce(p.maintenance_interval_units,[]) + $interval_unit,
            p.maintenance_applies_to       = coalesce(p.maintenance_applies_to, [])    + $applies_to,
            p.maintenance_components       = coalesce(p.maintenance_components, [])    + $component,
            p.maintenance_data_classes     = coalesce(p.maintenance_data_classes, [])  + $data_class,
            p.maintenance_source_ids       = coalesce(p.maintenance_source_ids, [])    + $source_id,
            p.maintenance_confidences      = coalesce(p.maintenance_confidences, [])   + $confidence
        RETURN p.part_id AS pid
        """, {
            "frag":                upd["part_name_fragment"],
            "maintenance_id":      upd["maintenance_id"],
            "maintenance_activity": upd["maintenance_activity"],
            "interval":            upd["interval"],
            "interval_unit":       upd["interval_unit"],
            "applies_to":          upd["applies_to"],
            "component":           upd["component"],
            "data_class":          upd["data_class"],
            "source_id":           upd["source_id"],
            "confidence":          upd["confidence"],
        })
        pids = [rec["pid"] for rec in result]
        matched_parts.update(pids)
        total_writes += len(pids) * 9  # 9 props per match

    print(f"  -> Maintenance: {len(part_updates)} guideline entries applied to {len(matched_parts)} Part(s) ({total_writes} approx writes)")

# ---------------------------------------------------------------------------
# Step 21: Indexes
# ---------------------------------------------------------------------------

INDEXES = [
    "CREATE INDEX part_number_lookup IF NOT EXISTS FOR (n:Part) ON (n.part_number)",
    "CREATE INDEX part_name_lookup IF NOT EXISTS FOR (n:Part) ON (n.part_name)",
    "CREATE INDEX machine_model_lookup IF NOT EXISTS FOR (n:Machine) ON (n.model)",
    "CREATE INDEX machine_category_lookup IF NOT EXISTS FOR (n:Machine) ON (n.machine_category)",
    "CREATE INDEX service_name_lookup IF NOT EXISTS FOR (n:Service) ON (n.service_name)",
    "CREATE INDEX attachment_name_lookup IF NOT EXISTS FOR (n:Attachment) ON (n.attachment_name)",
    "CREATE INDEX category_name_lookup IF NOT EXISTS FOR (n:Category) ON (n.category_name)",
]

# ---------------------------------------------------------------------------
# Final count verification
# ---------------------------------------------------------------------------

def verify_counts(session):
    print("\n=== Final count verification ===")
    expected = {
        "Category":      17,
        "Machine":       77,
        "Specification": 1635,
        "Application":   29,
        "Attachment":    17,
        "Part":          43,
        "Service":       22,
        "DigitalService": 8,
        "Channel":       2,
    }
    all_pass = True
    for label, exp in expected.items():
        result = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        cnt = result.single()["cnt"]
        status = "PASS" if cnt == exp else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {label}: {cnt} (expected {exp})")

    rel_expected = {
        "BELONGS_TO":          77,
        "CHILD_OF":            16,
        "HAS_SPECIFICATION":   1635,
        "HAS_APPLICATION":     328,
        "HAS_PART_FITMENT":    943,
        "HAS_SERVICE":         1694,
        "REQUIRES_PART":       11,
        "HAS_DIGITAL_SERVICE": 616,
        "DELIVERED_BY":        23,
        "NOTIFIES":            2,
        "SUPPORTS":            2,
        "INTEGRATES":          1,
        "AFFECTS_MAINTENANCE_OF": 1,
        "FITS":                14,
    }
    for rel_type, exp in rel_expected.items():
        result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS cnt")
        cnt = result.single()["cnt"]
        status = "PASS" if cnt == exp else "WARN"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] :{rel_type}: {cnt} (expected {exp})")

    if all_pass:
        print("\n✅ All node counts verified. Graph import complete.")
    else:
        print("\n⚠️  Some counts differ — review output above.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HCME After-Sales Aura import")
    parser.add_argument("--dry-run", action="store_true",
                        help="Read and count CSVs only — do not connect to Aura or write anything")
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN — no Aura connection, no writes ===")
        for fname in [
            "categories.csv", "machines.csv", "specifications.csv",
            "applications.csv", "attachments.csv", "parts.csv",
            "services.csv", "digital_services.csv",
            "machine_part_fitment.csv", "machine_service.csv",
            "service_part_requirements.csv", "maintenance.csv",
            "relationships.csv",
        ]:
            rows = load(fname)
            print(f"  {fname}: {len(rows)} rows — OK")
        print("Dry run complete. All CSV files readable.")
        return

    print("Connecting to Neo4j Aura...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("Connected.\n")

    with driver.session(database=DATABASE) as session:
        # Safety check — refuse to run if DB is not empty
        node_count = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
        if node_count > 0:
            print(f"[ABORT] Database already contains {node_count} node(s). "
                  "This import is designed for a clean database.\n"
                  "Run with --force to override (not recommended).")
            driver.close()
            sys.exit(1)

        print("=== Step 1: Constraints ===")
        for cq in CONSTRAINTS:
            session.run(cq)
        print(f"  -> {len(CONSTRAINTS)} constraints created")

        print("\n=== Steps 2-10: Nodes ===")
        import_categories(session)
        import_machines(session)
        import_specifications(session)
        import_applications(session)
        import_attachments(session)
        import_parts(session)
        import_services(session)
        import_digital_services(session)
        import_channels(session)

        print("\n=== Steps 11-20: Relationships ===")
        import_machine_category(session)
        import_machine_specification(session)
        import_machine_application(session)
        import_machine_attachment(session)
        import_machine_part_fitment(session)
        import_machine_service(session)
        import_service_part_requirement(session)
        import_machine_digital_service(session)
        import_channel_relationships(session)
        import_maintenance(session)

        print("\n=== Step 21: Indexes ===")
        for iq in INDEXES:
            session.run(iq)
        print(f"  -> {len(INDEXES)} indexes created")

        verify_counts(session)

    driver.close()


if __name__ == "__main__":
    main()
