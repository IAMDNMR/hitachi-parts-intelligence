# Cleanup Report

## 01_CATEGORIES
Dropped Official URL and Notes. Kept 12 of 14 source columns. 0 exact-duplicate rows merged.

## 02_MACHINES
Dropped Official Product URL and Brochure PDF (URLs). Preserved Model / Models Covered / Model Count exactly as published — a catalogue-page Machine ID is not silently split into one row per model code.

## 03_SPECIFICATIONS
Dropped Official URL. 0 rows had "NOT PUBLICLY STATED" as their Specification Value; that text is nulled (never converted to a fake number) and the fact it was explicitly unpublished is preserved in the value_stated column instead of being lost.

## 04_APPLICATIONS
Dropped Source URL. 0 values recast to a canonical case form (distinct application names were never merged). 0 exact machine+application duplicates merged.

## 05_ATTACHMENTS
Dropped Official URL. No Weight/Dimensions/Capacity values were invented for rows where the source leaves them blank.

## 06_PARTS
Dropped Source URL. 20 of 43 parts carry a real published part number (record_class=ORDERABLE_OEM_PART); the rest are named product lines with no part number (record_class=PRODUCT_LINE_PART_FAMILY) — none was assigned a manufactured SKU.

## 07_MACHINE_PART_FITMENT
Dropped Official URL. Compatibility free text normalized to a controlled evidence vocabulary (EXACT_MODEL/MODEL_RANGE/CATEGORY/NOT_STATED); original free text kept in evidence_original. 0 identical-evidence duplicate pairs merged. 0 machine+part pairs had genuinely conflicting evidence and are logged in fitment_conflicts.csv rather than silently resolved.

## 08_SERVICES
Dropped Source URL. Customer Site / Dealer Workshop / Other Location kept as capability flags on the service record, not split into separate location entities.

## 09_MACHINE_SERVICE
Applicability free text normalized to ALL_MACHINES_STATED/CATEGORY/NOT_STATED (original kept in applicability_original — none of these rows literally state a single exact-model-only applicability, so EXACT/MODEL_RANGE were not asserted where the source never states them). 0 duplicates merged, 0 conflicts logged.

## 10_MAINTENANCE
Dropped Source URL. Only the 4 genuinely published interval figures carry a real value; everything else stays as the source states it (typically blank/NOT PUBLICLY STATED).

## 11_SERVICE_PART_REQUIREMENTS
Dropped Source URL. No quantity or part number was invented for the rows the source leaves blank.

## 12_DIGITAL_SERVICES
Dropped URL. The Fleet-management/Service page scope conflict noted in the source (mini excavators included or not) is preserved via the Applicability + Stated Applicability fields rather than silently picking a side.

## 13_RELATIONSHIPS
Dropped Source URL. Every row classified by relationship_class: {'CORE': 169, 'DERIVED': 3097, 'INVALID': 17}. Only CORE and DERIVED rows should be treated as graph-ready; DUPLICATE/INVALID/UNRESOLVED are kept in the sheet but flagged, not silently dropped.

## 14_PROVENANCE
Dropped the raw URL column from the graph-ready provenance table — the full source register with URLs remains available in the untouched original workbook for audit if ever needed.

## 15_DATA_QUALITY
Passed through unchanged apart from whitespace/blank normalization — this source sheet is itself a quality/conflict log, not raw entity data.

## Recommended graph entities
Category, Machine, Specification, Application, Part, Attachment, Service, DigitalService — see schema_candidates.md for the evidence behind each.

## Remaining data-quality concerns
- 0 fitment conflicts logged for human review (fitment_conflicts.csv).
- 0 machine-service applicability conflicts logged for review.
- 0 dangling foreign keys found — see data_quality_report.md.