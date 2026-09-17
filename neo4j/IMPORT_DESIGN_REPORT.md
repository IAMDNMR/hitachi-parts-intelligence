# Import Design Report

No Neo4j connection made. No Aura credentials used. No Cypher executed against any database. `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` and every file under `neo4j/data/` are untouched (verified by file timestamp, unchanged from the cleaning phase — see below).

## 1. Final node model

9 labels imported: `Category` (17), `Machine` (77), `Specification` (1635), `Application` (29 distinct, from 328 rows), `Part` (43: 20 `ORDERABLE_OEM_PART` + 23 `PRODUCT_LINE_PART_FAMILY`), `Attachment` (17), `Service` (22), `DigitalService` (8 distinct, from 616 rows), `Channel` (2). Full property lists are in each file under `neo4j/import/nodes/`. No node created for any future/deferred entity — see §10.

## 2. Final relationship model

| Relationship | Count expected | File |
|---|---|---|
| `BELONGS_TO` (Machine→Category) | 77 | `relationships/machine_category.cypher` |
| `CHILD_OF` (Category→Category) | 16 | `relationships/machine_category.cypher` |
| `HAS_SPECIFICATION` (Machine→Specification) | 1635 | `relationships/machine_specification.cypher` |
| `HAS_APPLICATION` (Machine→Application) | 328 | `relationships/machine_application.cypher` |
| `HAS_PART_FITMENT` (Machine→Part) | **943** (see §11) | `relationships/machine_part_fitment.cypher` |
| `FITS` (Attachment→Machine, model-level) | **14** (see §13) | `relationships/machine_attachment.cypher` |
| `HAS_SERVICE` (Machine→Service) | 1694 | `relationships/machine_service.cypher` |
| `REQUIRES_PART` (Service→Part) | 11 | `relationships/service_part_requirement.cypher` |
| `HAS_DIGITAL_SERVICE` (Machine→DigitalService) | 616 | `relationships/machine_digital_service.cypher` |
| `DELIVERED_BY` (Service→Channel) | 23 | `relationships/channel_relationships.cypher` |
| `NOTIFIES` (DigitalService→Channel) | 2 | `relationships/channel_relationships.cypher` |
| `SUPPORTS` (DigitalService→Service) | 2 | `relationships/channel_relationships.cypher` |
| `INTEGRATES` (DigitalService→DigitalService) | 1 | `relationships/channel_relationships.cypher` |
| `AFFECTS_MAINTENANCE_OF` (Attachment→Part) | 1 | `relationships/channel_relationships.cypher` |
| *(none — maintenance is 9 list-property SETs on `Part`, not a relationship; see §8)* | 9 Part nodes updated, ~11 guideline entries total | `relationships/maintenance.cypher` |

## 3. Primary keys

Full table in `neo4j/import/IMPORT_KEY_MAP.md`. In brief: every imported label keys on the source's own ID column except `Application` (no source ID exists — keyed on canonicalized name) and `Channel` (no source sheet — keyed on the ID found in `relationships.csv`'s `To ID`). Nothing keys on row position, display name where a real ID exists, or a URL.

## 4. Constraints

9 uniqueness constraints (one per label) + 1 existence constraint (`Part.record_class`). Full reasoning in `neo4j/import/CONSTRAINT_DESIGN.md`, including the caveat that the existence constraint may need to become a query-time check instead, depending on the target Aura tier's support for property existence constraints.

## 5. Indexes

7 lookup indexes tied to named query patterns (part number, part name, machine model, machine category, service name, attachment name, category name) — not one per property. Full reasoning in `neo4j/import/02_indexes.cypher`'s header comments.

## 6. Import order

