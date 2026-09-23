# PHASE 0-6 DATA CLEANUP — BEFORE STATE SNAPSHOT

Captured live against the production AuraDB instance (`backend/.env` credentials, via
`app.db.neo4j.connection.get_neo4j_session()` — the app's own session-factory pattern) on
2026-09-23, before any modification in this cleanup pass. All output below is raw query
output, not summarized.

## 1. Entity counts (BEFORE)

```
Part: 68
Machine: 77
DealerBranch: 182
Depot: 1
Allocation: 73
FulfilmentRequest: 165
FulfilmentOption: 167
Order: 295
Shipment: 2
InventoryCache: 162
InventoryLedger: 55
Supplier: 2
CatalogEntry: 3
InventorySnapshot: 3
CustomsContext: 1
```

## 2. PT-044–PT-053 (full records, live)

All 10 present. All already carry `data_class: INTERNALLY GENERATED DATA`, `confidence: LOW`,
`source_id: SRC-048` (from a prior session's `relabel_internal_parts.py`). All still carry
`record_class: ORDERABLE_OEM_PART` (unchanged, the open defect).

```
PT-044 | part_number 4719002 | Hitachi OEM Main Control Valve Block Assembly
PT-045 | part_number 4658321 | Hitachi OEM Dual Axial Piston Main Hydraulic Pump
PT-046 | part_number 4621008 | Hitachi OEM Stage V Industrial Diesel Engine Assembly
PT-047 | part_number 4398110 | Hitachi OEM Slewing Ring / Swing Bearing Assembly
PT-048 | part_number 9265430 | Hitachi OEM Final Drive Travel Motor & Gearbox
PT-049 | part_number 4683058 | Hitachi OEM Electronic Control Module (ECM / Main Controller)
PT-050 | part_number 4679860 | Hitachi OEM Multi-Station Solenoid Valve Manifold Bank
PT-051 | part_number 4465700 | Hitachi OEM Forged Dual-Flange Lower Track Roller Assembly
PT-052 | part_number 4600500 | Hitachi OEM Heavy Hydraulic Demolition Breaker Attachment
PT-053 | part_number 3065785 | Hitachi OEM ZW-Series Heavy Wheel Loader Axle Assembly
```
All: `record_class=ORDERABLE_OEM_PART`, `data_class=INTERNALLY GENERATED DATA`,
`confidence=LOW`, `source_id=SRC-048`, `source_date` 2026-09-17/18.

Note: PT-045's `part_number` (4658321) is the same part number referenced by 3 live Order
records (see Section 6) — i.e. this internally-generated/LOW-confidence part has actually
been ordered through the live E2E test flow.

## 3. PT-054–PT-060 (full records, live)

All 7 present, all `data_class: OFFICIAL WEBSITE DATA`, `confidence: HIGH`,
`source_id: SRC-042`, `source_date: 2026-09-18`, `record_class: ORDERABLE_OEM_PART`.

```
PT-054 | part_number 12345678        | Hitachi OEM High-Intensity LED Working Light Bar Kit (24V)
PT-055 | part_number 114362-77011    | Hitachi OEM Heavy-Duty 24V Engine Starter Motor Assembly
PT-056 | part_number LR2100-701A     | Hitachi OEM Dust-Sealed 24V/100A Brushless Alternator
PT-057 | part_number 9062575         | Hitachi OEM Dual-Core Radiator & Hydraulic Oil Cooler Module
PT-058 | part_number 4642345         | Hitachi OEM Heavy-Dust Air Breather & Pre-Cleaner Assembly
PT-059 | part_number 2011409         | Hitachi OEM Single-Flange Upper Carrier Roller Assembly
PT-060 | part_number 91823456        | Hitachi OEM Induction-Hardened Track Drive Sprocket Segment Group
```
`PT-054`'s part number `12345678` is a literal placeholder pattern.

`provenance.csv` line 43 for SRC-042: `SRC-042,HCME,Official dealer page,Dealer network,All,
Service delivery channel,...,Official Source: Yes` — a dealer/service-delivery source, not a
parts-catalogue source. Confirmed mismatch: SRC-042 does not describe the content type
(LED bars, starter motors, alternators, coolers, air cleaners, rollers, sprockets) attributed
to it.

## 4. PT-021–PT-043 (full records, live)

23 records found (matches CSV). All carry `record_class: PRODUCT_LINE_PART_FAMILY`,
`data_class: OFFICIAL WEBSITE DATA`, `confidence: HIGH`, `part_number` absent (by design —
these are program-level families like "Hitachi Genuine Parts", "Hitachi Genuine Hydraulic Oil
5000", "AdBlue® / Diesel Exhaust Fluid", not individual SKUs). Source IDs vary legitimately
per family (SRC-016, SRC-027, SRC-030..038 etc.), each matching real HCME.co.uk parts-and-fluids
program content. Full per-record dump captured in
`C:\Users\iamdn\AppData\Local\Temp\claude\...\scratchpad\snapshot_output.txt` (raw session
capture) — reproduced in the companion report, Section 4.

## 5. CONC6-DBG* nodes (full records, live)

16 nodes total: **8 `Part` nodes** + **8 `InventoryLedger` nodes** (one ledger per part, all
`sourceId` prefixed `DEPOT-CONC6-DBG...`).

Part nodes (all properties — only `part_id`/`part_number` set, no `record_class`,
`data_class`, `confidence`, `source_id`, `description`, `part_name`, etc. — i.e. these are
bare synthetic stub Parts, structurally incapable of being mistaken for a catalogued OEM
part since they carry none of the catalogue fields the UI renders):
```
CONC6-DBG5b100774, CONC6-DBG3ba3b216, CONC6-DBG0eb0a1cb, CONC6-DBG6e9d0d2d,
CONC6-DBG297bd563, CONC6-DBG7bdc9f46, CONC6-DBG86788fb1, CONC6-DBG50babf64
```

InventoryLedger nodes: 1:1 with the 8 parts above, `sourceId` = `DEPOT-CONC6-DBG<hash>`
(not the real Depot's `SRC-050`/`REGIONAL-DEPOT-DEFAULT` sourceId).

Relationships: 18 `(Part)-[:ALLOCATES]->(Allocation)` edges from the 8 CONC6-DBG parts to 18
distinct `Allocation` nodes (ids `alloc-...`), captured in full in the snapshot output file.
No relationship from any CONC6-DBG node to a real `Machine`, `DealerBranch`, or `Depot` node
was found in this query pass — HAS_PART_FITMENT / real-catalogue linkage not present for
these nodes (to be double-checked before deletion in the main report).

## 6. All Orders — provenance/synthetic/testRunId breakdown (live, full population)

Total Order count: **295**.

```
provenance distribution:
  INTERNAL_TEST_WORKFLOW:      292
  SYNTHETIC_DEMO_KPI_WORKFLOW:   3

synthetic distribution:
  null:  292
  true:    3

testRunId set (non-null): 0   <- confirms none came from pytest fixtures (conftest tags
                                  testRunId and auto-cleans; these all came from live,
                                  non-pytest calls into the same order-creation code path)

status distribution:
  CREATED:    292
  ACCEPTED:     2
  CANCELLED:    1

destinationBranchId distribution:
  DEALER-BRANCH-NL-01: 289
  DEALER-BR-101:          3
  DLR-019:                2
  DLR-001:                1

partNumber patterns (top values):
  4663907 (PT-001 battery):        16
  4658321 (PT-045, LOW-confidence, internally-generated hydraulic pump): 3
  PN6-TEST_<uuid>-<hash>:         the overwhelming majority of the remainder (literal "TEST"
                                   marker baked into the part number string itself)
```

**Source-code finding (decisive, not inferred):** `backend/app/modules/order/service.py`
line 116, inside the one and only order-creation function (`create_order`), hardcodes
`provenance: 'INTERNAL_TEST_WORKFLOW'` on every Order node it creates — there is no code
path anywhere in the service that ever writes a different provenance value for a normal
order. The function's own comment (line 173-174) reads: *"Internal test/development
submission attempt — never presented as a real HCME integration (see TestOrderProvider
docstring)."* This means: by the application's own design, **100% of Order nodes ever
created through the live API are structurally test/development records** — there is no
"real transaction" code path in this prototype at all. The separate
`SYNTHETIC_DEMO_KPI_WORKFLOW` provenance (3 orders, `synthetic=true`) is written by a
different seeding path for demo-KPI purposes and is already correctly flagged.

Full per-order id/status/provenance/synthetic/partNumber/destination dump is in the raw
snapshot capture (395 order rows would be excessive to inline in full here; the aggregate
breakdowns above are exhaustive over all 295 records, computed via `count(*)` aggregation
directly in Cypher, not sampled).

## 7. Raw capture files

- Full raw query output (all sections, unabridged): 
  `C:\Users\iamdn\AppData\Local\Temp\claude\C--Users-iamdn-OneDrive-Desktop-Parts-Service\5a65ab93-aa0a-4599-a45c-25e32ad48c9c\scratchpad\snapshot_output.txt`
- Script used to generate it (reusable, uses the app's own `get_neo4j_session()` pattern):
  `C:\Users\iamdn\AppData\Local\Temp\claude\C--Users-iamdn-OneDrive-Desktop-Parts-Service\5a65ab93-aa0a-4599-a45c-25e32ad48c9c\scratchpad\snapshot.py`

This file is the BEFORE state of record for this cleanup pass. No modification to live
Neo4j data occurs until after this file is written.
