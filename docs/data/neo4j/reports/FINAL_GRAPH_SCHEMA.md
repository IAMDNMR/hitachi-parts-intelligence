# Final Graph Schema — HCME After-Sales

Status: **proposal for review**. No Neo4j connection has been made to produce or validate this document — everything below was checked against the CSVs in `neo4j/data/` and the source workbook only, using `neo4j/scripts/*.py` and ad-hoc verification queries.

## 1. Graph purpose

Represent the after-sales knowledge Hitachi Construction Machinery Europe actually publishes — machines, their specifications and applications, the parts and attachments that fit them, the services and digital services available, and the evidence behind every one of those claims — so the Parts Store and the Service experience can answer "what fits, what's available, and how sure are we" without either app inventing an answer the source doesn't support.

## 2. Design principles

1. **Evidence over assertion.** Every fitment/applicability/compatibility relationship carries the evidence level the source actually states (exact model, model range, category, or not stated) as a property. No relationship is imported without it.
2. **No entity without source rows.** Customer, Dealer, Warehouse, Inventory, Order, Shipment, Warranty and MachineAlert have zero rows in this workbook. They appear below marked `FUTURE / NOT CURRENTLY POPULATED` and nothing is created for them now.
3. **Distinct concepts stay distinct.** An `ORDERABLE_OEM_PART` (a real, published part number) and a `PRODUCT_LINE_PART_FAMILY` (a named product line with no part number) are never modelled so that a query can't tell them apart.
4. **Row count ≠ entity count.** Several source sheets are junction tables (one row per Machine×DigitalService, Machine×Service pair, etc.) — those become relationships, not one node per row. Verified per-sheet below; this correction is the main change from the earlier `schema_candidates.md` draft.
5. **Compact provenance.** `source_id`/`confidence`/`data_class` travel as small properties on the fact they support. No `Source` node holding a URL that every consumer would have to filter out.
6. **No overengineering.** No node for a URL, a row number, a UI ranking value, or a piece of metadata nothing will ever traverse.

## 3–5. Node types, labels, primary keys

| Label | Primary key | Source | Count | Status |
|---|---|---|---|---|
| `Category` | `category_id` | 01_MACHINE_CATEGORIES | 17 | READY |
| `Machine` | `machine_id` | 02_MACHINE_MASTER | 77 | READY |
| `Specification` | `spec_id` | 03_MACHINE_SPECIFICATIONS | 1635 | READY |
| `Application` | `name` (canonical, after case-fold) | 04_MACHINE_APPLICATIONS | **29 distinct** (328 rows are the Machine×Application relationship, not 328 nodes) | READY — corrected from schema_candidates.md, which already had this one right |
| `Part` | `part_id` | 06_PART_MASTER | 43 (20 `ORDERABLE_OEM_PART` + 23 `PRODUCT_LINE_PART_FAMILY`) | READY |
| `Attachment` | `attachment_id` | 05_ATTACHMENTS | 17 | READY |
| `Service` | `service_id` | 08_SERVICE_CAPABILITIES | 22 | READY |
| `DigitalService` | `digital_service_id` | 12_MACHINE_DIGITAL_SERVICES | **8 distinct** (616 rows are the Machine×DigitalService relationship, not 616 nodes — this is the number `schema_candidates.md` got wrong and Step 1 below explains) | READY — corrected |
| `Channel` | `channel_id` | 13_AFTER_SALES_RELATIONSHIPS (`To ID` where `To Entity Type = Channel`) | **2 distinct** (`CH-DEALER`, `CH-EXTERNAL`) | READY, small — see §15 for the alternative (property instead of node) |
| `Customer` | — | none | 0 | FUTURE / NOT CURRENTLY POPULATED |
| `Dealer` | — | none | 0 | FUTURE / NOT CURRENTLY POPULATED |
| `Warehouse` | — | none | 0 | FUTURE / NOT CURRENTLY POPULATED |
| `Inventory` | — | none | 0 | FUTURE / NOT CURRENTLY POPULATED |
| `PartsRequirement` | — | 11_SERVICE_PART_REQUIREMENTS exists but has no stock/quantity/pricing dimension to make this a distinct entity from the relationship itself | 11 rows | See §7 — modelled as a relationship, not a node |
| `ServiceJob` | — | none (this workbook has service *capabilities*, not service *transactions*) | 0 | FUTURE / NOT CURRENTLY POPULATED |
| `Order`, `OrderLine`, `Shipment` | — | none | 0 | FUTURE / NOT CURRENTLY POPULATED |
| `Warranty` | — | none | 0 | FUTURE / NOT CURRENTLY POPULATED |
| `MachineAlert` | — | none — 12_MACHINE_DIGITAL_SERVICES documents alert *capability*, never an actual alert event | 0 | FUTURE / NOT CURRENTLY POPULATED |
| `MaintenanceActivity` / node vs property | — | 10_MAINTENANCE_SCHEDULE, 10 rows | 10 | See §8 — kept as `schema_candidates.md` recommended: too thin to be its own node yet |

