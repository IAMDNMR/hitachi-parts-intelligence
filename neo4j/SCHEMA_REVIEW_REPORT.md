# Schema Review Report

Reviewed against `neo4j/data/*.csv`, `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`, and the reports from the cleaning phase. No Neo4j connection made; no import run.

## What changed from `schema_candidates.md`

The earlier draft was mostly right but had one systematic error: it listed `DigitalService` at 616 records and (implicitly, via `applications.csv`) `Application` needed checking too. Verified directly:
- **DigitalService: 8 distinct records**, not 616 — the 616 is the Machine×DigitalService relationship count. Fixed in `GRAPH_SCHEMA_MATRIX.csv`.
- **Application: 29 distinct**, already correctly listed as 29 in the earlier draft (verified, no change needed).
- One genuinely new entity surfaced that wasn't in the original candidate list: **`Channel`** (2 records: `CH-DEALER`, `CH-EXTERNAL`), found only as relationship targets in `13_AFTER_SALES_RELATIONSHIPS`, not as its own sheet.

## Validation run (Step 18)

| Check | Result |
|---|---|
| Duplicate Category IDs | 0 |
| Duplicate Machine IDs | 0 |
| Duplicate Part IDs | 0 |
| Duplicate Attachment IDs | 0 |
| Duplicate Service IDs | 0 |
| `PRODUCT_LINE_PART_FAMILY` records carrying a part number (accidental SKU creation) | 0 |
| Fitment rows missing an evidence value | 0 |
| `EXACT_MODEL` rows whose original text actually reads as category-level (evidence collapsed wrong direction) | 0 |
| `CATEGORY` rows whose original text actually reads as model-level (evidence collapsed wrong direction) | 0 |
| Fitment conflicts (from the cleaning phase) | 0 |
| Machine-service conflicts (from the cleaning phase) | 0 |
| Dangling foreign keys (from the cleaning phase, scope-descriptor sentinels correctly excluded) | 0 |

No fake compatibility, no fake part numbers, no fake machine models, no evidence collapsed into the wrong bucket, no core/derived conflation in what's recommended for import.

## 1. What is ready for Neo4j

Category (17), Machine (77), Specification (1635), Application (29 distinct), Part (43: 20 orderable + 23 family), Attachment (17), Service (22), DigitalService (8 distinct), Channel (2) — and the relationships built from the *detail* tables: `CHILD_OF`, `BELONGS_TO`, `HAS_SPECIFICATION`, `HAS_APPLICATION`, `HAS_PART_FITMENT`, `HAS_SERVICE`, `HAS_DIGITAL_SERVICE`, `REQUIRES_PART` (11_SERVICE_PART_REQUIREMENTS), `FITS`/`FITS_CATEGORY` (from 05_ATTACHMENTS' own columns), plus the small, clean sheet-13-only edges: `SUPPORTS`, `NOTIFIES`, `INTEGRATES`, `DELIVERED_BY`, `AFFECTS_MAINTENANCE_OF`.

## 2. What is intentionally deferred

- `Customer`, `Dealer`, `Warehouse`, `Inventory`, `Order`, `OrderLine`, `Shipment`, `Warranty`, `MachineAlert`, `ServiceJob` — zero source rows for any of them.
- `MaintenanceActivity` as its own node — 10 rows, mostly scope-descriptor text, not yet structured enough.
- Sheet 13's `RECEIVES` (1631) and `USES` (558) rows — would duplicate `HAS_SERVICE`/`HAS_DIGITAL_SERVICE` at a coarser evidence grain and at a different count than the detail tables.
- Sheet 13's `FITS` rows (17, all with a blank target) and its single `PROVIDES_CATALOGUE_FOR → 'ALL'` row — not usable as real edges without source correction.

## 3. Remaining ambiguities

1. 77 machine records compute to 84 distinct model codes (via the `|`-delimited `Models Covered` field on 7 rows), but the source workbook's own README states "79 distinct model codes." Not reconciled — needs your input or a closer look at which 5 codes are counted differently.
2. Sheet 13's summary relationship counts (`HAS_FITMENT` 943, `RECEIVES` 1631, `USES` 558) are close to but not identical to the detail tables (944, 1694, 616). Recommendation is to trust the detail tables and treat sheet 13 as a non-imported cross-check, but this is a judgment call worth your confirmation, not something the data resolves on its own.
3. `Channel` as a node vs. a property on `Service`/`DigitalService` — real either way, thin data (2 records), included as a node above but flagged as a genuine open choice.

## 4. Schema decisions that require your approval before any import script is written

- Confirm the `Channel` node decision (§3.3 above).
- Confirm treating sheet 13's `RECEIVES`/`USES`/`FITS`/`PROVIDES_CATALOGUE_FOR` rows as non-imported / deferred rather than reconciling and importing them too.
- Confirm the Maintenance approach (relationship-attached annotation, not a node) is acceptable for the current phase.
- Confirm the 77-vs-84-vs-79 model-code discrepancy doesn't block moving forward, or tell us how you'd like it investigated further.

## 5. Exact next step for the eventual Neo4j import phase

Once the above four points are confirmed: write (do not run) `neo4j/scripts/build_cypher_import.py`, generating parameterized Cypher (`UNWIND`/`LOAD CSV`, plus uniqueness constraints from `GRAPH_SCHEMA_MATRIX.csv`'s primary keys) for each node and relationship type marked READY in `GRAPH_SCHEMA_MATRIX.csv` / `GRAPH_RELATIONSHIP_MATRIX.csv`, in dependency order: Category → Machine → Part/Attachment/Service/DigitalService/Channel → all relationships. That script gets reviewed the same way this phase's outputs are being reviewed now, before anything touches Aura.

**No Neo4j Aura connection made. No Aura credentials used. No constraints, indexes, nodes, or relationships created in any database. Stopping here as instructed.**
