#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 10 — live data-quality audit (READ-ONLY).

Classifies every node label and runs the Phase 10 quality checks against the
live AuraDB, then writes docs/research/data-quality/DATA_QUALITY_ISSUES.json
with real counts and record IDs. Re-run after every fix task to prove the fix.

    python docs/data/neo4j/scripts/phase10_data_audit.py
"""
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
load_dotenv(ROOT / "backend" / ".env")
OUT = ROOT / "docs" / "research" / "data-quality" / "DATA_QUALITY_ISSUES.json"

# Every European country code that may legitimately carry an HCME record.
EUROPE = {
    "AT", "BE", "BG", "BY", "CH", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GB", "GR",
    "HR", "HU", "IE", "IS", "IT", "LT", "LU", "LV", "MT", "NL", "NO", "PL", "PT", "RO", "RS",
    "SE", "SI", "SK", "UA", "AL", "BA", "ME", "MK", "MD", "TR",
}

# Label -> classification rule. Order of precedence inside classify():
# TEST_DATA > SYNTHETIC_DEMO > this default.
DEFAULT_CLASS = {
    "Part": "SOURCE_DERIVED", "Machine": "SOURCE_DERIVED", "DealerBranch": "SOURCE_DERIVED",
    "Depot": "SOURCE_DERIVED", "Service": "SOURCE_DERIVED", "Category": "SOURCE_DERIVED",
    "Application": "SOURCE_DERIVED", "Specification": "SOURCE_DERIVED",
    "Attachment": "SOURCE_DERIVED", "DigitalService": "SOURCE_DERIVED", "Channel": "SOURCE_DERIVED",
    # Produced by app/integrations/mocks/* — no live ERP/WMS is connected.
    "InventoryCache": "NOT_CONNECTED", "InventoryLedger": "NOT_CONNECTED",
    "FulfilmentOption": "NOT_CONNECTED", "FulfilmentRequest": "NOT_CONNECTED",
    "Allocation": "NOT_CONNECTED", "Order": "NOT_CONNECTED",
    "AuditRecord": "INTERNAL_REFERENCE_ONLY", "IdempotencyRecord": "INTERNAL_REFERENCE_ONLY",
    "Customer": "UNKNOWN", "PartsInquiry": "UNKNOWN", "RequestedPart": "UNKNOWN",
}

CLASSIFY = """
MATCH (n) WHERE $label IN labels(n)
WITH n,
  CASE
    WHEN n.provenance = 'INTERNAL_TEST_WORKFLOW' AND coalesce(n.synthetic,false) = false THEN 'TEST_DATA'
    WHEN coalesce(n.partNumber,'') STARTS WITH 'PN6-TEST' OR coalesce(n.partNumber,'') STARTS WITH 'TEST-' THEN 'TEST_DATA'
    WHEN coalesce(n.email,'') ENDS WITH '@example.com' OR coalesce(n.testRunId,'') <> '' THEN 'TEST_DATA'
    WHEN n.data_source = 'HCME_SAP_SUPPLIER_MASTER' THEN 'REAL'
    WHEN n.synthetic = true OR n.data_source = 'SYNTHETIC_DEMO' THEN 'SYNTHETIC_DEMO'
    ELSE $default
  END AS cls
