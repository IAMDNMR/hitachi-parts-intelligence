# Phase 10 — Data Quality Audit

Source of truth: live Neo4j AuraDB, audited by `docs/data/neo4j/scripts/phase10_data_audit.py`
(read-only). Machine-readable output with record IDs: `docs/research/data-quality/DATA_QUALITY_ISSUES.json`.

## 1. Baseline (before any Phase 10 fix) — 2026-09-23

**19 of 29 checks failing, 1,826 offending records.**

### 1.1 Classification by label

| Label | Classification (count) | Notes |
|---|---|---|
| Part | SOURCE_DERIVED 60 | HCME website / battery compliance pages; 37 of 60 have a part number |
| Machine | SOURCE_DERIVED 77 | |
| Machine→Part fitment | SOURCE_DERIVED 1,041 | every edge has source_id + confidence (DQ-03 PASS) |
| DealerBranch | SOURCE_DERIVED 182 | 30 countries, 19 in NL, all with source_id |
| Depot | SOURCE_DERIVED 1 | Hitachi European parts centre, Oosterhout NL — facility facts only, no stock |
| Service / Category / Application / Specification / Attachment / DigitalService / Channel | SOURCE_DERIVED | |
| ComplianceRequirement | SYNTHETIC_DEMO 3, UNKNOWN 1 | |
| Supplier | SYNTHETIC_DEMO 2 | "Demo European Logistics Partner A/B" — logistics partners, not part suppliers |
| Shipment / ShipmentEvent / ServiceJob / ServiceEvent / CatalogEntry / CustomsContext / InventorySnapshot | SYNTHETIC_DEMO (7/10/2/8/3/1/3) | correctly flagged |
| Order | TEST_DATA 171, SYNTHETIC_DEMO 3 | 171 created by API/E2E test runs |
| Allocation | TEST_DATA 71, NOT_CONNECTED 6, SYNTHETIC_DEMO 3 | |
| InventoryLedger | TEST_DATA 71, NOT_CONNECTED 2 | |
| FulfilmentOption | NOT_CONNECTED 146, SYNTHETIC_DEMO 3 | produced by mock rate/routing adapters |
| FulfilmentRequest | NOT_CONNECTED 143, SYNTHETIC_DEMO 3 | |
| InventoryCache | NOT_CONNECTED 143 | produced by `integrations/mocks/inventory_mock.py` |
| PartsInquiry | TEST_DATA 14 | all "Customer Test <test@example.com>" |
| Customer | TEST_DATA 1, UNKNOWN 1 | "Migration QA Test" is test; the other is a real quote submission |
| RequestedPart | UNKNOWN 68 | lines of the test inquiries |
| AuditRecord | INTERNAL_REFERENCE_ONLY 627, TEST_DATA 21 | |
| IdempotencyRecord | INTERNAL_REFERENCE_ONLY 12 | |
| BOM / Assembly | **does not exist** | |
| Purchase Order | **does not exist** | |
| Part→Supplier | **does not exist** | |

### 1.2 Failing checks

| ID | Check | Severity | Count | Root cause / example |
|---|---|---|---|---|
| DQ-06 | dealer coordinates outside Europe / missing | MEDIUM | 4 | **DLR-043 Hitachi CM Nederland has latitude = null**; DLR-116 French Guiana and DLR-130 Réunion are overseas; DLR-066 Tenerife is valid (bounding-box false positive) |
| DQ-07 | unsupported transport pricing | CRITICAL | 146 | €35 STANDARD / €65 EXPRESS hardcoded in `integrations/mocks/shipping_rate_mock.py` |
| DQ-09 | unsupported transit / ETA marked CONFIRMED | CRITICAL | 146 | 1 day hardcoded in `integrations/mocks/routing_mock.py` |
| DQ-10 | unsupported carrier | HIGH | 146 | `LOGISTICS_PARTNER_STD/EXP` — invented codes |
| DQ-11 | unsupported inventory | CRITICAL | 143 | `inventory_mock.py` quantities |
| DQ-12 | invented source locations | HIGH | 7 distinct | `REGIONAL-DEPOT-AMS`, `REGIONAL-DEPOT-DEFAULT`, `SRC1` — no such depot; the real depot is Oosterhout |
| DQ-13 | test orders | CRITICAL | 136 | `provenance = INTERNAL_TEST_WORKFLOW` |
| DQ-14 | test part numbers | CRITICAL | 256 | `PN6-TEST_*` / `TEST-*` across Order/FulfilmentRequest/Allocation/Inventory |
| DQ-15 | test customers | HIGH | 15 | 14 PartsInquiry + 1 Customer at `@example.com` |
| DQ-16 | synthetic label on test data | HIGH | 35 | 35 test orders stamped `data_source=SYNTHETIC_DEMO` by the Phase 9 order sync, but `synthetic` not set |
| DQ-18 | orphan orders | HIGH | 146 | no FOR_PART and no allocation |
| DQ-19 | orphan fulfilment requests | MEDIUM | 140 | |
| DQ-21 | order destination not a dealer | HIGH | 171 | `DEALER-BRANCH-NL-01`, `DEALER-BR-101` — not DealerBranch IDs |
| DQ-24 | shipment not linked to dealer | MEDIUM | 5 | |
| DQ-25 | part without fitment | LOW | 8 | generic fluids/paint — acceptable, retained |
| DQ-26 | part without supplier | MEDIUM | 60 | Supplier Risk tab has no data |
| DQ-27 | machine without BOM | MEDIUM | 77 | Impact tab "Total BOM qty" / "Critical paths" has no data |
| DQ-28 | ACCEPTED order without allocation | MEDIUM | 39 | |
| DQ-29 | CONFIRMED confidence from a mock | HIGH | 146 | |