1. `01_constraints.cypher`
2. `nodes/categories.cypher`
3. `nodes/machines.cypher`
4. `nodes/specifications.cypher`
5. `nodes/applications.cypher`
6. `nodes/attachments.cypher`
7. `nodes/parts.cypher`
8. `nodes/services.cypher`
9. `nodes/digital_services.cypher`
10. `nodes/channels.cypher`
11. `relationships/machine_category.cypher` (needs Machine + Category)
12. `relationships/machine_specification.cypher` (needs Machine + Specification)
13. `relationships/machine_application.cypher` (needs Machine + Application)
14. `relationships/machine_attachment.cypher` (needs Attachment + Machine + `MODEL_CODE_INVENTORY.csv` staged as a temporary helper — see §13)
15. `relationships/machine_part_fitment.cypher` (needs Machine + Part)
16. `relationships/machine_service.cypher` (needs Machine + Service)
17. `relationships/service_part_requirement.cypher` (needs Service + Part)
18. `relationships/machine_digital_service.cypher` (needs Machine + DigitalService)
19. `relationships/channel_relationships.cypher` (needs Service/DigitalService/Attachment/Part/Channel)
20. `relationships/maintenance.cypher` (needs Part)
21. `02_indexes.cypher` (can run any time after the labels it targets exist; placed last so index creation doesn't slow down the bulk load)

Matches the brief's suggested order with `channels.cypher` moved to position 10 (node creation) ahead of any relationship file — `channel_relationships.cypher` (a relationship file) depends on it — and indexes deliberately moved to last for load performance.

## 7. Idempotency strategy

Every node file uses `MERGE (n:Label {primary_key: ...})` followed by `SET` for every other property — re-running the same file updates the existing node's properties rather than creating a duplicate, so a corrected re-export of the same CSV can be re-run safely. Every relationship file uses `MERGE` on the relationship pattern (for most types) or `MERGE ... {natural_key: ...}` where multiple relationships of the same type could otherwise exist between the same two nodes with different evidence (`HAS_PART_FITMENT` keyed additionally on `fitment_id`, `REQUIRES_PART` on `requirement_id`, `HAS_MAINTENANCE_GUIDELINE` on `maintenance_id`) — this prevents the idempotent re-run from collapsing two genuinely different fitment/requirement/maintenance rows that happen to connect the same two nodes. `CREATE` is never used anywhere in `neo4j/import/`.

## 8. Evidence strategy

`HAS_PART_FITMENT.evidence` (`EXACT_MODEL`/`MODEL_RANGE`/`CATEGORY`/`NOT_STATED`) and `HAS_SERVICE.applicability` (`ALL_MACHINES_STATED`/`CATEGORY`/`NOT_STATED`) are set from the values already computed and reviewed in the cleaning phase — this design does not recompute or reinterpret them. `evidence_original`/`applicability_original` are also carried through, so the source's own free text is never lost behind the normalized value.

**Maintenance — revised during final pre-import review** (decision #4 still holds: no standalone node). The design that reached that phase's report used a `HAS_MAINTENANCE_GUIDELINE` self-relationship on `Part`; review correctly flagged that as semantically awkward and asked for a fresh look at Machine/Service/Part attachment. Re-inspection confirmed:
- *Machine* — still rejected: every row's `Machine ID` value is the sentinel `"ALL - see Applies To"`, not a real machine reference.
- *Service* — still mostly rejected, but with a more precise finding than the earlier pass: only 1 of 10 rows (`MS-010`) has strong textual correspondence to a specific Service (its activity name and calendar-interval text both echo `SVC-004`/`SVC-008`). Linking only that one row while leaving the other 9 unlinked would be an inconsistent special case, not a general schema rule — not implemented.
- *Part* — confirmed as the only consistently resolvable anchor (9 of 10 rows). The self-relationship was replaced with **parallel list properties directly on `Part`** (`maintenance_activities`, `maintenance_intervals`, etc., all index-aligned) — this still correctly supports `PT-032`'s two guidelines (1500h with a breaker attachment vs 2000h with other attachments) without either node collision or an artificial self-loop. See `neo4j/FINAL_PRE_IMPORT_REVIEW.md` item 1 for the full before/after reasoning.

## 9. Provenance strategy

Implements `FINAL_GRAPH_SCHEMA.md` §12 exactly: `source_id`/`confidence`/`data_class` as compact properties on the node or relationship the fact belongs to, never a `Source`/`Provenance` node, never a URL in a business property. `provenance.csv` (47 rows) is not imported as graph nodes in this phase — it remains a separate, non-graph reference table joinable by `source_id` for audit purposes, exactly as recommended.

## 10. Deferred relationships

Not imported, per approved decision #3: `RECEIVES` (1631 rows — Machine→Service, sheet 13's coarser restatement of `HAS_SERVICE`), `USES` (558 rows — Machine→DigitalService, restatement of `HAS_DIGITAL_SERVICE`), `FITS` from sheet 13 (17 rows, **all 17 have a blank `To ID`** in the source — not importable as-is regardless of the deferral decision), `PROVIDES_CATALOGUE_FOR` (1 row, target is the literal sentinel `ALL`, not a resolvable Part). None of these rows were deleted from `relationships.csv` — they remain there, untouched, for whenever a future phase decides to reconcile and import them.

Not created as future entities (zero source rows for any of them): `Customer`, `Dealer`, `Warehouse`, `Inventory`, `ServiceJob`, `Order`, `OrderLine`, `Shipment`, `Warranty`, `MachineAlert`.

## 11. Expected counts

All match the brief's table except two, both with a documented reason — not silently forced to match:

| Dataset | Brief's expectation | Actual import count | Reason for the difference |
|---|---|---|---|
| Machine-Part Fitment | 944 | **943** | `machine_part_fitment.cypher` excludes 1 row (`FIT-0032`) whose `Machine ID` is the source's own scope-descriptor sentinel `"NOT IN CURRENT CATALOGUE"` — not a real machine, so no `Machine` node exists to attach it to. The row is not deleted from `machine_part_fitment.csv`; it's simply not a resolvable graph edge. |
| Attachment→Machine `FITS` | (not explicitly given a count in the brief; `GRAPH_RELATIONSHIP_MATRIX.csv` estimated "subset of 17") | **14** | Only 7 of 17 attachments have `Compatible Machine Model` populated at all; of the model-code text in those 7 rows, 14 fragments resolve cleanly against `MODEL_CODE_INVENTORY.csv` and 7 do not (free-text qualifiers like `"ZX10 to ZX85 (as stated)"` or `"(short reach front)"`, not literal codes — see §13). |

Every other count (Categories 17, Machines 77, Specifications 1635, Applications 29 distinct/328 rows, Attachments 17, Parts 43 [20/23], Services 22, Machine-Service 1694, Digital Services 8 distinct/616 rows, Channels 2, Service-Part Requirements 11, Provenance 47, Relationships 3283 [186 CORE/3097 DERIVED]) matches the brief exactly, confirmed by the dry-run validator.

## 12. Dry-run validation results

`neo4j/scripts/dry_run_validator.py` — simulates every `MATCH`/`MERGE` in the Cypher files directly against the CSVs, in plain Python, with **no Neo4j driver and no network call**. Full checklist from Step 10, all passing on the final run:

- ✅ Every relationship endpoint exists (11 foreign-key checks across all detail sheets, plus sheet-13's imported types)
- ✅ Every node key is unique (Category, Machine, Specification, Part, Attachment, Service; DigitalService verified to correctly *converge* to 8 via MERGE, not error as a duplicate)
- ✅ Application converges to exactly 29 distinct names
- ✅ No unsupported labels (9 approved, 9 used)
- ✅ No unsupported relationship types (every type in `relationships.csv` is either imported or in the explicit deferred set — this check caught two of my own oversights, `HAS_FITMENT` and `REQUIRES`, before this report was finalized — see the honesty note below)
- ✅ No fake IDs (Category parent-ID resolution corrected during this phase — see below)
- ✅ No fake part numbers (0 `PRODUCT_LINE_PART_FAMILY` rows carry a part_number; 0 `ORDERABLE_OEM_PART` rows lack one)
- ✅ No URL pollution in any property a node `.cypher` file actually sets
- ✅ No family converted into SKU
- ✅ No range converted into exact model (evidence direction checked both ways)
- ✅ Evidence semantics preserved (every fitment row has a value; original text kept alongside)
- ✅ CORE/DERIVED distinction preserved (`relationship_class` present on all 3283 sheet-13 rows)

**Two mistakes found and fixed while building this design, documented rather than hidden:**
1. `machine_category.cypher`'s first draft matched `Parent Category` against `Category Name` text. Direct inspection of the data showed `Parent Category` actually holds a `Category ID` (or the literal sentinel `(root)` for the top node) — fixed before this was finalized.
2. `dry_run_validator.py`'s first run correctly caught that `HAS_FITMENT` and `REQUIRES` (both sheet-13 relationship types) weren't in the "imported or deferred" set — an oversight in the deferred-types list, not a design decision. Fixed by adding them to the deferred set, matching the intent already stated in `FINAL_GRAPH_SCHEMA.md` §11.

## 13. Known limitations

- **`Attachment` category-level compatibility text is not resolved into a graph edge.** 10 of 17 attachments state only a `Compatible Machine Category` (e.g. `"Excavators (mini, medium, large, wheeled)"`), which spans multiple real `Category` rows and can't be split into exact Category IDs without semantic interpretation the source doesn't make explicit. Kept as a string property on `Attachment` (`compatible_machine_category`) rather than a fuzzy-matched, possibly-wrong edge.
- **7 of 84 `Compatible Machine Model` text fragments don't resolve to a model code** in `machine_attachment.cypher` — they're descriptive qualifiers (ranges, parentheticals) rather than literal codes (full list in the dry-run output and in the file's own trailing comment). Silently skipped, not guessed at.
- **Maintenance list-properties on `Part` are not idempotent on re-run** (§7, §8) — `SET p.x = coalesce(p.x, []) + value` appends every time the file runs, so re-running `maintenance.cypher` without first clearing the 9 properties would duplicate entries. Every other file in this design is safely re-runnable; this one file is the exception, called out explicitly rather than silently shipped.
- **`Channel.label`** — resolved during final pre-import review (`neo4j/reports/CHANNEL_REVIEW.md`). `CH-EXTERNAL`'s `To Name` text genuinely varies per relationship (a source fact, not a data error), and was being read into the wrong place in the schema (node label instead of relationship property). Fixed: `Channel.label` is now a stable, generic description; the per-service detail (`"Yes (Reman centre)"`, `"Yes (BNP Paribas Leasing Solutions; DLL)"`) moved to `DELIVERED_BY.provider_detail`.
- **3 attachment model-range fragments (ATT-014/015/016) are real, resolvable machine references currently left unresolved by design** — see `neo4j/reports/ATTACHMENT_FITMENT_RECONCILIATION.md`. The exact-match resolver deliberately doesn't attempt delimiter normalization, favouring zero false positives over higher recall in this phase.
- **`part_record_class_exists` constraint may not be supported on all Aura tiers** (§4) — needs confirming against the actual target instance before Step 3's file is ever run for real.

## 14. Exact next step

Final pre-import review (`neo4j/FINAL_PRE_IMPORT_REVIEW.md`) has now resolved the Maintenance design, the `CH-EXTERNAL` label, and reconciled both count deviations in §11 with full evidence. See that document for the readiness verdict. Once approved, per the phase sequence you specified: **LOCAL IMPORT TEST** — spin up a local Neo4j instance (not Aura), copy `neo4j/data/*.csv` and `neo4j/reports/MODEL_CODE_INVENTORY.csv` into its import directory, and run the files in the order in §6, checking the actual counts against §11 and running `03_validation_queries.cypher`'s count/orphan/duplicate queries against the real (local) database — before any Aura connection is made or requested.

**No Neo4j Aura connection made. No Aura credentials used or requested. No Cypher run against any database, local or remote. No constraints or indexes created anywhere. Cleaned workbook and CSVs untouched. Stopping here as instructed.**
