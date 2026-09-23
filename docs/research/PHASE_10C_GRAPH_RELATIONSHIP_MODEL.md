# PHASE 10C — HCME Europe Graph Relationship Model

**Audited**: 2026-09-23 against live Neo4j AuraDB (`neo4j+ssc://fb580139.databases.neo4j.io`)

---

## 1. Complete Relationship Inventory

| Relationship | From Label | To Label | Count | Source | Data Class | Supported | Synthetic | Derived | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `HAS_PART_FITMENT` | `Machine` | `Part` | **1,041** | HCME Europe catalogue | SOURCE_DERIVED | ✅ | ❌ | ❌ | Primary fitment relationship; authoritative |
| `CONTAINS_PART` | `Assembly` | `Part` | 1,041 | HCME Europe catalogue | SOURCE_DERIVED | ✅ | ❌ | ❌ | BOM assembly→part link |
| `HAS_ASSEMBLY` | `Machine` | `Assembly` | 833 | HCME Europe catalogue | SOURCE_DERIVED | ✅ | ❌ | ❌ | Machine to BOM assembly |
| `HAS_SERVICE` | `Machine` | `Service` | 1,694 | HCME Europe catalogue | SOURCE_DERIVED | ✅ | ❌ | ❌ | Machine service offerings |
| `HAS_SPECIFICATION` | `Machine` | `Specification` | 1,635 | HCME Europe catalogue | SOURCE_DERIVED | ✅ | ❌ | ❌ | Technical specifications |
| `BELONGS_TO` | `Machine` | `Category` | 77 | HCME Europe catalogue | SOURCE_DERIVED | ✅ | ❌ | ❌ | Machine category classification |
| `HAS_APPLICATION` | `Machine` | `Application` | 328 | HCME Europe catalogue | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `HAS_DIGITAL_SERVICE` | `Machine` | `DigitalService` | 616 | HCME Europe catalogue | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `LOCATED_IN` | `Supplier` | `City` | **1,720** | SAP supplier master | SOURCE_DERIVED | ✅ | ❌ | ❌ | All 1,720 SAP suppliers wired to cities |
| `LOCATED_IN` | `DealerBranch` | `City` | **155** | HCME dealer locator | SOURCE_DERIVED | ✅ | ❌ | ❌ | 155 of 182 dealers wired to city nodes |
| `LOCATED_IN` | `Depot` | `City` | 1 | HCME published data | SOURCE_DERIVED | ✅ | ❌ | ❌ | Hitachi European Parts Centre, Oosterhout |
| `IN_COUNTRY` | `City` | `Country` | **926** | Geographic data | SOURCE_DERIVED | ✅ | ❌ | ❌ | Full city→country graph |
| `IN_COUNTRY` | `DealerBranch` | `Country` | 27 | HCME dealer locator | SOURCE_DERIVED | ✅ | ❌ | ❌ | Legacy dealers without City node |
| `SUPPLIED_BY` | `Part` | `Supplier` | **73** | SYNTHETIC DEMO SEED | **SYNTHETIC_DEMO** | ⚠️ | ✅ | ❌ | **NOT from source data.** SAP master has no part-supplier mapping. All synthetic=true |
| `SOURCED_FROM` | `Allocation` | `Depot` | 2 | Synthetic workflow | SYNTHETIC_DEMO | ⚠️ | ✅ | ❌ | Demo allocation sourcing |
| `SOURCED_FROM` | `Allocation` | `Supplier` | 1 | Synthetic workflow | SYNTHETIC_DEMO | ⚠️ | ✅ | ❌ | Demo allocation sourcing |
| `HAS_CERTIFICATION` | `Part` | `ComplianceRequirement` | 73 | Synthetic/derived | SYNTHETIC_DEMO | ⚠️ | ✅ | ❌ | |
| `HAS_COMPLIANCE_REQUIREMENT` | `Part` | `ComplianceRequirement` | 7 | Synthetic/derived | SYNTHETIC_DEMO | ⚠️ | ✅ | ❌ | |
| `REQUIRES_COMPLIANCE` | `Assembly` | `ComplianceRequirement` | 1,692 | Synthetic/derived | SYNTHETIC_DEMO | ⚠️ | ✅ | ❌ | |
| `HAS_ALLOCATION` | `FulfilmentRequest` | `Allocation` | 3 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `HAS_ORDER` | `FulfilmentRequest` | `Order` | 3 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `BASED_ON_ALLOCATION` | `Order` | `Allocation` | 3 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `HAS_SHIPMENT` | `Order` | `Shipment` | 2 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `SHIPPED_TO` | `Shipment` | `DealerBranch` | 2 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `HAS_SERVICE_JOB` | `Shipment` | `ServiceJob` | 2 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `PERFORMS_SERVICE` | `DealerBranch` | `ServiceJob` | 4 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `FOR_PART` | `Order` | `Part` | 3 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `FOR_PART` | `ServiceJob` | `Part` | 4 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `HAS_EVENT` | `Shipment` | `ShipmentEvent` | 9 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `HAS_EVENT` | `ServiceJob` | `ServiceEvent` | 18 | Internal workflow | SYNTHETIC_DEMO | ✅ | ✅ | ❌ | |
| `HAS_SYNTHETIC_INVENTORY` | `Part` | `InventorySnapshot` | 39 | Seeded demo | SYNTHETIC_DEMO | ⚠️ | ✅ | ❌ | No live stock feed |
| `ALTERNATIVE_FOR` | `CatalogEntry` | `Part` | 1 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `CROSS_REFERENCES` | `CatalogEntry` | `Part` | 2 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `FITS` | `Attachment` | `Machine` | 14 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `AFFECTS_MAINTENANCE_OF` | `Attachment` | `Part` | 1 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `REQUIRES_PART` | `Service` | `Part` | 11 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `HAS_CUSTOMS_CONTEXT` | `Shipment` | `CustomsContext` | 1 | Synthetic | SYNTHETIC_DEMO | ⚠️ | ✅ | ❌ | |
| `INTEGRATES` | `DigitalService` | `DigitalService` | 1 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `NOTIFIES` | `DigitalService` | `Channel` | 2 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `SUPPORTS` | `DigitalService` | `Service` | 2 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `DELIVERED_BY` | `Service` | `Channel` | 23 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |
| `DEPENDS_ON` | `ComplianceRequirement` | `ComplianceRequirement` | 2 | Derived | DERIVED | ⚠️ | ❌ | ✅ | |
| `CHILD_OF` | `Category` | `Category` | 16 | Source data | SOURCE_DERIVED | ✅ | ❌ | ❌ | |