Passing: DQ-01 duplicate parts, DQ-02 duplicate dealers, DQ-03 fitment provenance, DQ-04 canonical
provenance, DQ-05 non-European countries, DQ-08 non-EUR currency, DQ-17 real marked synthetic,
DQ-20 option linkage, DQ-22 shipment dates, DQ-23 service dates.

## 2. Transport / fulfilment lineage (Task 4 input)

```
UI  "REGIONAL-DEPOT-AMS (REGIONAL_DEPOT) CONFIRMED · Mode ROAD (LOGISTICS_PARTNER_STD) · Transit 1 day · €35.00"
    "REGIONAL-DEPOT-AMS (REGIONAL_DEPOT) CONFIRMED · Mode COURIER (LOGISTICS_PARTNER_EXP) · Transit 1 day · €65.00"
    (currency renders as €, not $, in the current build — but the values are equally unsupported)
 ↓ React   frontend/components/FulfilmentOptionSelector.tsx:156-172
 ↓ API     POST /api/v1/fulfilment/...  → app/modules/fulfilment/service.py (lines ~180-260)
 ↓ calls   routing adapter  → app/integrations/mocks/routing_mock.py   (estimated_transit_days = 1)
           rate adapter     → app/integrations/mocks/shipping_rate_mock.py (cost = 35.0 / 65.0)
 ↓ writes  (:FulfilmentOption {transportCost, currency:'EUR', transitDays, carrierCode, confidence:'CONFIRMED'})
 ↓ source  NONE — invented constants. No HCME tariff, carrier contract or transit table exists.
```
Verdict: every price, transit time and carrier code is **unsupported**. It must not be shown as a fact.

## 3. Screen field inventory (Task 3)

Target screens: the 5 uploaded screenshots, adapted to HCME Europe (vehicle → machine, connector → part).
STATUS: OK = exists and correct · GAP = required but missing · DERIVED = computed from real data · REMOVE = currently shown, not on target.

### 3.1 Parts Intelligence — question + result cards (screenshots 4, 5)

| Field | Current source | Provenance | Status | Action |
|---|---|---|---|---|
| Question box | user input | — | OK | keep |
| Workflow Execution (duration, step count) | measured request time | real | OK | keep; show real elapsed time + step count |
| Part ID (e.g. PT-001) | Part.part_id | SOURCE_DERIVED | OK | card title |
| Description (part name) | Part.part_name | SOURCE_DERIVED | OK | |
| Match % | search score | DERIVED | OK | show as % badge |
| Tile 1 — Part number | Part.part_number | SOURCE_DERIVED | OK (37/60) | show "Not published" when null |
| Tile 2 — Category | Part.part_category | SOURCE_DERIVED | OK | |
| Tile 3 — Assembly | Part.component_assembly | SOURCE_DERIVED | OK | |
| Tile 4 — Fits (n machines) | count of HAS_PART_FITMENT | SOURCE_DERIVED | OK | |
| Type tag | Part.part_subcategory | SOURCE_DERIVED | OK | |
| Match assessment ("Good match with minor trade-offs") | score bands | DERIVED | OK | |
| View Full Details → Technical specifications | Part flags (genuine, wear, service, consumable), confidence | SOURCE_DERIVED | OK | |
| View Full Details → Description | Part.description | SOURCE_DERIVED | OK | |
| Availability / Source / Confidence stat row | availability service / mock | NOT_CONNECTED | REMOVE | not on target card |
| Example-question chips, hero pills | static | — | REMOVE | "nothing extra" |