### Removed from consideration
- **`Source` node** — 47 provenance rows, but nothing in the graph should ever traverse "which source said this" as a first-class path. Compact properties on the fact instead (§12).

## 6. Node properties (core fields per node)

**Category**: `category_id`, `parent_category`, `category_name`, `official_category_name`, `category_description`, `product_type`, `machine_configuration`, `on_road_off_road`, `primary_application`.

**Machine**: `machine_id`, `model`, `models_covered` (list — see §4 below, never split into fake extra Machine nodes), `model_count`, `machine_category`, `machine_subcategory`, `category_id`, `product_family`, `generation_series`, `machine_type`, `configuration`, `power_source`, `official_product_name`, `engine_motor_rated_power`, `operating_weight_kg_normalised`, `operating_weight_as_published`, plus the other published spec headline fields already flattened onto Machine in `machines.csv` (bucket capacity, battery capacity, payload, digging depth/reach, dimensions, fuel tank capacity).

**Specification**: `spec_id`, `machine_id`, `specification_group`, `specification_name`, `specification_value` (null if unpublished), `unit`, `normalised_value`, `value_stated` (boolean — false only where the source explicitly states "NOT PUBLICLY STATED"; true for every other row including this workbook's 1635, since none of them happened to say that — see §18).

**Application**: `name` (canonical), `application_type`.

**Part**: `part_id`, `part_number` (null for family records — never invented), `part_name`, `part_category`, `part_subcategory`, `component_assembly`, `record_class` (`ORDERABLE_OEM_PART` | `PRODUCT_LINE_PART_FAMILY`), `genuine_hitachi_part`, `consumable`, `wear_part`, `replacement_part`, `service_part`, `attachment_part`, `description`, `supersedes_part_number`, `superseded_by`.

**Attachment**: `attachment_id`, `attachment_name`, `attachment_type`, `attachment_category`, `mounting_coupling_type`, `hydraulic_requirement`, `weight`, `dimensions`, `capacity`, `purpose_application`, `detachable_fixed`.

**Service**: `service_id`, `service_name`, `service_category`, `description`, `customer_site`, `dealer_workshop`, `other_location`, `dealer_delivered`, `external_authorised_provider`.

**DigitalService**: `digital_service_id`, `service_name`, `capability`, `machine_data`, `alert_monitoring`, `maintenance_support`, `diagnostic_support`, `parts_support`, `dealer_support`, `description`.

**Channel**: `channel_id`, `label` — a stable, generic description, e.g. `"HCME authorised dealer network"` for `CH-DEALER`. **Revised during final pre-import review** (`neo4j/reports/CHANNEL_REVIEW.md`): `CH-EXTERNAL`'s label is generic too ("External authorised provider..."), not any one service's specific provider name — the source's `To Name` text for `CH-EXTERNAL` varies per relationship (`"Yes (Reman centre)"` for one service, `"Yes (BNP Paribas Leasing Solutions; DLL)"` for another), so that per-service detail lives on the `DELIVERED_BY` relationship (`provider_detail` property) instead of the node.

## 7–9. Relationship types and properties

| Relationship | From → To | Source | Count | Evidence property? |
|---|---|---|---|---|
| `(:Category)-[:CHILD_OF]->(:Category)` | Category → Category | 01 + 13 (`CHILD_OF`, 16 rows) | 16 | no — structural |
| `(:Machine)-[:BELONGS_TO]->(:Category)` | Machine → Category | 02 (`Category ID` column) + 13 (`BELONGS_TO`, 77 rows, exact match) | 77 | no |
| `(:Machine)-[:HAS_SPECIFICATION]->(:Specification)` | Machine → Specification | 03 | 1635 | `data_class` |
| `(:Machine)-[:HAS_APPLICATION]->(:Application)` | Machine → Application | 04 | 328 | `confidence`, `data_class` (all 328 rows are `DERIVED (category-level...)` — see §13, this is honestly a 100%-derived relationship type) |
| `(:Machine)-[:HAS_PART_FITMENT {evidence, evidence_original, fitment_type, source_id, confidence}]->(:Part)` | Machine → Part | 07 | 944 | **yes — mandatory**, see §5 below |
| `(:Attachment)-[:FITS {evidence_scope}]->(:Machine \| :Category)` | Attachment → Machine or Category | 05 (direct columns) + 13 (`FITS`, 17 rows — **17 of 17 have a blank `To ID`, see §18**) | 17 via 05; 13's `FITS` rows need remediation before import | see §10 |
| `(:Machine)-[:HAS_SERVICE {applicability, applicability_original, confidence}]->(:Service)` | Machine → Service | 09 | 1694 | **yes — mandatory**, see §6 |
| `(:Service)-[:REQUIRES_PART {quantity, mandatory_optional}]->(:Part)` | Service → Part | 11 (per-machine detail, 11 rows) + 13 `REQUIRES` (service-level summary, 11 rows) | 11 | `quantity` only where stated |
| `(:Machine)-[:HAS_DIGITAL_SERVICE {applicability, confidence}]->(:DigitalService)` | Machine → DigitalService | 12 | 616 | yes |
| `(:DigitalService)-[:SUPPORTS]->(:Service)` | DigitalService → Service | 13 (`SUPPORTS`, 2 rows) | 2 | `data_class` |
| `(:DigitalService)-[:INTEGRATES]->(:DigitalService)` | DigitalService → DigitalService | 13 (`INTEGRATES`, 1 row) | 1 | `data_class` |
| `(:DigitalService)-[:NOTIFIES]->(:Channel)` | DigitalService → Channel | 13 (`NOTIFIES`, 2 rows) | 2 | `data_class` |
| `(:Service)-[:DELIVERED_BY]->(:Channel)` | Service → Channel | 13 (`DELIVERED_BY`, 23 rows) | 23 | `data_class`, `provider_detail` (per-service text — see `CHANNEL_REVIEW.md`) |
| `(:Attachment)-[:AFFECTS_MAINTENANCE_OF]->(:Part)` | Attachment → Part | 13 (1 row) | 1 | `data_class` |
| `(:DigitalService)-[:PROVIDES_CATALOGUE_FOR]->(:Part)` | DigitalService → Part | 13 (1 row, target is the literal sentinel `ALL` — **needs review, see §18**) | 1 (blocked) | — |

Not imported as first-class edges: `RECEIVES` (1631 rows) and `USES` (558 rows) from 13_AFTER_SALES_RELATIONSHIPS. Both appear to be sheet 13's own derived restatement of `HAS_SERVICE` (1694 in 09) and `HAS_DIGITAL_SERVICE` (616 in 12) respectively, at slightly different counts (1631 vs 1694; 558 vs 616). Rather than silently pick one number, both are flagged in §20 as an ambiguity: the per-machine detail tables (09, 12) are recommended as the source of truth because they carry richer evidence properties per row; sheet 13's summary rows would need to be reconciled against them (not merged blindly) before anyone imports both.

## 5 (detail). Machine ↔ Part fitment — the exact model

```
(:Machine)-[:HAS_PART_FITMENT {
    evidence: 'EXACT_MODEL' | 'MODEL_RANGE' | 'CATEGORY' | 'NOT_STATED',
    evidence_original: <source's own free text>,
    fitment_type: 'Maintenance' | 'Replacement' | 'Accessory' | 'Standard' | 'Wear',
    source_id: 'SRC-xxx',
    confidence: 'HIGH' | 'MEDIUM'
}]->(:Part)
```

Real distribution in the cleaned data: `CATEGORY` 876, `EXACT_MODEL` 37, `MODEL_RANGE` 31 — **876 of 944 fitment rows (93%) are category-level, not exact-model**. Any query that treats `HAS_PART_FITMENT` as "this exact machine takes this exact part" without checking `evidence` will overstate certainty for 93% of fitment data. `evidence_type`/`confidence`/`fitment_scope` (the properties the brief asked about) map onto `evidence`, `confidence`, and `evidence` again respectively — kept as one property (`evidence`) rather than three overlapping ones, since the source only actually states one evidence dimension per row.

`fitment_type` (Maintenance/Replacement/Accessory/Standard/Wear) is a **different axis** — the nature of the part, not the fitment confidence — and must not be confused with `evidence`. `07_MACHINE_PART_FITMENT`'s own `Compatibility` column is the one normalized into `evidence`; `Fitment Type` is a separate, orthogonal property, both kept.

## 6 (detail). Machine ↔ Service

```
(:Machine)-[:HAS_SERVICE {
    applicability: 'ALL_MACHINES_STATED' | 'CATEGORY' | 'NOT_STATED',
    applicability_original: <source free text>,
    confidence
}]->(:Service)
```
Real distribution: `ALL_MACHINES_STATED` 847, `CATEGORY` 784, `NOT_STATED` 63. No row in this sheet states a single-exact-model-only applicability, so `EXACT_MODEL`/`MODEL_RANGE` were **not** invented as possible values for this relationship — they simply don't occur in the source for Machine↔Service (unlike Machine↔Part, where they do). `NOT_STATED` rows (63) should be treated by any consumer as "no confirmed applicability" and never surfaced as if the service applies.

## 7 (detail). Service ↔ Part

Decision: `(:Service)-[:REQUIRES_PART]->(:Part)`, **not** an intermediate `ServicePartRequirement` node.

Reasoning from the actual data: 11_SERVICE_PART_REQUIREMENTS has 11 rows, each already a simple (Service, Part) pair with `Quantity` and `Mandatory/Optional` as flat scalar properties — no row has multiple parts bundled per requirement, no row needs its own further sub-relationships (no requirement-to-requirement links, no requirement history). An intermediate node earns its place when the relationship itself needs to be a source or target of other edges, or carries a one-to-many internal structure; neither is true here with 11 rows. If the eventual live system starts tracking requirement history, review dates, or per-dealer requirement overrides, `ServicePartRequirement` becomes justified — not now.

## 8 (detail). Maintenance

**Revised during final pre-import review** (`neo4j/FINAL_PRE_IMPORT_REVIEW.md` item 1) — the original text of this section (below, struck through in spirit) overstated the Machine↔Service correspondence found in the data on closer, row-by-row inspection.

Decision: no dedicated `Maintenance` node (unchanged). Attach maintenance data as **parallel list properties directly on `Part`** — not a `Service` relationship annotation as originally written here, and not a self-relationship as an intermediate design attempted (see the import report's revision history).

Reasoning, corrected: every row's own `Machine ID` field is a scope-descriptor sentinel (`"ALL - see Applies To"`), not a real machine reference. **On closer inspection, only 1 of the 10 rows (`MS-010`, "Regular services and inspections under Extended Warranty") has strong textual correspondence to an actual `Service`** — its activity name closely matches `SVC-004` ("Regular services and inspections") and its `Calendar Interval` text ("Up to 84 months (Full Coverage)") echoes `SVC-008`'s name ("Extended Warranty - Full Coverage"). The other 9 rows ("Hydraulic oil change", "Daily inspection", etc.) have no `Service Name`/`Service ID` in the sheet and no clean textual match against any of the 22 services — linking only `MS-010` while leaving the other 9 unlinked would be an inconsistent one-off special case, not a schema pattern, so no Machine↔Service or Maintenance↔Service edge is created for any of them.

What **is** consistently resolvable: 9 of 10 rows' `Required Part` text matches an existing `Part` by name (the 10th, `MS-005` "Daily inspection", has no required part — a visual check needs no consumable). One part (`PT-032`, Hitachi Genuine Hydraulic Oil Multi) is required by two different rows (`MS-002`: 1500h with a breaker attachment; `MS-003`: 2000h with other attachments) with different intervals — flat scalar properties on `Part` would silently overwrite one with the other, so the 9 maintenance facts are carried as index-aligned **list** properties (`maintenance_activities`, `maintenance_intervals`, etc.) on `Part`, correctly supporting more than one guideline per part without a new node or a confusing self-relationship. Full implementation in `neo4j/import/relationships/maintenance.cypher`.

## 9 (detail). Digital Services

`DigitalService` is a node (8 distinct — DS-001 through DS-008), never one node per Machine×DigitalService row. The 616 rows in `12_MACHINE_DIGITAL_SERVICES` become 616 `HAS_DIGITAL_SERVICE` relationship instances between 77 Machines and 8 DigitalServices, each carrying `applicability` and `confidence`. Distinguishing machine *digital capability* (`Capability`/`Machine Data`/`Alert / Monitoring` columns — booleans describing what the digital service CAN do) from machine *data* or a live *alert* (neither of which exists in this workbook — no telemetry event, no timestamped alert row anywhere) matters: nothing here should be surfaced to a user as "your machine has an active alert." It is capability metadata only.

## 10 (detail). Attachments

Decision: `(:Attachment)-[:FITS]->(:Machine)` for the 17 rows where `05_ATTACHMENTS` names a specific `Compatible Machine Model` directly (e.g. ATT-002 → EX1200-7 etc.), and `(:Attachment)-[:FITS_CATEGORY]->(:Category)` where only `Compatible Machine Category` is stated (the majority — e.g. ATT-001 → "Excavators (mini, medium, large, wheeled)"). Not `COMPATIBLE_WITH` — `FITS` matches the vocabulary the source's own relationship sheet already uses (13_AFTER_SALES_RELATIONSHIPS' `FITS` type), and splitting it into `FITS` (model-level) vs `FITS_CATEGORY` (category-level) preserves the evidence distinction the brief requires, the same way `HAS_PART_FITMENT.evidence` does for parts. No attachment dimension, weight, or compatibility was invented for rows where the source leaves them blank.

## 11. Relationship model (13_AFTER_SALES_RELATIONSHIPS)

3283 rows, 186 `CORE` (`OFFICIAL WEBSITE DATA`), 3097 `DERIVED` (`DERIVED FROM OFFICIAL SOURCE`) — CORE and DERIVED are **not equal-strength evidence** and must never be queried as if they were. Recommendation:
- `CORE` rows describing edges not otherwise captured (`BELONGS_TO`, `CHILD_OF`, `DELIVERED_BY`, `SUPPORTS`, `NOTIFIES`, `INTEGRATES`, `AFFECTS_MAINTENANCE_OF`) → import directly, `data_class: 'CORE'`.
- `DERIVED` rows that duplicate the fitment/service/digital-service detail tables (`HAS_FITMENT`, `RECEIVES`, `USES`) → **do not** import as a second copy of the same edge; the detail tables already carry richer per-row evidence. Keep sheet 13's version only as a cross-check artifact (already preserved untouched in `13_RELATIONSHIPS`/`relationships.csv`).
- `REQUIRES` (Service→Part, service-level) → cross-check against 11_SERVICE_PART_REQUIREMENTS (machine-level); both are legitimate but at different granularity, keep both, label the relationship source (`service_level` vs `machine_level`) so they're never confused for two independent facts.
- `FITS` (17 rows, **100% with a blank `To ID`**) → **do not import** until the source data is corrected; flagged in `16_REVIEW_REQUIRED`.
- `PROVIDES_CATALOGUE_FOR` targeting the literal string `ALL` → **do not import** as a real Part reference; either model as a Service/DigitalService-level flag (`provides_full_catalogue: true`) or leave deferred.

## 12. Provenance model

Recommendation: **B is wrong, A+D**. Not a `Source` node (nobody should ever need to traverse "all facts from source X" as a first-class graph path for either the Parts Store or the Service experience), but relationship/node properties carrying `source_id` (a short code, e.g. `SRC-039`), `confidence` (`HIGH`/`MEDIUM`/`LOW`), and `data_class` — exactly the 3 fields already on almost every cleaned row. The 47-row `14_PROVENANCE` table is kept as a **separate, non-graph reference table** (already exported as `provenance.csv` with the URL stripped) that a human or an audit tool can join against `source_id` when the full citation is needed — it does not need to be walked at query time by either app.

## 13. Core vs derived semantics

See §11. In one sentence: **`CORE` = the specific fact is stated verbatim on an official page; `DERIVED` = the fact was propagated from a category-level or structural statement.** `04_MACHINE_APPLICATIONS` is honestly 100% `DERIVED` per its own README ("HCME publishes applications per CATEGORY, not per model... propagated to the machines in that category") — this is not a data-quality problem, it's what the source states about itself, and the graph must keep saying so via the `data_class` property rather than presenting all 328 Machine→Application edges as equally certain.

## 14. Part family vs orderable part semantics

`record_class` is the load-bearing property. `ORDERABLE_OEM_PART` (20 records) has a real `part_number`; `PRODUCT_LINE_PART_FAMILY` (23 records) has `part_number: null`. **Any UI or query surfacing a Part must check `record_class` before implying "add to cart" / "order this exact SKU"** — a `PRODUCT_LINE_PART_FAMILY` node (e.g. "Hitachi Genuine Parts", a named product line with no part number) must never render or behave like a concrete orderable item.

## 15. Future entities

`Customer`, `Dealer`, `Warehouse`, `Inventory`, `Order`, `OrderLine`, `Shipment`, `Warranty`, `MachineAlert`, `ServiceJob` — all `FUTURE / NOT CURRENTLY POPULATED`. Zero rows in this workbook support any of them. When real transactional/CRM data becomes available, they slot into the existing `Machine`/`Service`/`Part` backbone without restructuring it (e.g. `(:Order)-[:FOR_MACHINE]->(:Machine)`, `(:OrderLine)-[:FOR_PART]->(:Part)`).

`Channel` (2 records, `CH-DEALER`/`CH-EXTERNAL`) is real but thin — could remain a tiny node (as proposed above, supporting `DELIVERED_BY`/`NOTIFIES`) or collapse into a `delivery_channel` enum property on `Service`/`DigitalService`. Recommend keeping it as a node only because it's already the target of 2 distinct relationship types from 2 distinct source labels (`Service`, `DigitalService`) — collapsing it would mean choosing which one owns the enum, which is arbitrary.

## 16. Example graph paths

- `(:Machine {machine_id:'MC-001'})-[:HAS_PART_FITMENT]->(:Part)-[:HAS_PART_FITMENT]-(:Machine)` — every other machine sharing a part with MC-001.
- `(:Machine)-[:BELONGS_TO]->(:Category)<-[:BELONGS_TO]-(:Machine)` — machines in the same category.
- `(:Part {record_class:'ORDERABLE_OEM_PART'})<-[:HAS_PART_FITMENT {evidence:'EXACT_MODEL'}]-(:Machine)` — parts with confirmed exact-model fitment only.
- `(:Machine)-[:HAS_SERVICE]->(:Service)-[:REQUIRES_PART]->(:Part)` — full parts BOM for a machine's available services.
- `(:Machine)-[:HAS_DIGITAL_SERVICE]->(:DigitalService)-[:SUPPORTS]->(:Service)` — which digital services back which physical service.

## 17. Example Cypher queries (for design review only — not run against any live database)

```cypher
// 1. What parts fit this machine, with evidence?
MATCH (m:Machine {machine_id:$id})-[f:HAS_PART_FITMENT]->(p:Part)
RETURN p.part_id, p.part_name, p.record_class, f.evidence, f.confidence
ORDER BY f.evidence;

// 3. Exact-model fit only
MATCH (m:Machine {machine_id:$id})-[f:HAS_PART_FITMENT {evidence:'EXACT_MODEL'}]->(p:Part)
RETURN p;

// 4 + 9. Services for a machine, marking CORE vs DERIVED
MATCH (m:Machine {machine_id:$id})-[hs:HAS_SERVICE]->(s:Service)
RETURN s.service_name, hs.applicability, hs.confidence;

// 11. Full after-sales ecosystem from a machine
MATCH (m:Machine {machine_id:$id})
OPTIONAL MATCH (m)-[:HAS_PART_FITMENT]->(p:Part)
OPTIONAL MATCH (m)-[:HAS_SERVICE]->(s:Service)
OPTIONAL MATCH (m)-[:HAS_DIGITAL_SERVICE]->(ds:DigitalService)
OPTIONAL MATCH (m)-[:HAS_APPLICATION]->(app:Application)
RETURN m, collect(DISTINCT p) AS parts, collect(DISTINCT s) AS services,
       collect(DISTINCT ds) AS digitalServices, collect(DISTINCT app) AS applications;

// 12. From a part, back out to machines/services
MATCH (p:Part {part_id:$id})<-[f:HAS_PART_FITMENT]-(m:Machine)
OPTIONAL MATCH (m)-[:HAS_SERVICE]->(s:Service)-[:REQUIRES_PART]->(p)
RETURN m, f.evidence, s;
```

## 18. Data currently available

See the counts throughout §3–11, all pulled from `neo4j/data/*.csv` at review time. Summary: 17 categories, 77 machines (84 model codes via `Models Covered`, see the open discrepancy below), 1635 specifications, 29 distinct applications, 43 parts (20/23 split), 17 attachments, 22 services, 8 digital services, 944 fitment relationships (0 conflicts), 1694 machine-service relationships (0 conflicts), 616 machine-digital-service relationships, 11 service-part requirements, 3283 sheet-13 relationships (186 CORE / 3097 DERIVED).

## 19. Data intentionally deferred

- All transactional entities (§15).
- `MaintenanceActivity` as its own node (§8) — insufficient structured data (10 rows, mostly scope-descriptor + free text).
- Sheet 13's `RECEIVES`/`USES` rows as separate edges from `HAS_SERVICE`/`HAS_DIGITAL_SERVICE` (§11) — would double-count the same facts at a coarser evidence grain.
- `FITS` rows with a blank target (17 of 17) and the single `PROVIDES_CATALOGUE_FOR → 'ALL'` row (§11) — not importable as-is.

## 20. Risks / ambiguities requiring a decision

1. ~~**77 machine records vs 84 computed model codes vs the source's own README claim of "79 distinct model codes."**~~ **RESOLVED** — see `MODEL_CODE_RECONCILIATION_REPORT.md`: 84 = total model-code slots, 79 = distinct code strings (5 strings each name 2 different Electric-Drive-variant catalogue pages). Approved: 77 Machine nodes, `models_covered` list property.
2. **Sheet 13 (`HAS_FITMENT`=943, `RECEIVES`=1631, `USES`=558) vs the detail tables (fitment=944, machine_service=1694, digital_services=616).** Approved decision: detail tables are the source of truth; sheet 13's `HAS_FITMENT`/`RECEIVES`/`USES` (plus `FITS` and `PROVIDES_CATALOGUE_FOR`) are deferred, not imported. See `IMPORT_DESIGN_REPORT.md` §10.
3. ~~**`Channel` as a node vs a property**~~ **RESOLVED** — approved as a node. The separate label-content issue found during final pre-import review (the source `To Name` text varying per relationship for `CH-EXTERNAL`) is fixed — see `CHANNEL_REVIEW.md`.
4. **17 `FITS` rows with blank targets and 1 `PROVIDES_CATALOGUE_FOR → 'ALL'` row** — source data quality issues, not something to silently patch. Held in `16_REVIEW_REQUIRED`, deferred per item 2 above.

## 21. Recommended next implementation phase

Once the above is confirmed: write (not yet run) a `neo4j/scripts/build_cypher_import.py` that emits parameterized `LOAD CSV` / `UNWIND` Cypher for each node and relationship type listed in §3–11, in dependency order (Category → Machine → Part/Attachment/Service/DigitalService → relationships), plus the uniqueness constraints in `GRAPH_SCHEMA_MATRIX.csv`. That script should still not execute against Aura until you've reviewed the generated Cypher text — matching the same "produce, don't run" discipline used in this phase.
