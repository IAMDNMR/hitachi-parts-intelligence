# Final Pre-Import Review

No Neo4j connection made. No Aura credentials used or requested. No import run. `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` and every file under `neo4j/data/` are untouched — confirmed by file timestamp (13:18, unchanged from the cleaning phase) both before and after this review.

## 1. Maintenance decision

**Changed.** The design reviewed by this phase used a `HAS_MAINTENANCE_GUIDELINE` self-relationship on `Part`. Re-inspecting `10_MAINTENANCE_SCHEDULE`, `11_SERVICE_PART_REQUIREMENTS`, `08_SERVICE_CAPABILITIES`, and `09_MACHINE_SERVICE_MATRIX` confirmed:

- **Machine attachment**: still rejected. Every one of the 10 maintenance rows' `Machine ID` is the sentinel `"ALL - see Applies To"`, not a real machine reference.
- **Service attachment**: rejected, but with a more precise finding than the earlier pass produced. Only **1 of 10 rows** (`MS-010`, "Regular services and inspections under Extended Warranty") has real textual correspondence to a specific Service — its activity name echoes `SVC-004` ("Regular services and inspections") and its calendar-interval text ("Up to 84 months (Full Coverage)") echoes `SVC-008` ("Extended Warranty - Full Coverage"). Linking only that one row while leaving the other 9 unlinked would be an inconsistent one-off, not a schema rule, so no Service edge is created for any maintenance row. No Service record was invented.
- **Part attachment**: confirmed as the only consistently resolvable anchor — 9 of 10 rows' `Required Part` text matches a real `Part` by name (`MS-005`, "Daily inspection", correctly has none — a visual check needs no consumable).

**Revised design**: no relationship at all. Maintenance data is now carried as 9 parallel, index-aligned **list properties directly on `Part`** (`maintenance_ids`, `maintenance_activities`, `maintenance_intervals`, `maintenance_interval_units`, `maintenance_applies_to`, `maintenance_components`, `maintenance_data_classes`, `maintenance_source_ids`, `maintenance_confidences`). This is simpler than both the rejected self-relationship *and* a new node, and it's the only representation of the three tried that both (a) doesn't invent a Machine/Service link the source doesn't support and (b) doesn't lose data for `PT-032`, which is required by two different maintenance rows (`MS-002`: 1500h with a breaker attachment; `MS-003`: 2000h with other attachments) — a flat scalar property would have silently overwritten one interval with the other.

**One new limitation this introduces, documented rather than hidden**: unlike every other file in the import design, `maintenance.cypher`'s list-append pattern (`SET p.x = coalesce(p.x, []) + value`) is **not idempotent** — re-running it without first clearing the 9 properties would duplicate entries. Flagged in `IMPORT_DESIGN_REPORT.md` §7 and §13.

**Files updated**: `neo4j/reports/FINAL_GRAPH_SCHEMA.md` §8, `neo4j/IMPORT_DESIGN_REPORT.md` (§2 relationship table, §8, §13, §14), `neo4j/reports/GRAPH_SCHEMA_MATRIX.csv` (MaintenanceActivity row), `neo4j/import/relationships/maintenance.cypher` (full rewrite), `neo4j/scripts/dry_run_validator.py` (new simulation + `HAS_MAINTENANCE_GUIDELINE` removed from the approved relationship-type set).

## 2. Channel decision

**Root cause found, design fixed — this was a mistake in the earlier import design, not a source data problem.** Full trace in `neo4j/reports/CHANNEL_REVIEW.md`. Summary: `CH-EXTERNAL` is referenced by two different relationship rows in `13_AFTER_SALES_RELATIONSHIPS`, each with a **different** `To Name` (`"Yes (Reman centre)"` for SVC-016; `"Yes (BNP Paribas Leasing Solutions; DLL)"` for SVC-022) — because that text answers a **per-service** question ("who is the external provider for this service?"), not a fixed identity for the Channel node. By contrast, `CH-DEALER`'s `To Name` is identical (`"HCME authorised dealer network"`) across every row that references it — genuinely stable, correctly used as-is.

