# Fitment Import Count Reconciliation

## 1. Summary of Reconciliation
- **Total rows in source workbook (07_MACHINE_PART_FITMENT)**: 944 data rows.
- **Total rows in clean workbook (HITACHI_AFTERSALES_NEO4L_CLEAN.xlsx - 07_MACHINE_PART_FITMENT)**: 944 data rows.
- **Total rows in current clean CSV (neo4j/data/machine_part_fitment.csv)**: 944 data rows (Fitment IDs FIT-0001 to FIT-0944).
- **Total valid graph relationships to create in Neo4j**: **943**
- **Excluded sentinel rows**: **1** (FIT-0032, ZX240N-7, Machine ID NOT IN CURRENT CATALOGUE):).

## 2. Origin of the 1607 Discrepancy
The number 1,607 reported in the previous assistant message was an assistant typographical error in the summary table.
The actual file neo4j/data/machine_part_fitment.csv on disk has mtime 2026-09-17 13:18:08, SHA-256 82d09f7d16ff5dc7b2de2a58f01b21702c9bb5e9633f85d2cfeab1b196641d48, and contains exactly 944 data rows.

## 3. Fitment Evidence Breakdown
- CATEGORY: 826 rows (category-level product line association)
- EXACT_MODEL: 118 rows (published OEM battery compliance exact model fitments)
- Total: 944 rows

## 4. The Excluded Sentinel Record (FIT-0032)
- FIT-0032 has Machine ID NOT IN CURRENT CATALOGUE for model ZX240N-7.
- It is preserved in the CSV but excluded from the graph edges via WHERE machine_id <> 'NOT IN CURRENT CATALOGUE'.
- Resulting graph relationships: exactly 943.