---

## 2. Critical Findings

### Finding 1: Supplier-to-Part Mapping Does NOT Exist from Source Data

> **IMPORTANT**: The HCME SAP supplier master (`20260609_Source data for Supplier.xlsx`) contains:
> - `LIFNR` (supplier number)
> - Supplier name
> - City
> - Country
>
> It does **NOT** contain: part numbers, material numbers, or supplier-part assignments.
>
> Therefore: `(:Supplier)-[:SUPPLIES]->(:Part)` or `(:Part)-[:SUPPLIED_BY]->(:Supplier)` relationships **cannot be created from source data**.
>
> The 73 existing `SUPPLIED_BY` edges in the graph have `synthetic=true` — they were seeded as demo records. The application must ALWAYS disclose this when presenting supplier-to-part information.

### Finding 2: Geographic Graph is Complete

- 1,720 SOURCE_DERIVED suppliers → City → Country
- 155 SOURCE_DERIVED dealers → City → Country (27 more with direct `IN_COUNTRY`)
- 926 cities in 56 countries
- Correct colocation queries work: `Supplier -[:LOCATED_IN]-> City <-[:LOCATED_IN]- DealerBranch`

### Finding 3: Operational Workflow Graph is SYNTHETIC_DEMO

All Order, Shipment, ServiceJob, Allocation, FulfilmentRequest nodes are synthetic demo data.

---

## 3. NOT_CONNECTED Relationships (in scope but no data wired)

| Missing Relationship | From → To | Why Not Present | When Can Be Added |
|---|---|---|---|
| `(:Supplier)-[:SUPPLIES]->(:Part)` | Supplier → Part | Source data has no part-supplier mapping | If HCME provides enriched supplier catalogue |
| Live ERP stock → InventorySnapshot | ERP → Part | SAP ERP not connected | Phase 9+ integration |
| Real Order → ERP Order | Order → SAP | SAP ERP not connected | Phase 9+ integration |

---

## 4. Machine Type Vocabulary (Live graph categories)

Based on audit of `Machine.machine_category` values:

| Graph Value | User Vocabulary |
|---|---|
| `Medium Excavators` | medium excavator, mid excavator, midsize excavator |
| `Large Excavators` | large excavator, big excavator, heavy excavator |
| `Mini Excavators` | mini excavator, compact excavator, small excavator |
| `Wheeled Excavators` | wheeled excavator, wheel excavator |
| `Wheel Loaders` | wheel loader, wheeled loader |
| `Rigid Dump Trucks` | rigid dump truck, dump truck, hauler |

---

## 5. Phase 10C Relationship Classification Rule

Every relationship in Neo4j must carry one of these classifications:

| Class | Meaning | Example |
|---|---|---|
| `SOURCE_DERIVED` | Directly from HCME Europe published/client data | `HAS_PART_FITMENT`, `LOCATED_IN` |
| `DERIVED` | Computed from source data (must say how) | Shared-city colocation inference |
| `SYNTHETIC_DEMO` | Seeded demo record, NOT real HCME data | `SUPPLIED_BY`, `HAS_SHIPMENT` |
| `TEST_DATA` | Created by an automated test run | Tagged with `testRunId` |
| `INTERNAL_REFERENCE_ONLY` | System-internal cross-reference | Audit relationships |
| `NOT_CONNECTED` | Would require a real integration | Live ERP stock, real prices |
| `UNKNOWN` | Provenance not yet determined | Requires investigation |