### 3.2 Graph Insights → Impact (screenshot 3)

| Field | Current source | Status | Action |
|---|---|---|---|
| Affected machines (count) | fitment count | OK | |
| Total BOM qty | — | **GAP** | needs BOM quantity per machine (Task 6, SYNTHETIC_DEMO) |
| Critical paths (assembly + qty) | — | **GAP** | needs assembly criticality (Task 6) |
| Machines list (name, family, category) | Machine via fitment | OK | |
| Assemblies (name, criticality, qty) | fitment.assembly (name only) | partial **GAP** | criticality + qty from Task 6 |
| Product families / Related services / Fitment evidence rows | impact + insights | REMOVE | not on target |

### 3.3 Graph Insights → Compliance (screenshot 2)

| Field | Current source | Status | Action |
|---|---|---|---|
| Requirement name | ComplianceRequirement (4 nodes, 7 links) | **GAP** | assembly-level EU requirements (Task 8) |
| "via <assembly>" | — | **GAP** | Assembly → requirement |
| "← <parent requirement>" | — | **GAP** | requirement dependency (Task 8) |
| Compliance gaps ("Missing X required by Y") | — | **GAP / DERIVED** | required-by-assembly minus part certifications |

### 3.4 Graph Insights → Supplier Risk (screenshot 1)

| Field | Current source | Status | Action |
|---|---|---|---|
| This part's supplier: name, region, tier | — | **GAP** | Part SUPPLIED_BY Supplier (Task 7) |
| Share % | — | **GAP** | relationship property |
| Dual-source eligible | — | **GAP / DERIVED** | ≥2 suppliers for part |
| Platform concentration: per supplier critical parts, sole-source parts | — | **GAP / DERIVED** | aggregate over SUPPLIED_BY |
| Single points of failure (this part) | — | **DERIVED** | sole source AND critical assembly |
| Source risk level / distinct source citations / buffers | source_risk.py | REMOVE | replaced by target layout |

### 3.5 Graph Insights → Mitigation

| Field | Current source | Status | Action |
|---|---|---|---|
| Executive summary | mitigation.py | DERIVED | keep, rewrite from new evidence |
| Affected machine programmes (count) | fitment | OK | |
| Preferred substitutes exist? | alternatives | DERIVED | |
| Workflow steps (Analyse Impact → Find Alternatives → Validate Compliance → Assess Supplier Risk → Rank Mitigation) | — | UI | show as executed steps |
| Alternative: part ID, similarity %, mitigation score | scoring.py | DERIVED | |
| Alternative: supplier | — | **GAP** | Task 7 |
| Alternative: compliance gaps | — | **GAP / DERIVED** | Task 8 |
| Score breakdown grid (Compatibility 40% / Availability 30% …) | mitigation.py | REMOVE | not on target |

### 3.6 Graph Insights — chrome

| Field | Status | Action |
|---|---|---|
| Title "Graph Insights", subtitle "<Part ID> — <part name>" | OK | |
| Tabs: Impact · Compliance · Supplier Risk · Mitigation | partial | keep these 4 only |
| Tabs: Fitment & Evidence, Source/Availability, Alternatives, Order Context, Supply Chain, Cross-Catalog | REMOVE | not on target |
| Top stats row (fitted machines / families / fitment records / alternatives) | REMOVE | not on target |
| Footer: "Analyze Disruption" + "Close" | GAP | add; Analyze Disruption opens Mitigation |

## 4. Fixes applied

### Task 4 — Transport / fulfilment (2026-09-23)

Code: `backend/app/modules/fulfilment/service.py` now honours the providers' `is_confirmed` flag. An
unconfirmed route or rate stores mode, carrier, service level, transit, ETA, price and currency as
null with `transportDataStatus = 'NOT_CONNECTED'`, and unconfirmed service-level variants collapse to
one option per source. The hardcoded split option (€50, 2 days) now carries no transport values.
UI (`FulfilmentOptionSelector.tsx`) shows "Carrier, transit time and ETA: not connected" and
"Est. Transport Cost: Not connected". Test `test_phase5_fulfilment.py` was updated to assert this
(it previously asserted `transport_cost > 0`, which enshrined the invented €35).

