# Model Code Reconciliation Report

No Neo4j connection made. No import run. `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` and `02_MACHINE_MASTER` were not modified — this is a read-only investigation.

## 1. Problem statement

The source workbook's own `00_README` states the machine catalogue is "77 product detail pages covering 79 distinct model codes." The cleaned dataset's `Model Count` column sums to 84 across those same 77 records. Before continuing schema/import work, this had to be traced to its actual cause in the source data rather than picking a number.

## 2. Source claim

Found verbatim in `00_README`, twice:
- `"MACHINE — A product the HCME website treats as a distinct product detail page (77 of them, covering 79 model codes). Sheet 02."`
- `"02_MACHINE_MASTER — 77 data rows. Complete HCME European machine catalogue: 77 product detail pages covering 79 distinct model codes."`

A third, related principle also found in `00_README`: **"5. No silent expansion — Published model ranges (e.g. 'ZX300-7 - ZX350-7') are recorded verbatim. Only literal model codes are matched to catalogue machines; intermediate models are never interpolated."** This confirmed that hyphen-joined range strings (like `ZX250-300-350-7`) are deliberately kept as one literal string, not split — relevant to Steps 4–5 below.

No other sheet in the workbook independently recomputes or corroborates 79 or 84 — both figures trace to `02_MACHINE_MASTER` alone.

## 3. Cleaned-data calculation

`Models Covered`, split on `|`, summed across all 77 rows: **84**. Verified directly against the raw source (not the cleaned CSV) — 70 rows have exactly 1 code, 7 rows have exactly 2 codes (`Model Count = 2`, `|`-delimited):

| Machine ID | Models Covered |
|---|---|
| MC-026 | ZX690LCH-7 \| ZX690LCR-7 |
| MC-027 | ZX890LCH-7 \| ZX890LCR-7 |
| MC-033 | ZX210LC-7 \| ZX210LCN-7 |
| MC-037 | ZX250LC-7 \| ZX250LCN-7 |
| MC-038 | ZX300LC-7 \| ZX300LCN-7 |
| MC-040 | ZX350LC-7 \| ZX350LCN-7 |
| MC-045 | ZX17U-6 \| ZX19U-6 |

70×1 + 7×2 = 84.

## 4. Exact 84-code inventory

Full inventory (all 84 code slots, with their source machine ID, catalogue record name, raw value, and source URL) is in **`neo4j/reports/MODEL_CODE_INVENTORY.csv`**.

## 5. Reconstruction of 79 — the actual cause, with evidence

**79 = the count of *distinct model-code text strings* among those 84 slots.** Computed directly: `len(set(all_84_codes)) == 79`. The gap is exactly 5, caused by 5 code strings each appearing on **two different catalogue pages**:

| Code | Appears on | Evidence it's two real, different products |
|---|---|---|
| EX2000-7 | MC-014, MC-015 | MC-014 URL ends `.../product.ex2000-7/`; MC-015 URL ends `.../product.ex2000-7e/`. MC-014 `Available In: Europe`; MC-015 `Available In: Not stated`. |
| EX2600-7 | MC-016, MC-017 | Same pattern: `.../ex2600-7/` vs `.../ex2600-7e/` |
| EX3600-7 | MC-018, MC-019 | Same pattern: `.../ex3600-7/` vs `.../ex3600-7e/` |
| EX5600-7 | MC-020, MC-021 | Same pattern: `.../ex5600-7/` vs `.../ex5600-7e/` |
| EX8000-7 | MC-022, MC-023 | Same pattern: `.../ex8000-7/` vs `.../ex8000-7e/` |

