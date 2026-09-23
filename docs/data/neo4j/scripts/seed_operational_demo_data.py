#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs/data/neo4j/scripts/seed_operational_demo_data.py

Builds the synthetic-but-honestly-labeled operational/commercial context
layer described in
docs/research/HCME_EUROPE_OPERATIONAL_DATA_AND_KPI_FOUNDATION.md, around the
REAL HCME Europe Part + DealerBranch graph. Connects to the SAME single Neo4j
graph used by the rest of the app (no separate database).

Absolute rule enforced throughout this script: every node this script writes
that is NOT a verified real HCME fact carries BOTH `synthetic = true` and
`data_source = "SYNTHETIC_DEMO"`. The one real node this script writes (the
Oosterhout Depot) carries real provenance fields instead (source_id,
confidence, data_class, source_date, record_class) and `synthetic = false`.

Idempotent: every write is a MERGE keyed on a stable id, so re-running this
script does not create duplicates (verified in
backend/tests/test_operational_demo_seed.py).

Never mutates: (:Part) fields, (:DealerBranch) fields, (:Machine) fields, any
Phase 6 Allocation/Order/FulfilmentRequest/FulfilmentOption node written by
the real application code paths (backend/app/modules/{allocation,order,
fulfilment,availability}/*). This script only MERGEs its OWN new demo node
ids (fr-demo-*, fo-demo-*, alloc-demo-*, order-demo-*, ship-demo-*, etc.),
which never collide with real ids (real Order ids are `order-<uuid4>`, real
Allocation/FulfilmentRequest/FulfilmentOption ids come from the live
services) and reuses existing real Part/DealerBranch nodes strictly via
MATCH, never CREATE.

Run:
    python docs/data/neo4j/scripts/seed_operational_demo_data.py
    python docs/data/neo4j/scripts/seed_operational_demo_data.py --dry-run
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

# Real parts used for demo scenarios (well-provenanced SRC-039 battery
# family, deliberately NOT PT-054..PT-060 which carry the flagged/unresolved
# SRC-042 provenance mismatch reported in
# docs/research/HCME_EUROPE_PARTS_AND_DEALER_DATA_RESEARCH.md).
PART_1 = "PT-001"  # 4663907 Battery - Starter, Lighting & Ignition
PART_2 = "PT-002"  # 4621541 Battery - Starter, Lighting & Ignition
PART_3 = "PT-010"  # YA60106848 Battery - Traction (Industrial)

DEALER_NL = "DLR-019"  # Danny Bergmans, NL — intra-EU demo destination
DEALER_GB = "DLR-001"  # AC Plant Sales, GB — post-Brexit customs demo destination

SCHEMA_STATEMENTS = [
    "CREATE CONSTRAINT Depot_id IF NOT EXISTS FOR (n:Depot) REQUIRE n.depot_id IS UNIQUE",
    "CREATE CONSTRAINT Supplier_id IF NOT EXISTS FOR (n:Supplier) REQUIRE n.supplier_id IS UNIQUE",
    "CREATE CONSTRAINT CatalogEntry_id IF NOT EXISTS FOR (n:CatalogEntry) REQUIRE n.catalog_entry_id IS UNIQUE",
    "CREATE CONSTRAINT InventorySnapshot_id IF NOT EXISTS FOR (n:InventorySnapshot) REQUIRE n.snapshot_id IS UNIQUE",
    "CREATE CONSTRAINT Shipment_id IF NOT EXISTS FOR (n:Shipment) REQUIRE n.shipment_id IS UNIQUE",
    "CREATE CONSTRAINT CustomsContext_id IF NOT EXISTS FOR (n:CustomsContext) REQUIRE n.customs_context_id IS UNIQUE",
]

# ---------------------------------------------------------------------------
# 1. REAL — one Depot node, existence + published facility facts only.
#    Source: SRC-050 (docs/data/neo4j/data/provenance.csv), HCME's own Onsite
#    news article, published 2024-07-09, verified live via browser fetch on
#    2026-09-23. NOT live inventory — no stock-by-part figures are published
#    and none are asserted here.
# ---------------------------------------------------------------------------
DEPOT_CYPHER = """
MERGE (d:Depot {depot_id: 'DEPOT-OOSTERHOUT'})
SET d.name = 'Hitachi European Parts Centre',
    d.city = 'Oosterhout',
    d.country = 'NL',
    d.building_area_m2 = 28000,
    d.storage_locations = 110000,
    d.storage_locations_pre_upgrade = 73000,
    d.stocked_parts_count_2024 = 80000,
    d.stocked_parts_count_2015 = 68800,
    d.logistics_partner = 'Neovia',
    d.dispatch_to_dealer_claim = 'Parts ordered via a local dealer are dispatched from this depot within 24 hours (per source article)',
    d.published_date = '2024-07-09',
    d.record_class = 'DEPOT_FACILITY',
    d.data_class = 'OFFICIAL WEBSITE DATA',
    d.source_id = 'SRC-050',
    d.confidence = 'HIGH',
    d.source_date = '2026-09-23',
    d.synthetic = false,
    d.note = 'Facility existence and published facility-level facts only (size, storage-location count, historical stocked-SKU counts as of the article date). This is NOT a live inventory feed and no per-part stock levels are asserted from this node.'
"""

# ---------------------------------------------------------------------------
# 2. SYNTHETIC — Suppliers (Part 11: no real HCME-published supplier data
#    exists; these exist only to give the synthetic supply-chain KPI demo a
#    non-Depot source option).
# ---------------------------------------------------------------------------
SUPPLIER_CYPHER = """
UNWIND $rows AS row
MERGE (s:Supplier {supplier_id: row.id})
SET s.name = row.name,
    s.country = row.country,
    s.synthetic = true,
    s.data_source = 'SYNTHETIC_DEMO',
    s.record_class = 'DEMO_SUPPLIER',
    s.note = 'Synthetic demo supplier — no real HCME-published third-party supplier data exists (see docs/research/HCME_PRICING_ORDER_INTEGRATION_RESEARCH.md Part 11).'
"""
SUPPLIERS = [
    {"id": "SUP-DEMO-001", "name": "Demo European Logistics Partner A", "country": "DE"},
    {"id": "SUP-DEMO-002", "name": "Demo European Logistics Partner B", "country": "BE"},
]

# ---------------------------------------------------------------------------
# 3. SYNTHETIC — CatalogEntry nodes (KPI 2 cross-catalog + KPI 4 master-data
#    consistency). No real cross-catalog/supersession evidence beyond what
#    prior research already found (none new) -> demo relationships only,
#    explicitly labeled.
# ---------------------------------------------------------------------------
CATALOG_CYPHER = """
UNWIND $rows AS row
MATCH (p:Part {part_id: row.part_id})
MERGE (c:CatalogEntry {catalog_entry_id: row.id})
SET c.catalog_name = row.catalog_name,
    c.catalog_part_number = row.catalog_part_number,
    c.description = row.description,
    c.category = row.category,
    c.synthetic = true,
    c.data_source = 'SYNTHETIC_DEMO',
    c.record_class = 'DEMO_CATALOG_ENTRY',
    c.note = 'SYNTHETIC DEMO DATA — demonstrates cross-catalog matching and master-data consistency reasoning only. Not a real third-party catalogue.'
MERGE (c)-[rel:%s {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(p)
"""
CATALOG_ENTRIES = [
    # CAT-DEMO-001: near-identical to PT-001 -> expect MATCH
    {"id": "CAT-DEMO-001", "part_id": PART_1, "catalog_name": "Demo Partner Catalogue A",
     "catalog_part_number": "4663907", "description": "Battery - Starter, Lighting & Ignition",
     "category": "Electrical", "rel": "CROSS_REFERENCES"},
    # CAT-DEMO-002: stylistic wording diff from PT-002 -> expect MINOR_DIFFERENCE
    {"id": "CAT-DEMO-002", "part_id": PART_2, "catalog_name": "Demo Partner Catalogue A",
     "catalog_part_number": "4621541-ALT", "description": "SLI Battery, 12V starting/lighting/ignition",
     "category": "Electrical", "rel": "CROSS_REFERENCES"},
    # CAT-DEMO-003: meaningfully different category/description vs PT-001 -> expect SIGNIFICANT_DIFFERENCE
    {"id": "CAT-DEMO-003", "part_id": PART_1, "catalog_name": "Demo Partner Catalogue B",
     "catalog_part_number": "AFTM-9981", "description": "Generic aftermarket hydraulic filter element",
     "category": "Filtration", "rel": "ALTERNATIVE_FOR"},
]

# ---------------------------------------------------------------------------
# 4. SYNTHETIC — InventorySnapshot (Part 3/4). Deliberately its own label,
#    NOT InventoryCache/InventoryLedger (those are Phase 6's real live-flow
#    node types read by app/modules/availability + app/integrations — never
#    write demo data into them, or Phase 6 reads would treat it as real).
# ---------------------------------------------------------------------------
INVENTORY_CYPHER = """
UNWIND $rows AS row
MATCH (p:Part {part_id: row.part_id})
MERGE (i:InventorySnapshot {snapshot_id: row.id})
SET i.location_type = row.location_type,
    i.location_id = row.location_id,
    i.quantity = row.quantity,
    i.as_of = row.as_of,
    i.synthetic = true,
    i.data_source = 'SYNTHETIC_DEMO',
    i.record_class = 'DEMO_INVENTORY_SNAPSHOT',
    i.note = 'SYNTHETIC DEMO DATA — no real HCME per-part stock levels are public (see docs/research/HCME_PRICING_ORDER_INTEGRATION_RESEARCH.md).'
MERGE (p)-[:HAS_SYNTHETIC_INVENTORY {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(i)
"""
INVENTORY_SNAPSHOTS = [
    {"id": "INV-DEMO-001", "part_id": PART_1, "location_type": "DEPOT", "location_id": "DEPOT-OOSTERHOUT", "quantity": 17, "as_of": "2026-09-23"},
    {"id": "INV-DEMO-002", "part_id": PART_2, "location_type": "DEALER", "location_id": DEALER_NL, "quantity": 4, "as_of": "2026-09-23"},
    {"id": "INV-DEMO-003", "part_id": PART_3, "location_type": "SUPPLIER", "location_id": "SUP-DEMO-001", "quantity": 0, "as_of": "2026-09-23"},
]

# ---------------------------------------------------------------------------
# 5. SYNTHETIC — full order-traceability chains (KPI 1 / KPI 3), reusing the
#    EXISTING Order/Allocation/FulfilmentRequest/FulfilmentOption labels and
#    the real CREATED/ACCEPTED/CANCELLED state vocabulary documented in
#    backend/app/modules/order/service.py, rather than inventing a parallel
#    schema. Every node/rel below carries synthetic=true + data_source, and
#    every id uses a `-demo-` infix that can never collide with a real id
#    (real Order ids are `order-<uuid4>`; real Allocation/FulfilmentRequest/
#    FulfilmentOption ids are minted by the live services, never this
#    pattern). No Phase 6 service function is called — these are direct,
#    inert graph writes; they never touch the live allocation ledger,
#    inventory cache, or idempotency store.
# ---------------------------------------------------------------------------
ORDER_CHAIN_CYPHER = """
UNWIND $rows AS row
MATCH (p:Part {part_id: row.part_id})
MATCH (dest:DealerBranch {dealer_id: row.dealer_id})
MERGE (fr:FulfilmentRequest {id: row.fr_id})
SET fr.partNumber = p.part_number, fr.quantity = row.quantity,
    fr.destinationBranchId = row.dealer_id, fr.status = row.fr_status,
    fr.synthetic = true, fr.data_source = 'SYNTHETIC_DEMO'
MERGE (fo:FulfilmentOption {id: row.fo_id})
SET fo.fulfilmentRequestId = row.fr_id, fo.sourceId = row.source_id,
    fo.sourceType = row.source_type, fo.destinationBranchId = row.dealer_id,
    fo.isSelected = true, fo.synthetic = true, fo.data_source = 'SYNTHETIC_DEMO'
MERGE (a:Allocation {id: row.alloc_id})
SET a.fulfilmentRequestId = row.fr_id, a.partNumber = p.part_number,
    a.sourceId = row.source_id, a.quantity = row.quantity, a.status = row.alloc_status,
    a.synthetic = true, a.data_source = 'SYNTHETIC_DEMO'
MERGE (o:Order {id: row.order_id})
SET o.fulfilmentRequestId = row.fr_id, o.partNumber = p.part_number,
    o.quantity = row.quantity, o.sourceId = row.source_id,
    o.destinationBranchId = row.dealer_id, o.status = row.order_status,
    o.unitPrice = null, o.currency = null, o.pricingStatus = 'NOT_AVAILABLE',
    o.provenance = 'SYNTHETIC_DEMO_KPI_WORKFLOW',
    o.synthetic = true, o.data_source = 'SYNTHETIC_DEMO'
MERGE (fr)-[:HAS_ALLOCATION {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(a)
MERGE (fr)-[:HAS_ORDER {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(o)
MERGE (o)-[:BASED_ON_ALLOCATION {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(a)
MERGE (o)-[:FOR_PART {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(p)
WITH o, a, row
CALL {
    WITH a, row
    WITH a, row WHERE row.source_type = 'DEPOT'
    MATCH (dep:Depot {depot_id: row.source_id})
    MERGE (a)-[:SOURCED_FROM {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(dep)
}
CALL {
    WITH a, row
    WITH a, row WHERE row.source_type = 'SUPPLIER'
    MATCH (sup:Supplier {supplier_id: row.source_id})
    MERGE (a)-[:SOURCED_FROM {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(sup)
}
RETURN o.id
"""

SHIPMENT_CYPHER = """
UNWIND $rows AS row
MATCH (o:Order {id: row.order_id})
MATCH (dest:DealerBranch {dealer_id: row.dealer_id})
MERGE (sh:Shipment {shipment_id: row.shipment_id})
SET sh.status = row.status, sh.carrier = row.carrier, sh.tracking_number = row.tracking_number,
    sh.origin = row.origin, sh.destination = row.destination, sh.eta = row.eta,
    sh.shipped_at = row.shipped_at, sh.delivered_at = row.delivered_at,
    sh.synthetic = true, sh.data_source = 'SYNTHETIC_DEMO',
    sh.note = 'SYNTHETIC DEMO DATA — Phase 7 (production shipment/tracking) is not implemented; this node exists for KPI/graph demonstration only.'
MERGE (o)-[:HAS_SHIPMENT {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(sh)
MERGE (sh)-[:SHIPPED_TO {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(dest)
"""

CUSTOMS_CYPHER = """
UNWIND $rows AS row
MATCH (sh:Shipment {shipment_id: row.shipment_id})
MERGE (cc:CustomsContext {customs_context_id: row.id})
SET cc.origin_country = row.origin_country, cc.destination_country = row.destination_country,
    cc.hs_code = row.hs_code, cc.requires_declaration = row.requires_declaration,
    cc.customs_status = row.customs_status, cc.flag_reason = row.flag_reason,
    cc.synthetic = true, cc.data_source = 'SYNTHETIC_DEMO',
    cc.note = 'SYNTHETIC DEMO DATA — no real HCME shipment customs data exists; illustrates the customs-flag reasoning pattern only.'
MERGE (sh)-[:HAS_CUSTOMS_CONTEXT {synthetic: true, data_source: 'SYNTHETIC_DEMO'}]->(cc)
"""

ORDER_CHAINS = [
    {  # ORD-DEMO-001: intra-EU (NL->NL), fully delivered, sourced from real Depot
        "fr_id": "fr-demo-001", "fo_id": "fo-demo-001", "alloc_id": "alloc-demo-001", "order_id": "order-demo-001",
        "part_id": PART_1, "dealer_id": DEALER_NL, "quantity": 2,
        "source_id": "DEPOT-OOSTERHOUT", "source_type": "DEPOT",
        "fr_status": "ORDERED", "alloc_status": "CONSUMED", "order_status": "ACCEPTED",
    },
    {  # ORD-DEMO-002: cross-border NL->GB, shipped but not yet delivered, customs flagged
        "fr_id": "fr-demo-002", "fo_id": "fo-demo-002", "alloc_id": "alloc-demo-002", "order_id": "order-demo-002",
        "part_id": PART_2, "dealer_id": DEALER_GB, "quantity": 1,
        "source_id": "DEPOT-OOSTERHOUT", "source_type": "DEPOT",
        "fr_status": "ORDERED", "alloc_status": "CONSUMED", "order_status": "ACCEPTED",
    },
    {  # ORD-DEMO-003: cancelled before shipment, sourced from a synthetic Supplier
        "fr_id": "fr-demo-003", "fo_id": "fo-demo-003", "alloc_id": "alloc-demo-003", "order_id": "order-demo-003",
        "part_id": PART_3, "dealer_id": DEALER_NL, "quantity": 1,
        "source_id": "SUP-DEMO-001", "source_type": "SUPPLIER",
        "fr_status": "CANCELLED", "alloc_status": "RELEASED", "order_status": "CANCELLED",
    },
]

SHIPMENTS = [
    {"shipment_id": "ship-demo-001", "order_id": "order-demo-001", "dealer_id": DEALER_NL,
     "status": "DELIVERED", "carrier": "Demo Carrier Logistics", "tracking_number": "DEMO-TRACK-0001",
     "origin": "Oosterhout, NL", "destination": "Netherlands (Danny Bergmans dealer branch)",
     "eta": "2026-09-20", "shipped_at": "2026-09-18T09:00:00Z", "delivered_at": "2026-09-20T14:30:00Z"},
    {"shipment_id": "ship-demo-002", "order_id": "order-demo-002", "dealer_id": DEALER_GB,
     "status": "SHIPPED", "carrier": "Demo Carrier Logistics", "tracking_number": "DEMO-TRACK-0002",
     "origin": "Oosterhout, NL", "destination": "United Kingdom (AC Plant Sales dealer branch)",
     "eta": "2026-09-28", "shipped_at": "2026-09-23T10:00:00Z", "delivered_at": None},
]

CUSTOMS = [
    {"id": "CUST-DEMO-001", "shipment_id": "ship-demo-002", "origin_country": "NL", "destination_country": "GB",
     "hs_code": "8507.10", "requires_declaration": True, "customs_status": "PENDING_DECLARATION",
     "flag_reason": "Destination (GB) is outside the EU customs union — a customs declaration is required for this cross-border shipment."},
]


def run(dry_run: bool = False):
    driver = GraphDatabase.driver(URI, auth=(USER, PW))
    with driver.session(database=DB) as s:
        if dry_run:
            print("DRY RUN — no writes will be made.")
            print(f"Would MERGE: 1 Depot, {len(SUPPLIERS)} Suppliers, {len(CATALOG_ENTRIES)} CatalogEntries, "
                  f"{len(INVENTORY_SNAPSHOTS)} InventorySnapshots, {len(ORDER_CHAINS)} Order chains, "
                  f"{len(SHIPMENTS)} Shipments, {len(CUSTOMS)} CustomsContexts.")
            driver.close()
            return

        for stmt in SCHEMA_STATEMENTS:
            s.run(stmt).consume()

        s.run(DEPOT_CYPHER).consume()
        print("Depot (real): 1 MERGEd")

        s.run(SUPPLIER_CYPHER, {"rows": SUPPLIERS}).consume()
        print(f"Supplier (synthetic): {len(SUPPLIERS)} MERGEd")

        for entry in CATALOG_ENTRIES:
            cypher = CATALOG_CYPHER % entry["rel"]
            s.run(cypher, {"rows": [entry]}).consume()
        print(f"CatalogEntry (synthetic): {len(CATALOG_ENTRIES)} MERGEd")

        s.run(INVENTORY_CYPHER, {"rows": INVENTORY_SNAPSHOTS}).consume()
        print(f"InventorySnapshot (synthetic): {len(INVENTORY_SNAPSHOTS)} MERGEd")

        s.run(ORDER_CHAIN_CYPHER, {"rows": ORDER_CHAINS}).consume()
        print(f"Order traceability chains (synthetic): {len(ORDER_CHAINS)} MERGEd "
              f"(FulfilmentRequest/FulfilmentOption/Allocation/Order per chain)")

        s.run(SHIPMENT_CYPHER, {"rows": SHIPMENTS}).consume()
        print(f"Shipment (synthetic): {len(SHIPMENTS)} MERGEd")

        s.run(CUSTOMS_CYPHER, {"rows": CUSTOMS}).consume()
        print(f"CustomsContext (synthetic): {len(CUSTOMS)} MERGEd")

    driver.close()
    print("Seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run))