**Classification: A — genuinely source-defined content, but read into the wrong place in the schema.** Not B (copied from an unrelated field), not C (unrelated descriptive value), not D (ambiguous) — comparing the two rows side by side made the meaning unambiguous.

**Fix**: `Channel.label` is now a stable, generic description for both channels; the per-service provider text moved to `provider_detail` on the `DELIVERED_BY` relationship, where a fact that varies by (Service, Channel) pair belongs. Nothing was removed or guessed at — both original texts are preserved verbatim, just relocated.

**Files updated**: `neo4j/reports/CHANNEL_REVIEW.md` (new), `neo4j/reports/FINAL_GRAPH_SCHEMA.md` (Channel properties, DELIVERED_BY properties, §20 item 3), `neo4j/IMPORT_DESIGN_REPORT.md` §13, `neo4j/reports/GRAPH_RELATIONSHIP_MATRIX.csv` (DELIVERED_BY row), `neo4j/import/nodes/channels.cypher` (full rewrite), `neo4j/import/relationships/channel_relationships.cypher` (DELIVERED_BY section), `neo4j/scripts/dry_run_validator.py` (new consistency check).

## 3. Fitment reconciliation

Full detail in `neo4j/reports/FITMENT_COUNT_RECONCILIATION.md`. Confirmed exactly as the brief specified, with direct evidence:

**944 source/cleaned fitment records. 943 valid graph relationships. 1 excluded source sentinel.**