The `...e` URL suffix is the electric-drive variant of each large excavator (consistent with `EX2000-7E`/`EX2600-7E`/etc. naming used elsewhere in this project's other, unrelated data sources). **The source's own `Model`/`Models Covered` text field was never given a distinguishing code for the electric page** — it repeats the standard model's code string verbatim — even though the page itself, its URL, and (per `Available In`) its regional availability are genuinely different. This is a real gap in how that one field was populated for these 5 pages, not an error in either the 79 or the 84 count: **both are internally consistent, counting two different things** (79 = distinct code *text*; 84 = total code *slots*, i.e. one per (machine record, code) pair).

This matches classification **E (counts a different field)** from the brief's list of hypotheses — more precisely, both counts read the same field, but 79 deduplicates identical text while 84 does not. This is not an arithmetic or documentation error (**F**), not an alias/duplicate exclusion (**B**), and not a different delimiter (**D**) — it's a straightforward distinct-string-vs-total-slot difference, caused by 5 pages sharing one code's text.

## 6. Difference between the two

84 (total slots) − 5 (code strings that repeat across exactly 2 pages each) = **79 distinct strings.** Full per-code classification: **`neo4j/reports/MODEL_CODE_RECONCILIATION.csv`** — 74 rows classified `CONFIRMED_DISTINCT_MODEL` (appear once), 5 rows classified `CONFIGURATION_VARIANT` (the pairs above).

## 7. Evidence for each discrepancy

See the URL/Available-In evidence in §5, and the full per-code detail in `MODEL_CODE_RECONCILIATION.csv`'s `evidence` column.

## 8. Affected records

- **Machine-Part Fitment (07)**, **Machine-Service (09)**, **Specifications (03)**, **Applications (04)**, **Digital Services (12)**, **Attachments (05)**, **13_AFTER_SALES_RELATIONSHIPS**: all key off `Machine ID` (e.g. `MC-014`, `MC-015`), not off the model-code text. **None of these are affected by the 79-vs-84 ambiguity** — they already correctly treat MC-014 and MC-015 as two separate machines regardless of what their `Model` text says.
- **Parts Store machine filtering / future machine-specific queries**: only affected if a filter or search were built to key off the literal model-code *string* instead of `Machine ID` — e.g. a naive "search for EX2000-7" that doesn't know it should match both MC-014 and MC-015. This is worth flagging to whoever builds that filter, but is not a defect in the cleaned dataset itself.
- **Nothing else in the graph is affected** by whether the "true" count is quoted as 77, 79, or 84 — they measure three different things (pages, distinct code text, total code slots) and none of them is used elsewhere as a row count or a join key.

## 9. Impact on graph design

None of the relationship counts, evidence classifications, or conflict findings from the earlier schema review need to change. The finding does reinforce the recommendation already made in `FINAL_GRAPH_SCHEMA.md` (§4): `Machine` should be one node per catalogue/product-page record (77 nodes, keyed on `Machine ID`), never per model-code string — if it were the latter, MC-014 and MC-015 would collide into one `EX2000-7` node and silently lose the fact that they're different products with (likely) different specs and availability.

## 10. Recommended canonical representation

**Option A: one Machine node per catalogue/product-page record (77 nodes), with `models_covered` as a list property.** Confirmed, not changed by this investigation. Specifically:
- The 7 `|`-delimited rows (§3) each get one Machine node with `models_covered: [code1, code2]` — both codes belong to the same page/spec/fitment data, so splitting them into two nodes would fabricate a second machine record with no independent specs, fitment, or URL of its own.
- The 5 duplicated-string pairs (§5) already correctly get two separate Machine nodes (MC-014 ≠ MC-015) — this investigation changes nothing about that, it only explains why their `models_covered` text happens to match.
- **Option B (one node per distinct model code)** is rejected: it would either merge MC-014/MC-015 into one incorrect node (losing the Electric Drive distinction) or require inventing a code string like `EX2000-7E` that neither the source nor `hitachicm.com` actually publishes in that field — both violate the "do not invent" rule.
- **Option C (Machine Family + Model nodes)** is not supported by the evidence: there's no source field expressing a family grouping above the catalogue-page level beyond `Category`/`Product Family`, which are already modelled. Introducing a new `Family` layer solely to hold pipe-split code pairs would be schema complexity the data doesn't ask for.

## 11. Unresolved records

None. All 79 distinct codes are classified in `MODEL_CODE_RECONCILIATION.csv` with direct evidence; every one of the 84 slots is accounted for in `MODEL_CODE_INVENTORY.csv`. No code was invented, removed, or merged in producing these files.

## 12. Exact action required before import

None — this investigation confirms the schema decision already recommended in `FINAL_GRAPH_SCHEMA.md` is correct as written; no change to `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`, `02_MACHINES`, machine IDs, model counts, or relationships is needed. This closes ambiguity item #1 from `neo4j/SCHEMA_REVIEW_REPORT.md` §3. The three remaining items in that report (§4: Channel as node vs property; sheet 13's `RECEIVES`/`USES`/`FITS`/`PROVIDES_CATALOGUE_FOR` rows; the Maintenance node decision) are still open and still require your approval before an import script is written.

## Validation

- No model codes invented: every one of the 84 rows in `MODEL_CODE_INVENTORY.csv` is a substring taken verbatim from the source's own `Models Covered` field, split only on the delimiter (`|`) the source itself uses.
- No model codes silently removed: 84 in, 84 out (`MODEL_CODE_INVENTORY.csv` row count == 84, asserted in the script).
- No aliases silently merged: the 5 `CONFIGURATION_VARIANT` codes are recommended to stay as two separate Machine nodes, not merged into one.
- No configuration variants silently merged: same point — explicitly called out, not collapsed.
- No source values modified: read-only against both the source and cleaned workbooks throughout this investigation.
- Every one of the 79 codes accounted for: `MODEL_CODE_RECONCILIATION.csv` row count == 79, asserted in the script.
- Every difference from the 79-count documented: the 5 duplicated strings and their evidence are listed in full in §5.

## Files produced

- `neo4j/reports/MODEL_CODE_INVENTORY.csv` (84 rows)
- `neo4j/reports/MODEL_CODE_RECONCILIATION.csv` (79 rows)
- `neo4j/reports/MODEL_CODE_RECONCILIATION_REPORT.md` (this file)
- `neo4j/scripts/model_code_reconciliation.py` (the script that produced the two CSVs, re-runnable, asserts both counts)

**No Neo4j connection made. No constraints, indexes, nodes, or relationships created. No import run. Waiting for your approval of the model-code decision (§10) and the three still-open items from the prior schema review before any import script is written.**