RETURN cls, count(*) AS n
"""

# (id, category, severity, description, cypher returning `id` per offending record, action)
CHECKS = [
    ("DQ-01", "duplicate_parts", "HIGH", "Part numbers used by more than one Part node",
     "MATCH (p:Part) WHERE p.part_number IS NOT NULL WITH p.part_number AS pn, collect(p.part_id) AS ids WHERE size(ids) > 1 RETURN pn + ' -> ' + apoc.text.join(ids, ',') AS id",
     "Merge or relabel duplicates"),
    ("DQ-02", "duplicate_dealers", "MEDIUM", "DealerBranch records with the same name and city",
     "MATCH (d:DealerBranch) WITH d.dealer_name + ' | ' + coalesce(d.city,'') AS k, collect(d.dealer_id) AS ids WHERE size(ids) > 1 RETURN k + ' -> ' + apoc.text.join(ids, ',') AS id",
     "Review — may be distinct branches at one site"),
    ("DQ-03", "invalid_machine_fitment", "HIGH", "Fitment relationships without source or confidence",
     "MATCH (m:Machine)-[f:HAS_PART_FITMENT]->(p:Part) WHERE f.source_id IS NULL OR f.confidence IS NULL RETURN m.machine_id + '->' + p.part_id AS id",
     "Add provenance or remove fitment"),
    ("DQ-04", "missing_provenance", "HIGH", "Canonical records with no source_id",
     "MATCH (n) WHERE any(l IN labels(n) WHERE l IN ['Part','Machine','DealerBranch','Depot','Service']) AND n.source_id IS NULL RETURN labels(n)[0] + ':' + coalesce(n.part_id, n.machine_id, n.dealer_id, n.depot_id, n.service_id, elementId(n)) AS id",
     "Trace source or mark UNKNOWN"),
    ("DQ-05", "non_european_records", "HIGH", "Customer-facing records (dealers, depot) outside Europe — SAP suppliers may be global",
     "MATCH (n) WHERE (n:DealerBranch OR n:Depot OR (n:Supplier AND coalesce(n.data_source, '') <> 'HCME_SAP_SUPPLIER_MASTER')) AND n.country IS NOT NULL AND NOT n.country IN $europe RETURN labels(n)[0] + ':' + coalesce(n.dealer_id, n.depot_id, n.supplier_id) + ' (' + n.country + ')' AS id",
     "Remove from HCME Europe scope"),
    ("DQ-06", "dealer_coordinates_outside_europe", "MEDIUM", "Dealers whose lat/long falls outside a Europe bounding box",
     "MATCH (d:DealerBranch) WHERE d.latitude IS NULL OR d.longitude IS NULL OR toFloat(d.latitude) < 34 OR toFloat(d.latitude) > 72 OR toFloat(d.longitude) < -25 OR toFloat(d.longitude) > 45 RETURN d.dealer_id + ' ' + d.dealer_name + ' (' + coalesce(toString(d.latitude),'null') + ',' + coalesce(toString(d.longitude),'null') + ')' AS id",
     "Correct coordinates — nearest-dealer depends on them"),
    ("DQ-07", "unsupported_pricing", "CRITICAL", "Fulfilment options with a transport price not backed by a source and not labelled synthetic",
     "MATCH (o:FulfilmentOption) WHERE o.transportCost IS NOT NULL AND coalesce(o.synthetic,false) = false RETURN o.id + ' ' + coalesce(o.serviceLevel,'') + ' ' + toString(o.transportCost) + ' ' + coalesce(o.currency,'') AS id",
     "Values come from integrations/mocks/shipping_rate_mock.py — relabel SYNTHETIC_DEMO or remove"),
    ("DQ-08", "non_eur_currency", "CRITICAL", "Monetary values in a currency other than EUR",
     "MATCH (n) WHERE n.currency IS NOT NULL AND n.currency <> 'EUR' RETURN labels(n)[0] + ':' + coalesce(n.id, elementId(n)) + ' ' + n.currency AS id",
     "Convert or remove"),
    ("DQ-09", "unsupported_delivery_transit", "CRITICAL", "Fulfilment options claiming transit days / ETA with CONFIRMED confidence but produced by a mock",
     "MATCH (o:FulfilmentOption) WHERE o.transitDays IS NOT NULL AND o.confidence = 'CONFIRMED' AND coalesce(o.synthetic,false) = false RETURN o.id + ' ' + coalesce(o.serviceLevel,'') + ' ' + toString(o.transitDays) + 'd' AS id",
     "Values come from integrations/mocks/routing_mock.py — must not be CONFIRMED"),
    ("DQ-10", "unsupported_carrier", "HIGH", "Carrier codes with no carrier source",
     "MATCH (o:FulfilmentOption) WHERE o.carrierCode IS NOT NULL AND coalesce(o.synthetic,false) = false RETURN o.id + ' ' + o.carrierCode AS id",
     "Relabel SYNTHETIC_DEMO or remove"),
    ("DQ-11", "unsupported_inventory", "CRITICAL", "Inventory quantities produced by the mock integration and not labelled synthetic",
     "MATCH (i:InventoryCache) WHERE coalesce(i.synthetic,false) = false RETURN i.id + ' ' + i.partNumber + ' @' + i.sourceId + ' avail=' + toString(i.availableQty) AS id",
     "Mock source (integrations/mocks/inventory_mock.py) — relabel or remove"),
    ("DQ-12", "invented_source_location", "HIGH", "Stock/allocation sources that are not a real Depot, DealerBranch or synthetic Supplier",
     "MATCH (n) WHERE (n:InventoryCache OR n:InventoryLedger OR n:Allocation OR n:FulfilmentOption) AND n.sourceId IS NOT NULL AND NOT EXISTS { MATCH (d:Depot) WHERE d.depot_id = n.sourceId } AND NOT EXISTS { MATCH (d:DealerBranch) WHERE d.dealer_id = n.sourceId } AND NOT EXISTS { MATCH (s:Supplier) WHERE s.supplier_id = n.sourceId } RETURN DISTINCT labels(n)[0] + ':' + n.sourceId AS id",
     "e.g. REGIONAL-DEPOT-AMS does not exist; real depot is Oosterhout"),
    ("DQ-13", "test_data_orders", "CRITICAL", "Orders created by API/E2E test runs (INTERNAL_TEST_WORKFLOW, not synthetic)",
     "MATCH (o:Order) WHERE o.provenance = 'INTERNAL_TEST_WORKFLOW' AND coalesce(o.synthetic,false) = false AND coalesce(o.data_source,'') <> 'SYNTHETIC_DEMO' RETURN o.id AS id",
     "Delete via cleanup script"),
    ("DQ-14", "test_data_part_numbers", "CRITICAL", "Operational records referencing test part numbers (PN6-TEST*, TEST-*)",
     "MATCH (n) WHERE coalesce(n.partNumber,'') STARTS WITH 'PN6-TEST' OR coalesce(n.partNumber,'') STARTS WITH 'TEST-' RETURN labels(n)[0] + ':' + coalesce(n.id, elementId(n)) AS id",
     "Delete via cleanup script"),
    ("DQ-15", "test_customers", "HIGH", "Customer / inquiry records that are test identities",
     "MATCH (c) WHERE (c:Customer OR c:PartsInquiry) AND (c.email ENDS WITH '@example.com' OR toLower(c.name) CONTAINS 'test' OR toLower(c.name) CONTAINS 'qa') RETURN labels(c)[0] + ':' + c.name + ' <' + c.email + '>' AS id",
     "Delete"),
    ("DQ-16", "synthetic_without_flag", "HIGH", "Records with data_source SYNTHETIC_DEMO but synthetic not true",
     "MATCH (n) WHERE n.data_source = 'SYNTHETIC_DEMO' AND coalesce(n.synthetic,false) = false RETURN labels(n)[0] + ':' + coalesce(n.id, n.shipment_id, elementId(n)) AS id",
     "Set synthetic=true"),
    ("DQ-17", "real_marked_synthetic", "CRITICAL", "Canonical source records flagged synthetic (explicit DEMO_PART fixtures PT-901..904 are labelled and excluded)",
     "MATCH (n) WHERE any(l IN labels(n) WHERE l IN ['Part','Machine','DealerBranch','Depot']) AND n.synthetic = true AND coalesce(n.record_class,'') <> 'DEMO_PART' RETURN labels(n)[0] + ':' + coalesce(n.part_id, n.machine_id, n.dealer_id, n.depot_id) AS id",
     "Remove synthetic flag"),
    ("DQ-18", "orphan_orders", "HIGH", "Orders with no link to a Part and no allocation",
     "MATCH (o:Order) WHERE NOT (o)-[:FOR_PART]->() AND NOT (o)-[:BASED_ON_ALLOCATION]->() RETURN o.id AS id",
     "Link or delete"),
    ("DQ-19", "orphan_fulfilment_requests", "MEDIUM", "FulfilmentRequests with no order and no allocation",
     "MATCH (f:FulfilmentRequest) WHERE NOT (f)-[:HAS_ORDER]->() AND NOT (f)-[:HAS_ALLOCATION]->() RETURN f.id AS id",
     "Delete if test, else keep as abandoned request"),
    ("DQ-20", "fulfilment_option_not_linked", "MEDIUM", "FulfilmentOptions whose fulfilmentRequestId points to no FulfilmentRequest",
     "MATCH (o:FulfilmentOption) WHERE NOT EXISTS { MATCH (f:FulfilmentRequest) WHERE f.id = o.fulfilmentRequestId } RETURN o.id AS id",
     "Delete"),
    ("DQ-21", "order_destination_not_a_dealer", "HIGH", "Orders whose destination is not a real DealerBranch",
     "MATCH (o:Order) WHERE NOT EXISTS { MATCH (d:DealerBranch) WHERE d.dealer_id = o.destinationBranchId } RETURN o.id + ' -> ' + coalesce(o.destinationBranchId,'null') AS id",
     "Fix destination or delete"),
    ("DQ-22", "invalid_shipment_dates", "HIGH", "Shipments delivered before shipped, or DELIVERED without delivered_at",
     "MATCH (s:Shipment) WHERE (s.delivered_at IS NOT NULL AND s.shipped_at IS NOT NULL AND s.delivered_at < s.shipped_at) OR (s.status = 'DELIVERED' AND s.delivered_at IS NULL) RETURN s.shipment_id AS id",
     "Fix dates"),
    ("DQ-23", "invalid_service_dates", "HIGH", "Service jobs with completion before install / install before receipt",
     "MATCH (j:ServiceJob) WHERE (j.completed_at IS NOT NULL AND j.installed_at IS NOT NULL AND j.completed_at < j.installed_at) OR (j.installed_at IS NOT NULL AND j.received_at IS NOT NULL AND j.installed_at < j.received_at) RETURN j.service_job_id AS id",
     "Fix dates"),
    ("DQ-24", "shipment_not_delivered_to_dealer", "MEDIUM", "Shipments with no SHIPPED_TO DealerBranch",
     "MATCH (s:Shipment) WHERE NOT (s)-[:SHIPPED_TO]->(:DealerBranch) RETURN s.shipment_id AS id",
     "Link or delete"),
    ("DQ-25", "part_without_fitment", "LOW", "Parts not fitted to any Machine",
     "MATCH (p:Part) WHERE NOT ()-[:HAS_PART_FITMENT]->(p) RETURN p.part_id + ' ' + p.part_name AS id",
     "Acceptable for generic fluids/paint; review others"),
    ("DQ-26", "part_without_supplier", "MEDIUM", "Parts with no supplier relationship (Supplier Risk tab cannot render)",
     "MATCH (p:Part) WHERE NOT (p)-[:SUPPLIED_BY]->(:Supplier) RETURN p.part_id AS id",
     "Seed SYNTHETIC_DEMO supply relationships (Task 7)"),
    ("DQ-27", "machine_without_bom", "MEDIUM", "Machines with fitments but no BOM quantities (Impact tab 'Total BOM qty' cannot render)",
     "MATCH (m:Machine)-[:HAS_PART_FITMENT]->() WHERE NOT (m)-[:HAS_ASSEMBLY]->() RETURN DISTINCT m.machine_id AS id",
     "Seed SYNTHETIC_DEMO BOM (Task 6)"),
    ("DQ-28", "inconsistent_order_state", "MEDIUM", "ACCEPTED orders with no allocation",
     "MATCH (o:Order {status:'ACCEPTED'}) WHERE NOT (o)-[:BASED_ON_ALLOCATION]->() RETURN o.id AS id",
     "Fix state or delete"),
    ("DQ-29", "confirmed_confidence_from_mock", "HIGH", "Operational records claiming confidence CONFIRMED although produced by a mock integration",
     "MATCH (n) WHERE (n:FulfilmentOption OR n:InventoryCache) AND n.confidence = 'CONFIRMED' RETURN labels(n)[0] + ':' + n.id AS id",
     "Downgrade to SYNTHETIC_DEMO"),
    ("DQ-30", "bom_fitment_mismatch", "HIGH", "BOM lines without a matching fitment, or fitments without a BOM line",
     "MATCH (m:Machine)-[:HAS_ASSEMBLY]->(a:Assembly)-[:CONTAINS_PART]->(p:Part) WHERE NOT (m)-[:HAS_PART_FITMENT]->(p) RETURN 'bom-only ' + a.assembly_id + '->' + p.part_id AS id UNION MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part) WHERE NOT EXISTS { (m)-[:HAS_ASSEMBLY]->(:Assembly)-[:CONTAINS_PART]->(p) } RETURN 'fitment-only ' + m.machine_id + '->' + p.part_id AS id",
     "Re-run seed_phase10_demo_data.py --step bom"),
    ("DQ-31", "demo_relationship_without_flag", "HIGH", "Phase 10 demo relationships not labelled SYNTHETIC_DEMO",
     "MATCH ()-[r:HAS_ASSEMBLY|CONTAINS_PART|SUPPLIED_BY|REQUIRES_COMPLIANCE|HAS_CERTIFICATION|HAS_SYNTHETIC_INVENTORY]->() WHERE coalesce(r.synthetic,false) = false AND r.data_source IS NULL RETURN type(r) + ':' + elementId(r) AS id",
     "Set synthetic=true, data_source='SYNTHETIC_DEMO'"),

    # --- Phase 10B: supplier master checks (20260609_Source data for Supplier.xlsx) ---
    ("DQ-32", "supplier_missing_number", "CRITICAL", "Suppliers with no supplier_number (unusable as a key)",
     "MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' AND coalesce(s.supplier_number,'') = '' RETURN elementId(s) AS id",
     "Investigate source row"),
    ("DQ-33", "supplier_duplicate_number", "CRITICAL", "Supplier numbers used by more than one Supplier node",
     "MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' WITH s.supplier_number AS num, collect(elementId(s)) AS ids WHERE size(ids) > 1 RETURN num + ' -> ' + apoc.text.join(ids, ',') AS id",
     "supplier_number must be unique — re-run import_sap_suppliers.py"),
    ("DQ-34", "supplier_missing_name", "HIGH", "Suppliers with no name",
     "MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' AND coalesce(s.name,'') = '' RETURN s.supplier_number AS id",
     "Investigate source row"),
    ("DQ-35", "supplier_invalid_country", "HIGH", "Suppliers with no 2-letter ISO country code",
     "MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' AND (s.country IS NULL OR NOT s.country =~ '^[A-Z]{2}$') RETURN s.supplier_number AS id",
     "Investigate source row"),
    ("DQ-36", "supplier_missing_city_country_link", "HIGH", "Real suppliers not linked to a City/Country",
     "MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' AND NOT (s)-[:LOCATED_IN]->(:City) RETURN s.supplier_number AS id",
     "Re-run import_sap_suppliers.py"),
    ("DQ-37", "supplier_duplicate_name", "LOW", "Same supplier name under different supplier numbers (retained by design, flagged)",
     "MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' AND s.possible_duplicate_of IS NOT NULL RETURN s.supplier_number AS id",
     "Manual review only — distinct SAP accounts are kept, not merged"),
    ("DQ-38", "city_missing_country_edge", "HIGH", "City nodes with no IN_COUNTRY edge (breaks country roll-ups)",
     "MATCH (c:City) WHERE NOT (c)-[:IN_COUNTRY]->(:Country) RETURN c.city_id AS id",
     "Investigate import script"),
    ("DQ-39", "real_supplier_marked_synthetic", "CRITICAL", "Real SAP supplier-master records flagged synthetic",
     "MATCH (s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' AND s.synthetic = true RETURN s.supplier_number AS id",
     "Real client data must never be classified SYNTHETIC_DEMO"),
    ("DQ-40", "unsupported_supplier_to_part", "CRITICAL", "Part-[:SUPPLIED_BY]->Supplier where the Supplier is a REAL (non-synthetic) supplier",
     "MATCH (:Part)-[:SUPPLIED_BY]->(s:Supplier) WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' RETURN s.supplier_number AS id",
     "The supplier master has no part numbers — never link a real supplier to a Part without an authoritative supplier-part source"),
    ("DQ-41", "unsupported_supplier_to_dealer", "CRITICAL", "Direct Supplier-[:SUPPLIES]->DealerBranch or similar relationships (never inferred from shared city)",
     "MATCH (:Supplier)-[r:SUPPLIES|SERVES]->(:DealerBranch) RETURN type(r) + ':' + elementId(r) AS id",
     "Delete — dealer/supplier co-location is LOCATED_IN -> City only, never a direct edge"),
    ("DQ-42", "unsupported_supplier_to_depot", "CRITICAL", "Direct Supplier-[:SUPPLIES]->Depot relationships (never inferred)",
     "MATCH (:Supplier)-[r:SUPPLIES]->(:Depot) RETURN type(r) + ':' + elementId(r) AS id",
     "Delete — no authoritative supplier-to-depot source exists"),
]


def main():
    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    db = os.environ.get("NEO4J_DATABASE") or None
    report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "database": os.environ["NEO4J_URI"].split("//")[-1], "label_classification": {},
              "summary": {}, "issues": []}

    with driver.session(database=db) as s:
        labels = sorted(s.run("CALL db.labels() YIELD label RETURN label").value())
        print("=== Label classification ===")
        for label in labels:
            rows = s.run(CLASSIFY, label=label, default=DEFAULT_CLASS.get(label, "UNKNOWN")).data()
            breakdown = {r["cls"]: r["n"] for r in rows}
            report["label_classification"][label] = breakdown
            print(f"  {label:22} {breakdown}")

        print("\n=== Quality checks ===")
        for cid, cat, sev, desc, cypher, action in CHECKS:
            ids = [r["id"] for r in s.run(cypher, europe=sorted(EUROPE))]
            report["issues"].append({"id": cid, "category": cat, "severity": sev, "description": desc,
                                     "count": len(ids), "record_ids": ids[:60],
                                     "truncated": len(ids) > 60, "action": action})
            report["summary"][cat] = len(ids)
            flag = "PASS" if not ids else f"{len(ids)} ISSUE(S)"
            print(f"  {cid} [{sev:8}] {cat:36} {flag}")

    driver.close()
    report["total_issue_records"] = sum(report["summary"].values())
    report["failing_checks"] = sum(1 for i in report["issues"] if i["count"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{report['failing_checks']}/{len(CHECKS)} checks failing, {report['total_issue_records']} records -> {OUT}")


if __name__ == "__main__":
    main()
