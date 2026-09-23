# Project: HCME After-Sales Data Foundation (HITACHI_AFTERSALES_NEO4J_CLEAN)

## Architecture
A deterministic data engineering and auditing pipeline that ingests a frozen, read-only 21-sheet Excel workbook (`HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`), audits pre-cleaning data quality, executes domain normalization and referential integrity enforcement, and exports a 17-sheet master Excel workbook (`HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`), 14 relational CSV files in `neo4j/data/`, and 5 audit/quality/cleanup/schema reports.

```
[ Authoritative Source Workbook (Frozen, Read-Only, Touched = 0 bytes) ]
   C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx
                                │
                                ▼
                   [ audit_workbook.py (CLI) ]
                                │
                                ├─► neo4j/reports/workbook_audit.md
                                │
                                ▼
                 [ export_clean_data.py (CLI) ]
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
[ HITACHI_AFTERSALES_     [ 14 Relational CSVs ]   [ Comprehensive Reports ]
  NEO4J_CLEAN.xlsx ]         neo4j/data/              - neo4j/reports/data_quality_report.md
  (17 worksheets:            - categories.csv         - neo4j/CLEANUP_REPORT.md
   00_README to              - machines.csv           - neo4j/reports/schema_candidates.md
   16_REVIEW_REQUIRED)       - specifications.csv     - reports/fitment_conflicts.csv
                             - applications.csv       - reports/service_relationship_conflicts.csv
                             - attachments.csv
                             - parts.csv
                             - machine_part_fitment.csv
                             - services.csv
                             - machine_service.csv
                             - maintenance.csv
                             - service_part_requirements.csv
                             - digital_services.csv
                             - relationships.csv
                             - provenance.csv
                                │
                                ▼
               [ Strict Neo4j Isolation Guardrail ]
          (Zero Aura calls, Zero sockets, Static on Disk)
```

