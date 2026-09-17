# Constraint Design

Explains every constraint in `01_constraints.cypher`. None of this has been executed.

## Uniqueness constraints (one per imported label)

| Constraint | Why |
|---|---|
| `category_id_unique` | `Category ID` is the canonical key (`IMPORT_KEY_MAP.md`); prevents two `MERGE` calls from ever creating duplicate Category nodes even if the load script is re-run or run out of order. |
| `machine_id_unique` | The single most important constraint in this schema. The model-code investigation proved that model-code *text* is not a safe key (`EX2000-7` names two different pages); `Machine ID` is. This constraint makes it structurally impossible to accidentally collapse MC-014 and MC-015 into one node during import. |
| `spec_id_unique` | 1635 rows, needs a hard guarantee against double-loading the same specification on a re-run. |
| `application_name_unique` | Deliberately on the *canonical* name (post-casing-normalization), not the raw `Application ID` — there is no `Application ID` in the source. This constraint is what makes `MERGE (a:Application {name: $name})` safe to call 328 times (once per Machine×Application row) and still end up with exactly 29 nodes. |
| `part_id_unique` | Also the anchor for `record_class` — see the existence constraint below. |
| `attachment_id_unique`, `service_id_unique`, `digital_service_id_unique`, `channel_id_unique` | Same reasoning as Category — small, stable ID sets, cheap insurance against duplicate creation on re-run. |

## Existence constraint

`part_record_class_exists` — `record_class` (`ORDERABLE_OEM_PART` | `PRODUCT_LINE_PART_FAMILY`) is the property that keeps a product-line family from ever behaving like a real orderable SKU (per `FINAL_GRAPH_SCHEMA.md` §14). Making it a hard existence constraint means the database itself refuses to create a `Part` node that skipped this classification, rather than relying on every future import script to remember to set it.

**Caveat, to confirm at Aura connection time**: property existence constraints on nodes require Neo4j Enterprise / Aura tiers that support them (not the free Aura tier). If the target Aura instance doesn't support it, drop this one constraint and instead assert `record_class IS NOT NULL` in the dry-run validator (already done — see `neo4j/scripts/dry_run_validator.py`) and in `03_validation_queries.cypher` (query 14-equivalent) as a query-time check instead of a database-enforced one.

## Deliberately not created

- No constraint on `Specification.spec_id` *and* a uniqueness constraint on `(machine_id, specification_name)` combined — the source itself already guarantees one `Spec ID` per (machine, spec name) pair (verified: 0 duplicate rows after cleaning), so a composite constraint would be redundant insurance for a property combination nothing in the import path can violate.
- No constraint on `Machine.model` or `Machine.models_covered` — deliberately non-unique (see `IMPORT_KEY_MAP.md`, "Rejected key candidates").
- No constraints for `Customer`/`Dealer`/`Order`/etc. — no data, no import, no constraint needed yet.