Data: `phase10_fix_data.py --step transport --execute` deleted 72 unselected EXPRESS options and
neutralised 77 remaining options.

| Check | Before | After |
|---|---|---|
| DQ-07 unsupported pricing | 146 | **0** |
| DQ-09 unsupported transit/ETA | 146 | **0** |
| DQ-10 unsupported carrier | 146 | **0** |
| DQ-08 non-EUR currency | 0 | 0 |

### Task 4b — Inventory truth (2026-09-23)

Root cause: `integrations/mocks/inventory_mock.py` returned hardcoded stock for every part number
(invented `REGIONAL-DEPOT-AMS` "Amsterdam Regional Depot", `REGIONAL-DEPOT-DEFAULT`,
`CENTRAL-DEPOT-JP` in Japan) and labelled it `provenance="HCME_ERP_SAP"`, which is false.

Fix:
- `seed_phase10_demo_data.py --step inventory --execute`: 36 `InventorySnapshot` nodes at the real
  `DEPOT-OOSTERHOUT`, one per catalogue part with a part number. Quantities are deterministic
  (0/2/6/12/18/25/40, including zero-stock parts). Each is `synthetic=true`, `data_source='SYNTHETIC_DEMO'`.
- New `app/integrations/adapters/synthetic_inventory_adapter.py` (default provider): catalogue parts
  read this demo stock with `provenance='SYNTHETIC_DEMO'`. Non-catalogue and test-run part numbers still
  use the test scenarios. A catalogue part without demo stock returns no sources.
- `availability/service.py` stores `provenance/synthetic/data_source` on `InventoryCache`;
  `fulfilment/service.py` propagates `synthetic` to each `FulfilmentOption`.
- UI: availability rows and fulfilment options show a **SYNTHETIC DEMO DATA** tag. "Check Real-Time
  Stock Availability" was renamed to "Check Stock Availability" because nothing is real-time.
- Bug fixed: `AvailabilityChecker.tsx` read camelCase fields (`sourceId`, `availableQty`,
  `providerName`), but the API returns snake_case. Source names were rendering blank and quantities
  as "undefined".
- `fix_data --step inventory`: deleted 148 mock `InventoryCache` rows.
- New test `test_catalogue_part_uses_labelled_synthetic_depot_stock`. 43/43 Phase 3–6/9 tests pass.

| Check | Before | After |
|---|---|---|
| DQ-11 unsupported inventory | 143 | **0** |

### Task 5 — Test-data leakage (2026-09-23)

`phase10_fix_data.py --step testdata --execute`. Records removed:

| Removed | Count | Why |
|---|---|---|
| Orders (`INTERNAL_TEST_WORKFLOW`, not synthetic) | 184 | test part numbers `PN6/7/8/9-*TEST*` or invented destinations `DEALER-BRANCH-NL-01` / `DEALER-BR-101` (171 at audit time + 13 leaked by API-level tests during this session) |
| Shipments + ShipmentEvents of those orders | 15 | 5 test shipments wrongly flagged `synthetic=true` + their events |
| Allocations (non-synthetic) | 79 | |
| FulfilmentOptions / FulfilmentRequests (non-synthetic) | 77 / 148 | |
| InventoryLedger rows | 75 | test part numbers / invented sources |
| PartsInquiry + RequestedPart (`test@example.com`) | 28 | |
| Orphan RequestedPart | 56 | |
| Customer "Migration QA Test" | 1 | |
| AuditRecords with `testRunId` | 21 | aborted test runs |

Fixed: `SJ-DEMO-001/002.order_id` was `ORD-DEMO-00x` but the Order id is `order-demo-00x`, so it was
a broken link.

Retained: the SYNTHETIC_DEMO chain `order-demo-001..003 → ship-demo-001/002 → SJ-DEMO-001/002`
(all `synthetic=true`), and the one real quote-request Customer.

Root cause of the leakage (still open, see Task 18): API-level tests (`TestClient`) create Orders
without a `testRunId`, so the per-test cleanup fixture never removes them.

Invented destinations removed from the UI: `AvailabilityChecker.tsx` offered "Amsterdam Main Hub
(BR-101)", "Oosterhout Regional Hub (BR-102)" and "Rotterdam Port Depot (BR-103)". None of these
exist. It now lists the 182 real DealerBranches, grouped by country, from the new `GET /api/v1/dealers`.