## Feature Inventory
Every feature from the Survey phase is enumerated here with its assigned milestone. No feature is unassigned.

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 21-Sheet Audit Scanner | Non-destructive audit of all 21 raw workbook sheets capturing dimensions, headers, fill rates, types | M1 | ORIGINAL_REQUEST R1 |
| 2 | Source Immutability Verifier | Computes SHA-256 hash and st_mtime before reading; asserts identical hash immediately after closing | M1 | ORIGINAL_REQUEST R1, R5 |
| 3 | Duplicate ID & Row Detector | Analyzes candidate primary keys and full rows for duplicate occurrences per sheet | M1 | ORIGINAL_REQUEST R1, R4 |
| 4 | URL & Noise Flagging Engine | Identifies regex matches for URLs and UI e-commerce ranking fields in raw sheets | M1 | ORIGINAL_REQUEST R1, R2 |
| 5 | Category Hierarchy Tree Builder | Builds acyclic parent-child tree ((:Category)-[:CHILD_OF]->(:Category)) with clean title casing | M2 | ORIGINAL_REQUEST R2 |
| 6 | Machine Master Disambiguator | Preserves catalogue page records (MC-001) vs covered model codes (models_covered, model_count) | M2 | ORIGINAL_REQUEST R2 |
| 7 | Specification Technical Filter | Extracts genuine engineering specs (weight, power, capacity, digging force); strips e-commerce ranking | M2 | ORIGINAL_REQUEST R2 |
| 8 | Sentinel Value Sanitizer | Converts sentinel strings ("NOT PUBLICLY STATED", "N/A", "-") to empty strings; preserves nulls | M2 | ORIGINAL_REQUEST R2, R5 |
| 9 | Application Canonicalizer | Normalizes application names into canonical title case (Demolition, Quarry & Mining, Forestry) | M2 | ORIGINAL_REQUEST R2 |
| 10 | Attachment Hygiene Filter | Cleans OEM attachments retaining name, type, application, compatibility; strips URLs and clutter | M2 | ORIGINAL_REQUEST R2 |
| 11 | Part Record Class Segregator | Strictly segregates parts into ORDERABLE_OEM_PART (published numbers) vs PRODUCT_LINE_PART_FAMILY | M2 | ORIGINAL_REQUEST R2 |
| 12 | Controlled Fitment Classifier | Normalizes fitment evidence to controlled vocabulary (EXACT_MODEL, MODEL_RANGE, CATEGORY, DERIVED, NOT_STATED) | M3 | ORIGINAL_REQUEST R2 |
| 13 | Fitment Conflict Isolator | Identifies contradictory fitment claims and routes offending records to conflict CSV and review sheet | M3 | ORIGINAL_REQUEST R2, R4 |
| 14 | Service Capability Extractor | Cleans after-sales service offerings, isolating location capabilities (FIELD_SERVICE, DEALER_WORKSHOP, REMOTE) | M3 | ORIGINAL_REQUEST R2 |
| 15 | Machine Service Matrix Mapper | Maps machine-to-service eligibility, retaining applicability evidence and tiers | M3 | ORIGINAL_REQUEST R2 |
| 16 | Maintenance Schedule Cleaner | Standardizes operating hour intervals (50h..2000h) and normalizes maintenance action verbs | M3 | ORIGINAL_REQUEST R2 |
| 17 | Service Part Requirement Linker | Connects maintenance intervals to required replacement parts with normalized quantities and units | M3 | ORIGINAL_REQUEST R2 |
| 18 | Digital Services Normalizer | Extracts telematics capabilities (ConSite, Global e-Service) with compatibility flags | M3 | ORIGINAL_REQUEST R2 |
| 19 | Relationship Classifier | Classifies cross-domain links into 6-value vocabulary (CORE, DUPLICATE, DERIVED, RESEARCH_ONLY, INVALID, UNRESOLVED) | M3 | ORIGINAL_REQUEST R2 |
| 20 | Compact Provenance Isolator | Extracts source_name, evidence_type, and confidence; moves all raw URL strings to provenance store | M3 | ORIGINAL_REQUEST R2, R5 |
| 21 | 16-Sheet Excel Generator | Assembles master cleaned Excel workbook containing sheets 00_README through 16_REVIEW_REQUIRED | M4 | ORIGINAL_REQUEST R3 |
| 22 | 14 Relational CSV Exporter | Exports 14 UTF-8 comma-delimited CSV files with RFC 4180 quoting and LF newlines | M2, M3 | ORIGINAL_REQUEST R3 |
| 23 | Data Quality Report Generator | Compiles source vs clean row counts, dropped record tallies, and fitment distribution metrics | M5 | ORIGINAL_REQUEST R4 |
| 24 | Cleanup Audit Log Generator | Produces exhaustive log of all discarded fields, value normalizations, and quarantined records | M5 | ORIGINAL_REQUEST R4 |
| 25 | Schema Candidates Reviewer | Generates graph schema proposal with node labels, relationship types, and indexing strategies | M5 | ORIGINAL_REQUEST R4 |
| 26 | Foreign Key Graph Validator | Validates 100% referential integrity across all 14 CSV files; asserts 0 dangling keys in CORE edges | M6 | ORIGINAL_REQUEST R5 |
| 27 | Deterministic Sort Enforcer | Applies deterministic multi-column sorting to all exported datasets prior to serialization | M2, M3, M6 | ORIGINAL_REQUEST R5 |
| 28 | Core URL Leakage Guard | Scans all core technical entity CSV files with regex to verify zero URL strings remain | M6 | ORIGINAL_REQUEST R5 |
| 29 | Determinism Double-Run Gate | Executes export pipeline twice into separate directories; asserts bit-for-bit identical hashes | M6 | ORIGINAL_REQUEST R5 |
| 30 | Neo4j Isolation Guardrail | Verifies zero database drivers are imported and zero socket connections are attempted to Neo4j ports | M1, M6 | ORIGINAL_REQUEST R6 |
| 31 | E2E Opaque-Box Test Harness | Builds 4-tier requirement-driven opaque-box test suite publishing TEST_READY.md | M-TEST | Dual Track Requirement |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| **M-TEST** | E2E Testing Suite Track | Design and implement opaque-box test runner and test cases for Tiers 1-4 (Features 1-30). Publish TEST_READY.md. | None (Parallel Track) | DONE |
| **M1** | Discovery & Pre-Cleaning Source Audit | Implement `audit_workbook.py` CLI; inspect all 21 source sheets; generate `neo4j/reports/workbook_audit.md`; verify source immutability and determinism. | None | IN_PROGRESS |
| **M2** | Core Entity Normalization & CSVs 1-6 | Implement physical entity normalization in `export_clean_data.py`: Categories, Machines, Specifications, Applications, Attachments, Parts -> CSVs 1-6 (`categories.csv` to `parts.csv`). | M1 | PLANNED |
| **M3** | Relational & Service Normalization & CSVs 7-14 | Implement relational normalization in `export_clean_data.py`: Fitment, Services, Machine Service, Maintenance, Service Part Requirements, Digital Services, Relationships, Provenance -> CSVs 7-14. | M2 | PLANNED |
| **M4** | Clean Master Excel Assembly | Implement Excel export generating `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` containing all 17 sheets (`00_README` through `16_REVIEW_REQUIRED`) with openpyxl validation. | M3 | PLANNED |
| **M5** | Reporting Engine & Conflict Logging | Implement report generation in `export_clean_data.py`: `data_quality_report.md`, `CLEANUP_REPORT.md`, `schema_candidates.md`, `fitment_conflicts.csv`, `service_relationship_conflicts.csv`. | M4 | PLANNED |
| **M6** | Final E2E Test Pass, Determinism & Hardening | Phase 1: Verify 100% pass on E2E Test Suite (Tiers 1-4); Phase 2: Tier 5 adversarial stress hardening with Challengers, double-run byte-identical validation, zero URL leakage, and strict Neo4j isolation audit. | M5, M-TEST | PLANNED |

