# Fitment Count Reconciliation

## Statement

**944 source/cleaned fitment records. 943 valid graph relationships. 1 excluded source sentinel.**

This is what the evidence confirms — not assumed going in.

## The excluded row

`07_MACHINE_PART_FITMENT`, `Fitment ID: FIT-0032`, full raw content:

| Field | Value |
|---|---|
| Machine ID | `NOT IN CURRENT CATALOGUE` |
| Machine Model | `ZX240N-7` |
| Part ID | `PT-012` |
| Part Number | `4391629` |
| Part Name | Battery - Starter, Lighting & Ignition |
| Compatibility | `Model-group level (as printed on the official page)` |
| Data Class | `OFFICIAL WEBSITE DATA` |
| Confidence | `HIGH` |
| **Notes** | **`"Model group 'ZX240N-7' has no matching product detail page in the current EU catalogue (superseded, other-region or intermediate model). Recorded verbatim - NOT expanded or invented."`** |

## Confirmation: `NOT IN CURRENT CATALOGUE` is genuinely a source-authored sentinel, not a machine ID

The row's own `Notes` field states this explicitly and in the source's own words — this isn't an inference. The battery compliance page names `ZX240N-7` as a model group the battery fits, but that model code has no corresponding entry among the 77 rows in `02_MACHINE_MASTER` (checked directly: `ZX240N-7` does not appear as a `Model` or within any `Models Covered` value across all 77 machine records, nor among the 79 distinct model-code strings in `MODEL_CODE_RECONCILIATION.csv`). The source authors recorded this honestly rather than inventing a matching catalogue page or silently dropping the fact — consistent with the same "no silent expansion" / "record verbatim" discipline documented in `00_README` and confirmed in `MODEL_CODE_RECONCILIATION_REPORT.md`.

## Confirmed: no valid machine-part relationship was accidentally removed

The underlying fact — "battery PT-012 (part number 4391629) fits model group ZX240N-7 at model-group level" — is fully preserved in `neo4j/data/machine_part_fitment.csv` (row `FIT-0032` is present, untouched, with `Machine Model: ZX240N-7` still readable). Nothing was deleted from the cleaned CSV. It is excluded only from the **graph relationship import**, because there is no `Machine` node to attach it to.

## Confirmed: no fake machine node should be created

Creating a `Machine` node for `ZX240N-7` to make this one row importable would mean inventing a catalogue/product-page record that HCME's current EU site does not publish — directly contrary to the "do not invent machine models" rule that has governed every phase of this project. The source's own explanation ("superseded, other-region or intermediate model") means this may correspond to a real historical or regional product, but not one this workbook's scope (the current EU catalogue) documents with its own page, specs, or URL — there is nothing to populate a `Machine` node with beyond the bare code string, which is exactly the kind of thin, unverifiable record the model-code investigation already warned against fabricating.

## Confirmed: no relationship should point to the sentinel

`relationships/machine_part_fitment.cypher` explicitly filters out this one row (`WHERE row.\`Machine ID\` <> 'NOT IN CURRENT CATALOGUE'`) before the `MATCH (m:Machine ...)` step — so even if a future data refresh introduced other rows with the same sentinel, they would be excluded the same way, not accidentally matched against some unrelated node.

## Net result

944 rows in `machine_part_fitment.csv` → 943 become `HAS_PART_FITMENT` graph relationships → 1 (`FIT-0032`) is excluded, fully documented, fact preserved in the CSV for any future phase that adds historical/regional machine coverage.
