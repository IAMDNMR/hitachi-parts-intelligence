# Import Key Map

Canonical primary key for every node type imported in this phase. None depends on Excel row position, display name alone, or a URL — every key below is a source-published identifier already present in the cleaned CSVs.

| Label | Canonical primary key | Source column | Source identifier scheme | Uniqueness |
|---|---|---|---|---|
| `Category` | `category_id` | `Category ID` (categories.csv) | `CAT-NNN`, source-assigned | Unique — verified 0 duplicates across 17 rows |
| `Machine` | `machine_id` | `Machine ID` (machines.csv) | `MC-NNN`, source-assigned, one per catalogue/product page (approved: 77 nodes, not 84) | Unique — verified 0 duplicates across 77 rows |
| `Specification` | `spec_id` | `Spec ID` (specifications.csv) | `SPEC-NNNN`, source-assigned | Unique — verified 0 duplicates across 1635 rows |
| `Application` | `name` | `Application` (applications.csv), canonicalized casing | Free text, no source ID of its own | Unique on canonical name — 29 distinct values from 328 rows |
| `Part` | `part_id` | `Part ID` (parts.csv) | `PT-NNN`, source-assigned | Unique — verified 0 duplicates across 43 rows |
| `Attachment` | `attachment_id` | `Attachment ID` (attachments.csv) | `ATT-NNN`, source-assigned | Unique — verified 0 duplicates across 17 rows |
| `Service` | `service_id` | `Service ID` (services.csv) | `SVC-NNN`, source-assigned | Unique — verified 0 duplicates across 22 rows |
| `DigitalService` | `digital_service_id` | `Digital Service ID` (digital_services.csv) | `DS-NNN`, source-assigned | Unique on the 8 distinct values (616 rows reference them) |
| `Channel` | `channel_id` | `To ID` where `To Entity Type = Channel` (relationships.csv) | `CH-DEALER` / `CH-EXTERNAL`, source-assigned | Unique — exactly 2 distinct values |

## Not assigned a key in this phase (no current data)

`Customer`, `Dealer`, `Warehouse`, `Inventory`, `PartsRequirement` (modelled as a relationship, not a node — see `FINAL_GRAPH_SCHEMA.md` §7), `ServiceJob`, `Order`, `OrderLine`, `Shipment`, `Warranty`, `MachineAlert`, `MaintenanceActivity` (approved decision: no standalone node — see `neo4j/IMPORT_DESIGN_REPORT.md` §8).

## Rejected key candidates

- **URL** — never used as an identifier anywhere, even though every Machine/Part/Service row carries one in the source. URLs are dropped from every node property (kept only in the untouched original workbook).
- **Display name alone** (e.g. Machine's `Model` text) — rejected for `Machine`, because the model-code investigation (`MODEL_CODE_RECONCILIATION_REPORT.md`) proved the same code text (`EX2000-7`) legitimately names two different catalogue pages (MC-014, MC-015). Using it as a key would silently merge them.
- **Row position** — never used; every source sheet's own ID column is honoured instead.