## Interface Contracts

### CLI: `audit_workbook.py`
- Invocation: `python audit_workbook.py [--input <path>] [--output <path>] [--verify-source]`
- Default `--input`: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`
- Default `--output`: `neo4j/reports/workbook_audit.md`
- Behavior:
  - Opens workbook in read-only, data-only mode (`openpyxl.load_workbook(path, read_only=True, data_only=True)`).
  - Asserts source file modification time and SHA-256 hash are identical before and after execution.
  - Outputs Markdown audit covering all 21 sheets with standardized metrics.
  - Returns exit code 0 on success, non-zero on failure.

### CLI: `export_clean_data.py`
- Invocation: `python export_clean_data.py [--input <path>] [--output-excel <path>] [--output-csv-dir <path>] [--output-reports-dir <path>]`
- Default `--input`: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`
- Default `--output-excel`: `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`
- Default `--output-csv-dir`: `neo4j/data`
- Default `--output-reports-dir`: `neo4j/reports`
- Behavior:
  - Generates `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` with 17 sheets.
  - Generates 14 CSV files in `neo4j/data/` with UTF-8 encoding, comma delimiters, and LF newlines.
  - Generates `data_quality_report.md`, `CLEANUP_REPORT.md`, `schema_candidates.md`.
  - Generates `reports/fitment_conflicts.csv` and `reports/service_relationship_conflicts.csv`.
  - Deterministic sort on primary and foreign keys.

### CSV Data Contracts (`neo4j/data/`)
- Header row matching lowercase snake_case column names.
- UTF-8 encoding, comma `,` separator, double-quote `"` quoting.
- Empty values serialized as `""` (no NaN, None, or sentinel strings).
- Zero URL strings in core entity CSVs.

## Code Layout
```
c:\Users\iamdn\OneDrive\Desktop\Parts&Service\
├── audit_workbook.py               # Pre-cleaning 21-sheet audit CLI script
├── export_clean_data.py            # Clean dataset transformation and export pipeline
├── HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx # Generated master clean workbook (17 sheets)
├── neo4j/
│   ├── data/                       # 14 normalized relational CSV files
│   │   ├── categories.csv
│   │   ├── machines.csv
│   │   ├── specifications.csv
│   │   ├── applications.csv
│   │   ├── attachments.csv
│   │   ├── parts.csv
│   │   ├── machine_part_fitment.csv
│   │   ├── services.csv
│   │   ├── machine_service.csv
│   │   ├── maintenance.csv
│   │   ├── service_part_requirements.csv
│   │   ├── digital_services.csv
│   │   ├── relationships.csv
│   │   └── provenance.csv
│   ├── reports/                    # Generated audit and schema reports
│   │   ├── workbook_audit.md
│   │   ├── data_quality_report.md
│   │   └── schema_candidates.md
│   └── CLEANUP_REPORT.md           # Exhaustive transformation and removal log
├── reports/                        # Conflict registers
│   ├── fitment_conflicts.csv
│   └── service_relationship_conflicts.csv
├── tests/
│   ├── test_e2e_harness.py         # Opaque-box E2E test runner (Tiers 1-4)
│   └── verify_pipeline_integrity.py# Integrity and determinism verification script
├── TEST_INFRA.md                   # Test architecture and tier coverage matrix
├── TEST_READY.md                   # Signal that E2E test suite is published and ready
├── PROJECT.md                      # Authoritative project architecture and milestones
└── ORIGINAL_REQUEST.md             # Immutable user request record
```