| Check | Before | After |
|---|---|---|
| DQ-12 invented source locations | 7 | **0** |
| DQ-13 test orders | 136 | **0** |
| DQ-14 test part numbers | 256 | **0** |
| DQ-15 test customers | 15 | **0** |
| DQ-16 synthetic label on test data | 35 | **0** |
| DQ-18 orphan orders | 146 | **0** |
| DQ-19 orphan fulfilment requests | 140 | **0** |
| DQ-21 order destination not a dealer | 171 | **0** |
| DQ-24 shipment not linked to dealer | 5 | **0** |
| DQ-28 ACCEPTED order without allocation | 39 | **0** |
| DQ-29 CONFIRMED from mock | 146 | **0** |
| **Failing checks** | **19 / 29** | **4 / 29** (DQ-06 dealer coords, DQ-25 fluids without fitment, DQ-26 supplier, DQ-27 BOM) |

### Task 6 — BOM (2026-09-23)

`seed_phase10_demo_data.py --step bom --execute`:
`(:Machine)-[:HAS_ASSEMBLY]->(:Assembly)-[:CONTAINS_PART {quantity, unit}]->(:Part)`.

| Element | Provenance |
|---|---|
| Which machine, which part, which assembly name | **SOURCE_DERIVED**, 1:1 from the 1,041 `HAS_PART_FITMENT` edges (assembly name = `fitment.assembly` with "(installed in …)" stripped) |
| Quantity per machine | **SYNTHETIC_DEMO**: track roller 12/14/16, carrier roller 2/4, sprocket 2, battery 1/2, filter 1/2/3, work lights 2/4/6, fluids 1 fill, otherwise 1 |
| Assembly criticality | **SYNTHETIC_DEMO** keyword rule (stored in `Assembly.criticality_basis`): engine, hydraulics, drivetrain, fuel, cooling and control = high; undercarriage, electrical, grease points and major components = medium; exterior, cab, lights and attachments = low |

Result: 833 Assembly nodes (all `synthetic=true`), 1,041 BOM lines across 77 machines.
New checks: DQ-30 BOM↔fitment mismatch = **0 in both directions**; DQ-31 unlabelled demo relationships = **0**.
DQ-27 machine without BOM: 77 → **0**.

### Task 7 — Suppliers (2026-09-23)

No HCME supplier data is public. `seed_phase10_demo_data.py --step suppliers` creates 8 **fictional**,
clearly named European demo suppliers ("Demo Hydraulics Supplier A", "Demo Battery Supplier", and so on),
so no real company is given an invented supply relationship. It also creates 73 `(:Part)-[:SUPPLIED_BY
{share_pct, role: SOLE|PRIMARY|SECONDARY}]->(:Supplier)` links from a commodity rule (fluids, batteries,
hydraulics, powertrain, undercarriage, electrical, filtration). About half the parts that have a second
source available are dual-sourced (60–85% / 15–40% shares). All 60 parts now have a supplier, and all
records are `synthetic=true`.
DQ-26 part without supplier: 60 → **0**.

### Task 8 — Compliance (2026-09-23)

The regulations are real EU instruments: REACH (EC) 1907/2006, CLP (EC) 1272/2008, Stage V (EU) 2016/1628,
Machinery Directive 2006/42/EC, EMC, and Battery Regulation (EU) 2023/1542. **Which assembly requires which
regulation, and which part holds which certificate, is SYNTHETIC_DEMO.** Records written: 1,692
`(:Assembly)-[:REQUIRES_COMPLIANCE]->`, 77 `(:Part)-[:HAS_CERTIFICATION]->` (about 1 in 6 required pairs
left without a certificate, so gaps exist), and 2 `DEPENDS_ON` (CLP → REACH, Battery Reg → REACH).
The one source-derived link (EU Battery Regulation on PT-001..003, SRC-039) is untouched and counts as held.

### After Tasks 4–8

**2 / 31 checks failing (12 records):** DQ-06 (DLR-043 "Hitachi CM Nederland — Regio Utrecht" has no
latitude in the source (SRC-049), so it is excluded from distance ranking and nothing is invented;
DLR-116 French Guiana and DLR-130 Réunion are French overseas territories listed by HCME; DLR-066
Tenerife is valid) and DQ-25 (8 generic fluids/paint with no fitment — acceptable).

_(Task 9 — Customer / Sales Order / Purchase Order seed — deferred: user re-prioritised Parts Intelligence.)_