The excluded row, `FIT-0032`, has `Machine ID: "NOT IN CURRENT CATALOGUE"` and `Machine Model: "ZX240N-7"` — a model code that doesn't appear in any of the 77 current catalogue records. The row's own `Notes` field states this explicitly: *"Model group 'ZX240N-7' has no matching product detail page in the current EU catalogue (superseded, other-region or intermediate model). Recorded verbatim - NOT expanded or invented."* Confirmed: no valid relationship was lost (the fact is still in the CSV, just not attachable to a `Machine` node that doesn't exist), no fake machine node should be created for it, and `machine_part_fitment.cypher` already excludes it explicitly rather than letting it silently fail to match.

## 4. Attachment reconciliation

Full detail in `neo4j/reports/ATTACHMENT_FITMENT_RECONCILIATION.md`. Of the 7 previously-unresolved fragments:

- **3** (ATT-014, ATT-015, ATT-016) are **real, specific model-range references**, resolvable in principle (to MC-003; MC-060; and MC-004+MC-005 respectively) but not currently imported — the exact-match resolver deliberately doesn't attempt delimiter normalization, favouring zero false positives. Flagged as a safe, well-scoped future improvement, not implemented under this review's time budget to avoid introducing unverified matching logic.
- **2** (ATT-005, ATT-007) are **genuine source-stated ranges**, correctly kept verbatim per the source's own "no silent expansion" policy — not intended to decompose into individual codes at all.
- **1** (ATT-002) is **descriptive prose** about codes already resolved elsewhere in the same row, not a separate compatibility claim.
- **1** (ATT-017, `"ZX135US-7 (short reach front)"`) is **genuinely ambiguous** — no exact match among the 79 known model codes, and nothing in the source disambiguates it from the two closest candidates (`ZX135US-7B`, `ZX135US-7 SRF`). Not resolved, not guessed at.

No compatibility was invented for any of the 7.

## 5. Final schema consistency check

Cross-checked `FINAL_GRAPH_SCHEMA.md`, `GRAPH_SCHEMA_MATRIX.csv`, `GRAPH_RELATIONSHIP_MATRIX.csv`, `IMPORT_KEY_MAP.md`, `CONSTRAINT_DESIGN.md`, and `IMPORT_DESIGN_REPORT.md` against each other and against the revised Cypher files. Found and fixed 2 places where the earlier documents still described the pre-review Maintenance/Channel design:

- `GRAPH_SCHEMA_MATRIX.csv`'s `MaintenanceActivity` row said "would attach to Service" — updated to describe the approved Part-list-property design.
- `GRAPH_RELATIONSHIP_MATRIX.csv`'s `DELIVERED_BY` row didn't mention `provider_detail` — added.

`IMPORT_KEY_MAP.md` and `CONSTRAINT_DESIGN.md` needed no changes — neither made any claim about Maintenance or Channel structure that the revision contradicts (Channel's key/constraint design is unaffected by the label-*content* fix; `MaintenanceActivity` was already correctly listed there as "no standalone node").

## 6. Dry-run result

`neo4j/scripts/dry_run_validator.py` re-run after all fixes above, with 2 new checks added (Channel label-stability consistency; maintenance list-property non-overwrite). **All checks pass:**

- No duplicate node keys (Category, Machine, Specification, Part, Attachment, Service; DigitalService confirmed to correctly converge to 8 via MERGE)
- No dangling endpoints (every foreign key in every imported relationship resolves; the one known sentinel is correctly excluded, not silently failing)
- No fake SKUs (0 `PRODUCT_LINE_PART_FAMILY` rows carry a part number)
- No fake machine IDs (Category parent-ID resolution verified correct after the earlier `Parent Category` fix)
- No fake model codes (attachment resolution only matches against `MODEL_CODE_INVENTORY.csv`'s verified 79-code list, nothing invented for the 7 unresolved fragments)
- No unsupported relationship types (`HAS_MAINTENANCE_GUIDELINE` removed from the approved set now that it no longer exists in the design)
- No URL pollution
- Evidence semantics preserved (fitment evidence direction checked both ways, none collapsed wrong)
- CORE/DERIVED semantics preserved (`relationship_class` present on all 3283 sheet-13 rows)
- Family vs orderable part distinction preserved (20/23 split, verified both directions)
- **New**: `PT-032`'s 2 maintenance guidelines both present, not overwritten
- **New**: `CH-DEALER` label confirmed stable; `CH-EXTERNAL` confirmed to vary per relationship, confirming it correctly does NOT get a fixed node-level label

## 7. Remaining uncertainties

1. **3 attachment model-range fragments (ATT-014/015/016) are resolvable in principle but not currently imported** (§4 above) — a deliberate, documented choice to favour zero false positives over higher recall in this phase, not an oversight.
2. **`ATT-017`'s `"ZX135US-7 (short reach front)"` is genuinely ambiguous** — may need either a source-side lookup or your judgment call; not resolved here.
3. **Sheet 13's `HAS_FITMENT`/`RECEIVES`/`USES` count mismatches against the detail tables** (from the prior schema review, still open) — approved as deferred, not re-litigated in this review.
4. **`part_record_class_exists` constraint's Aura-tier support** (from `CONSTRAINT_DESIGN.md`) — still needs confirming against the actual target instance, not something a local dry run can verify.

None of these block a local (non-Aura) import test — they're either deliberately conservative choices, already-approved deferrals, or things that only the actual target database configuration (not a dry run) can settle.

## 8. Readiness status

**READY_FOR_LOCAL_IMPORT_TEST**

All three items this review was asked to resolve (Maintenance, Channel, both count reconciliations) are resolved with direct source evidence, not assumption. Two genuine design errors were found and fixed (the `Parent Category` field mapping, caught during the import-design phase itself, and the `CH-EXTERNAL` label mapping, caught in this review) — both are documented rather than silently corrected. The dry-run validator passes every check, including two new ones added specifically for this review's findings. The cleaned dataset (`HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`, `neo4j/data/*.csv`) remains completely untouched throughout.

**No Neo4j Aura connection made. No Aura credentials used or requested. No Cypher executed against any database. Stopping here as instructed — waiting for your go-ahead before the local (non-Aura) import test.**
