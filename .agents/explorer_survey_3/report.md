# Pipeline Architecture, Determinism & Integrity Verification Report
**Agent**: explorer_survey_3 (Pipeline & Integrity Explorer)  
**Target Repository**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service`  
**Date**: 2026-09-17  
**Status**: COMPLETE  

---

## 1. Executive Summary & Problem Boundary

The HCME After-Sales Data Foundation project requires processing an authoritative 21-sheet Excel source workbook (`C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`, ~796 KB) into a fully normalized, graph-ready dataset comprising:
1. A cleaned 16-sheet Excel workbook (`HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`).
2. Exactly 14 normalized CSV files in `neo4j/data/`.
3. Four comprehensive markdown audit and quality reports in `neo4j/` and `neo4j/reports/`.
4. Dedicated conflict resolution CSVs in `reports/`.

### Critical Operating Constraints
- **Source Immutability**: The source workbook must remain completely untouched (verified by pre/post SHA-256 hash and OS timestamp checks).
- **Strict Neo4j Isolation Guardrail**: Under NO circumstances connect to Neo4j, call Neo4j Aura, or execute Cypher DDL/DML. The pipeline strictly ends with verified file artifacts on disk.
- **Byte-for-Byte Determinism**: Successive runs of `audit_workbook.py` and `export_clean_data.py` on the same input must produce bit-for-bit identical outputs.
- **Zero Referential Integrity Defects**: Zero dangling foreign keys across all core entities and relationships.

---

## 2. Architecture & Execution Requirements for `audit_workbook.py`

### 2.1 CLI Interface & Arguments Specification
The audit script is the initial inspection and discovery instrument. It must be non-destructive, robust, and capable of automated execution.

```bash
python audit_workbook.py [OPTIONS]
```

#### Argument Catalog
| Parameter | Type | Default | Description |
|---|---|---|---|
| `--input`, `-i` | `Path` | `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` | Path to the raw source workbook. Must exist. |
| `--output`, `-o` | `Path` | `neo4j/reports/workbook_audit.md` | Destination path for the markdown audit report. Parent dirs created automatically. |
| `--json-out` | `Path` | `None` (Optional) | Optional structured JSON output of all raw audit metrics for programmatic assertions. |
| `--verify-source` | `bool` | `True` | Calculate SHA-256 hash and `st_mtime` before reading, re-verify immediately after closing. |
| `--strict` | `bool` | `False` | When set, exits with code 1 if critical data corruption or missing sheets are detected. |
| `--quiet`, `-q` | `bool` | `False` | Suppress console stdout, logging errors only. |

#### Process Exit Codes
- `0`: Success — All 21 sheets parsed, metrics collected, source immutability verified, report generated.
- `1`: Validation Failure — Critical anomaly threshold exceeded under `--strict`.
- `2`: Source Missing / Unreadable — Input workbook not found, unreadable, or invalid zip archive.
- `3`: Immutability Violation — Source file hash or modification timestamp changed during run.

#### Immutability & Memory Safety Architecture
```python
# Deterministic & safe workbook loading pattern
import hashlib, os, openpyxl

def read_source_safely(path: str):
    # 1. Capture pre-read baseline
    stat_before = os.stat(path)
    with open(path, 'rb') as f:
        sha_before = hashlib.sha256(f.read()).hexdigest()
        
    # 2. Read-only openpyxl loading
    # read_only=True uses lazy streaming (minimal RAM)
    # data_only=True evaluates cached values, prevents formula recalculation
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    
    # 3. Post-read verification
    stat_after = os.stat(path)
    with open(path, 'rb') as f:
        sha_after = hashlib.sha256(f.read()).hexdigest()
        
    if sha_before != sha_after or stat_before.st_mtime != stat_after.st_mtime:
        raise SecurityError("CRITICAL: Source workbook modified during read!")
        
    return wb, sha_before
```

---

### 2.2 Metric Extraction Requirements for `neo4j/reports/workbook_audit.md`

The audit report must evaluate all **21 source sheets** systematically. For each sheet, the following exact metrics must be extracted and tabulated:

1. **Sheet Identity & Dimensions**:
   - Sheet Index (1..21) and exact Sheet Name.
   - Raw Row Count (including empty rows) vs. Active Data Row Count (excluding trailing blanks).
   - Raw Column Count vs. Named Column Count (header row populated).
2. **Column-by-Column Catalog**:
   - Column Index and Excel Column Letter (`A`, `B`, `C`...).
   - Column Header (exact verbatim string, noting leading/trailing spaces).
   - Inferred Python Data Types across all cells (`str`, `int`, `float`, `bool`, `datetime`, `NoneType`).
   - Non-empty Cell Count vs. Empty / Null Count.
   - Fill Rate (`(non_empty_count / total_data_rows) * 100` formatted to 2 decimal places).
   - Cardinality (count of distinct non-null values).
3. **Primary Key & Duplicate Analysis**:
   - Candidate Primary Key column(s).
   - Uniqueness test (count of distinct values vs row count).
   - Duplicate ID Count and sample offending duplicate keys.
   - Full-Row Duplicate Count (where every single cell matches another row).
4. **Data Quality & Hygiene Flags**:
   - **URL Leakage Count**: Cells matching regex `https?://` or `www\.` or `.hitachicm.com`.
   - **E-Commerce / UI Noise**: Presence of ranking, click metrics, price fields, visual order.
   - **Sentinel Values**: Presence and count of `"NOT PUBLICLY STATED"`, `"N/A"`, `"NA"`, `"-"`, `"TBD"`, `"UNKNOWN"`.
   - **Whitespace / Encoding Defects**: Non-breaking spaces (`\u00a0`), carriage returns (`\r`), multi-space sequences, leading/trailing whitespace.
5. **Graph Utility Classification**:
   Every column must be mapped into one of 5 distinct categories:
   - `TECHNICAL_ENTITY_ATTRIBUTE`: Retain as core node property (e.g. `operating_weight_kg`, `engine_power_kw`).
   - `GRAPH_RELATIONSHIP_POINTER`: Retain as edge pointer (e.g. `machine_id`, `category_id`, `part_id`).
   - `PROVENANCE_METADATA`: Isolate to provenance store (e.g. `source_url`, `extracted_date`, `confidence`).
   - `CONTROLLED_VOCAB_FIELD`: Requires vocabulary mapping (e.g. `fitment_evidence`, `record_class`).
   - `NOISE_TO_REMOVE`: Strip completely (e.g. UI ranking, search tags, shopping cart indicators).

---

### 2.3 Determinism Protocol for `audit_workbook.py`
To achieve 100% byte-for-byte reproducibility:
1. **Zero Dynamic Timestamps**: Do NOT output `datetime.now()` or execution durations in the generated markdown. Instead, include the static cryptographic hash:
   ```markdown
   **Source File SHA256**: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
   **Tool Version**: `audit_workbook.py v1.0.0 (HCME Data Foundation Pipeline)`
   ```
2. **Stable Sheet & Column Ordering**: Sheets are strictly traversed in Excel tab order (index 0 to 20). Columns are traversed from left to right (col 1 to max_col).
3. **Deterministic Set Formatting**: Whenever listing duplicate IDs or detected types, always sort:
   `", ".join(sorted(str(x) for x in list_of_items))`.
4. **Fixed Float Precision**: All percentages must be formatted explicitly with `f"{rate:.2f}%"`.
5. **Normalized Line Endings & Encoding**: Always open output files with `encoding='utf-8', newline='\n'`.

---

## 3. Architecture & Execution Requirements for `export_clean_data.py`

### 3.1 Modular Pipeline Architecture
`export_clean_data.py` must execute as a deterministic multi-stage transformation pipeline:

```
[Raw Workbook (Read-Only)]
            │
            ▼
   ┌─────────────────┐
   │ 1. Extraction   │ ◄── Stream sheets into typed staging records
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ 2. Normalization│ ◄── Clean whitespace, map controlled vocabs, strip noise
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ 3. Disambiguate │ ◄── Segregate ORDERABLE_OEM_PART vs PRODUCT_LINE_PART_FAMILY
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ 4. Validation   │ ◄── FK graph check, URL leakage scan, conflict extraction
   └────────┬────────┘
            │
     ┌──────┴───────────────────────────┐
     ▼                                  ▼
┌───────────────────────────┐  ┌──────────────────────────────┐
│ 5. Graph CSV Exporter     │  │ 6. Multi-Sheet Excel Exporter│
│ (14 CSVs in neo4j/data/)  │  │ (HITACHI_..._CLEAN.xlsx - 16s│
└───────────────────────────┘  └──────────────────────────────┘
     │                                  │
     └──────────────────┬───────────────┘
                        ▼
       ┌─────────────────────────────────┐
       │ 7. Audit & Conflict Reports     │
       │ (4 reports + 2 conflict CSVs)   │
       └─────────────────────────────────┘
```

---

### 3.2 Target Dataset Specifications

#### A. 14 Machine-Readable CSVs (`neo4j/data/`)
All CSV files must use UTF-8 encoding (no BOM), standard comma delimiter (`,`), RFC 4180 quoting, and `\n` line endings.

| # | CSV File | Primary Key | Foreign Keys / Graph Pointers | Controlled Vocab / Core Invariants |
|---|---|---|---|---|
| 1 | `categories.csv` | `category_id` | `parent_category_id` -> `categories(category_id)` | Hierarchy forms a valid acyclic tree. Clean title casing. |
| 2 | `machines.csv` | `machine_id` | `category_id` -> `categories(category_id)` | Catalogue page records (e.g. `MC-001`). Preserve `models_covered`, `model_count`. No invented models. |
| 3 | `specifications.csv` | `spec_id` / `machine_id` | `machine_id` -> `machines(machine_id)` | Weight, power, bucket capacity, reach. Null for "NOT PUBLICLY STATED". Zero UI ranking. |
| 4 | `applications.csv` | `application_id` | None | Normalized naming: `Demolition`, `Quarry & Mining`, `General Construction`, `Recycling`, `Forestry`. |
| 5 | `attachments.csv` | `attachment_id` | `application_id` -> `applications(application_id)` | Retain id, name, type, application, compatibility level. No manufactured part numbers. |
| 6 | `parts.csv` | `part_id` | `category_id` -> `categories(category_id)` (opt) | Strict `record_class`: `ORDERABLE_OEM_PART` (has part_number) vs `PRODUCT_LINE_PART_FAMILY` (no part_number). |
| 7 | `machine_part_fitment.csv` | `fitment_id` | `machine_id` -> `machines(machine_id)`<br>`part_id` -> `parts(part_id)` | `fitment_evidence` IN (`EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`). |
| 8 | `services.csv` | `service_id` | None | `service_name`, `service_category`, `location_type`. URLs and marketing clutter stripped. |
| 9 | `machine_service.csv` | `mapping_id` | `machine_id` -> `machines(machine_id)`<br>`service_id` -> `services(service_id)` | Applicability evidence retained. Conflicts routed to conflict log. |
| 10 | `maintenance.csv` | `maintenance_id` | `machine_id` -> `machines(machine_id)` | Maintenance intervals (hours), actions (inspect/replace). |
| 11 | `service_part_requirements.csv` | `requirement_id`| `maintenance_id` -> `maintenance(maintenance_id)`<br>`part_id` -> `parts(part_id)` | Connects maintenance actions to replacement filters, lubricants, gaskets. |
| 12 | `digital_services.csv` | `digital_service_id` | `machine_id` -> `machines(machine_id)` | ConSite, Global e-Service, telematics capabilities. |
| 13 | `relationships.csv` | `rel_id` | `source_id` -> Any Core Entity<br>`target_id` -> Any Core Entity | `classification` IN (`CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`). `CORE` has 0 dangling FKs. |
| 14 | `provenance.csv` | `provenance_id` | `entity_id` -> Core Entity or Rel ID | Isolated provenance store: `source_name`, `evidence_type`, `confidence` (`CONFIRMED`, `PROBABLE`, `DERIVED`). |

#### B. Clean Excel Workbook (`HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`)
Must contain exactly 16 sheets in this fixed order:
1. `00_README`: Version metadata, data dictionary, sheet index, schema invariants.
2. `01_CATEGORIES`: Clean machine category taxonomy and hierarchy.
3. `02_MACHINES`: Clean machine master records.
4. `03_SPECIFICATIONS`: Technical machine specifications without UI rankings.
5. `04_APPLICATIONS`: Industry applications.
6. `05_ATTACHMENTS`: Clean attachments and implements.
7. `06_PARTS`: Segregated parts (orderable parts vs product-line part families).
8. `07_MACHINE_PART_FITMENT`: Normalized fitment matrix with controlled evidence tags.
9. `08_SERVICES`: Dealer and OEM service capabilities.
10. `09_MACHINE_SERVICE`: Machine-to-service mapping matrix.
11. `10_MAINTENANCE`: Maintenance intervals and action schedule.
12. `11_SERVICE_PART_REQUIREMENTS`: Consumable and replacement part requirements per service.
13. `12_DIGITAL_SERVICES`: Telematics and connected fleet services.
14. `13_RELATIONSHIPS`: Graph relationship catalog with classification tags.
15. `14_PROVENANCE`: Compact provenance metadata isolated from graph nodes.
16. `15_DATA_QUALITY`: Audit KPIs, transformation metrics, before/after counts.
17. `16_REVIEW_REQUIRED`: Unresolved conflicts, ambiguous fitments, review items.

---

### 3.3 Deterministic Export Guarantees

To ensure that running `export_clean_data.py` multiple times produces byte-identical results:

1. **Deterministic Multi-Column Sort Order**:
   Every dataset must be sorted deterministically prior to export. Never rely on SQL query order or set/dict iteration.
   - `categories.csv`: `ORDER BY category_id ASC`
   - `machines.csv`: `ORDER BY machine_id ASC`
   - `specifications.csv`: `ORDER BY machine_id ASC, spec_id ASC`
   - `applications.csv`: `ORDER BY application_id ASC`
   - `attachments.csv`: `ORDER BY attachment_id ASC`
   - `parts.csv`: `ORDER BY record_class DESC, part_id ASC` (Groups `ORDERABLE_OEM_PART` first, then `PRODUCT_LINE_PART_FAMILY`)
   - `machine_part_fitment.csv`: `ORDER BY machine_id ASC, part_id ASC, fitment_evidence ASC`
   - `services.csv`: `ORDER BY service_id ASC`
   - `machine_service.csv`: `ORDER BY machine_id ASC, service_id ASC`
   - `maintenance.csv`: `ORDER BY machine_id ASC, interval_hours ASC, maintenance_id ASC`
   - `service_part_requirements.csv`: `ORDER BY maintenance_id ASC, part_id ASC`
   - `digital_services.csv`: `ORDER BY machine_id ASC, digital_service_id ASC`
   - `relationships.csv`: `ORDER BY classification ASC, source_id ASC, relationship_type ASC, target_id ASC`
   - `provenance.csv`: `ORDER BY entity_id ASC, provenance_id ASC`

2. **Standardized Value Representations**:
   - **Dates**: Strict ISO-8601 string format `YYYY-MM-DD` (e.g. `2026-09-17`).
   - **Floats & Integers**:
     - Weights, power, capacities: Integer if whole number (`int(val)`), or formatted float `f"{val:.2f}"` (or `f"{val:g}"` for exact specifications).
     - Never allow floating point representation artifacts like `45.00000000000001`.
   - **Null / Missing Values**:
     - In CSV: Empty string `""`. Never output `"NaN"`, `"null"`, `"None"`, or `"#N/A"`.
     - In Excel: Native Python `None` (empty cell).
     - In technical specifications: Sentinel `"NOT PUBLICLY STATED"` converted strictly to `""` / `None`.
   - **Text Sanitization**:
     - Strip leading and trailing whitespace (`.strip()`).
     - Convert all non-breaking spaces `\u00a0` to standard ASCII space `' '`.
     - Collapse multiple consecutive spaces to a single space.
     - Eliminate unescaped newline characters inside cell strings (replace internal newlines with space or ` \n `).

3. **Openpyxl Excel Determinism**:
   - Excel workbooks generated by `openpyxl` can have non-deterministic zip file timestamps if not controlled.
   - To guarantee byte-level reproducibility in `.xlsx` files:
     - Apply fixed metadata (Author: "HCME Data Foundation Pipeline", Created: fixed baseline date).
     - Avoid volatile auto-formatting or dynamic conditional formats.
     - Alternatively, sort and fix ZIP entry timestamps when serializing the `.xlsx` zip container if strict byte-for-byte `.xlsx` hashing is required.

---

### 3.4 Report Generation Architecture

`export_clean_data.py` must automatically produce five audit/reporting artifacts:

1. **`neo4j/reports/data_quality_report.md`**:
   - Tabulation of Source vs Clean row counts for all entities.
   - Dropped and deduplicated row counts with specific rationales.
   - Fitment evidence distribution breakdown (`EXACT_MODEL`: X, `MODEL_RANGE`: Y, etc.).
   - Foreign key integrity verification report proving 0 dangling edges in core graphs.
2. **`neo4j/CLEANUP_REPORT.md`**:
   - Exhaustive audit trail of all discarded columns (URLs, UI importance rankings, search metadata).
   - Value normalization mappings (e.g., how application names and category labels were canonicalized).
   - Part classification breakdown (justification for which items became `ORDERABLE_OEM_PART` vs `PRODUCT_LINE_PART_FAMILY`).
   - Provenance isolation summary.
3. **`neo4j/reports/schema_candidates.md`**:
   - Formal graph schema proposal for downstream Neo4j modeling.
   - Recommended Node Labels: `(:Category)`, `(:Machine)`, `(:Specification)`, `(:Application)`, `(:Attachment)`, `(:Part)`, `(:Service)`, `(:MaintenanceSchedule)`, `(:DigitalService)`.
   - Recommended Edge Relationships: `(:Category)-[:CHILD_OF]->(:Category)`, `(:Machine)-[:BELONGS_TO]->(:Category)`, `(:Part)-[:FITS_ON]->(:Machine)`, `(:Machine)-[:REQUIRES_MAINTENANCE]->(:MaintenanceSchedule)`, etc.
   - Concrete property graphs and index/constraint recommendations for future use.
4. **`reports/fitment_conflicts.csv`**:
   - Generated whenever contradictory fitment evidence exists (e.g., machine listed as compatible and incompatible, or conflicting levels).
   - Columns: `conflict_id`, `machine_id`, `part_id`, `claim_1`, `claim_2`, `resolution_status ('REVIEW_REQUIRED')`.
5. **`reports/service_relationship_conflicts.csv`**:
   - Documents conflicting service-to-machine capabilities or unresolvable service links.

---

## 4. Referential Integrity, Controlled Vocabulary & Validation Matrix

### 4.1 Referential Integrity Graph (14 CSVs)

```
                       ┌──────────────┐
                       │  categories  │◄─────┐
                       └──────┬───────┘      │ parent_category_id
                              │              │
                              │ category_id  │
                              ▼              │
                       ┌──────────────┐      │
             ┌─────────┤   machines   ├──────┘
             │         └──────┬───────┘
             │                │
             │ machine_id     │ machine_id
             ▼                ▼
     ┌───────────────┐ ┌───────────────┐
     │specifications │ │   fitment     │
     └───────────────┘ └──────┬────────┘
                              │ part_id
                              ▼
                       ┌───────────────┐
                       │     parts     │
                       └──────▲────────┘
                              │ part_id
                       ┌──────┴────────┐
                       │service_part_  │
                       │ requirements  │
                       └──────▲────────┘
                              │ maintenance_id
                              ▼
                       ┌───────────────┐
                       │  maintenance  │
                       └──────▲────────┘
                              │ machine_id
                       ┌──────┴────────┐
                       │machine_service│
                       └──────┬────────┘
                              │ service_id
                              ▼
                       ┌───────────────┐
                       │   services    │
                       └───────────────┘
```

#### Detailed Foreign Key Verification Rules
1. **Category Hierarchy**: Every `parent_category_id` in `categories.csv` must exist in `categories.csv(category_id)`, with `NULL` permitted only for root categories (e.g. `Excavators`, `Wheel Loaders`). The graph must be verified acyclic.
2. **Machine -> Category**: Every `category_id` in `machines.csv` must resolve to `categories.csv(category_id)`.
3. **Specification -> Machine**: Every `machine_id` in `specifications.csv` must resolve to `machines.csv(machine_id)`.
4. **Machine Part Fitment**:
   - `machine_id` must resolve to `machines.csv(machine_id)`.
   - `part_id` must resolve to `parts.csv(part_id)`.
5. **Machine Service**:
   - `machine_id` must resolve to `machines.csv(machine_id)`.
   - `service_id` must resolve to `services.csv(service_id)`.
6. **Maintenance -> Machine**: Every `machine_id` in `maintenance.csv` must resolve to `machines.csv(machine_id)`.
7. **Service Part Requirements**:
   - `maintenance_id` must resolve to `maintenance.csv(maintenance_id)`.
   - `part_id` must resolve to `parts.csv(part_id)`.
8. **Digital Services -> Machine**: Every `machine_id` in `digital_services.csv` must resolve to `machines.csv(machine_id)`.
9. **Relationships Matrix**:
   - For all records with `classification == 'CORE'`:
     - `source_id` must resolve to an existing ID in the table corresponding to `source_type`.
     - `target_id` must resolve to an existing ID in the table corresponding to `target_type`.
   - Dangling references in `CORE` relationships: **STRICTLY ZERO**.

---

### 4.2 Controlled Vocabulary & Classification Enums

| Domain | Attribute | Permitted Controlled Vocabulary | Validation Enforcement Rule |
|---|---|---|---|
| Parts | `record_class` | `ORDERABLE_OEM_PART`, `PRODUCT_LINE_PART_FAMILY` | If `ORDERABLE_OEM_PART`, `part_number` MUST NOT be null/empty. If `PRODUCT_LINE_PART_FAMILY`, `part_number` MUST be null. No fake SKUs. |
| Fitment | `fitment_evidence` | `EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED` | Any other string rejected. Contradictions logged to `reports/fitment_conflicts.csv`. |
| Relationships | `classification` | `CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED` | `CORE` edges must satisfy 100% referential integrity. Others isolated from primary graph export. |
| Provenance | `confidence` | `CONFIRMED`, `PROBABLE`, `DERIVED`, `RESEARCH_ONLY`, `UNSURE` | Maps source uncertainty without discarding origin data. |

---

### 4.3 URL Leakage Detection Engine

A strict acceptance criterion is that zero URLs may exist in core technical entity CSV files.

#### Scope of URL Isolation
- **Forbidden from having ANY URLs**:
  `categories.csv`, `machines.csv`, `specifications.csv`, `applications.csv`, `attachments.csv`, `parts.csv`, `services.csv`, `machine_service.csv`, `maintenance.csv`, `service_part_requirements.csv`, `digital_services.csv`.
- **Permitted to contain URLs**:
  Only `provenance.csv` (or isolated provenance columns in non-core sheets).

#### Validation Regex & Inspection Logic
```python
import re

URL_PATTERN = re.compile(
    r'(https?://[^\s,]+|www\.[^\s,]+|[a-zA-Z0-9.-]+\.(?:com|eu|org|net|de|co\.uk)(?:/[^\s,]*)?)',
    re.IGNORECASE
)

def assert_zero_url_leakage(csv_path: str):
    with open(csv_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            matches = URL_PATTERN.findall(line)
            if matches:
                raise AssertionError(
                    f"URL Leakage detected in {csv_path} at line {line_num}: {matches}"
                )
```

---

### 4.4 Openpyxl Validation for `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`

The generated Excel workbook must undergo strict structural validation before being approved:
1. **Clean Load Test**: Must open cleanly via `openpyxl.load_workbook(path, data_only=True)` with zero warnings or errors.
2. **Sheet Count & Names**:
   `assert len(wb.sheetnames) == 16`
   Sheet names must match the exact sequence:
   `['00_README', '01_CATEGORIES', '02_MACHINES', '03_SPECIFICATIONS', '04_APPLICATIONS', '05_ATTACHMENTS', '06_PARTS', '07_MACHINE_PART_FITMENT', '08_SERVICES', '09_MACHINE_SERVICE', '10_MAINTENANCE', '11_SERVICE_PART_REQUIREMENTS', '12_DIGITAL_SERVICES', '13_RELATIONSHIPS', '14_PROVENANCE', '15_DATA_QUALITY', '16_REVIEW_REQUIRED']`.
3. **Data Integrity**:
   - Every sheet (except possibly `16_REVIEW_REQUIRED`) must have a header row and at least 1 data row.
   - Header cells must be non-empty strings.
   - Cell types must be strictly valid Excel primitives: `str`, `int`, `float`, `bool`, `datetime`, or `None`.
   - Zero formula errors (e.g. `#VALUE!`, `#REF!`, `#NAME?`, `#N/A`).

---

## 5. Proposed Verification Harness & Milestone Strategy

### 5.1 Comprehensive Verification Test Suite Design

We propose an automated Python verification harness script (`tests/verify_pipeline_integrity.py`) structured into 5 hierarchical test tiers:

```
┌────────────────────────────────────────────────────────┐
│ Tier 1: Static Artifact & Schema Conformance           │
│ - Check existence of 16-sheet Excel, 14 CSVs, 4 reports│
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│ Tier 2: Source File Immutability Gate                  │
│ - Verify SHA-256 and mtime of source before vs after   │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│ Tier 3: 100% Deterministic Reproducibility Gate        │
│ - Execute run 1 -> dir A, run 2 -> dir B               │
│ - Assert SHA-256(file_A) == SHA-256(file_B) for all    │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│ Tier 4: Referential Integrity & Vocabulary Gate        │
│ - Load 14 CSVs into memory                             │
│ - Assert 0 duplicate PKs, 0 dangling FKs in CORE rels  │
│ - Validate controlled vocabulary enums                 │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│ Tier 5: Data Quality & Adversarial Security Gate       │
│ - URL leakage scan across core CSV columns             │
│ - openpyxl clean load and cell type validation         │
│ - Neo4j strict isolation assert (0 socket connections) │
└────────────────────────────────────────────────────────┘
```

#### Test Runner Specification
```bash
# Verification command
pytest tests/test_pipeline_integrity.py -v
```

---

### 5.2 Phased Milestone Road Map for Orchestrator

| Milestone | Objective | Key Deliverables / Tasks | Verification Gate |
|---|---|---|---|
| **M0: Setup & Baseline Guardrails** | Initialize environment and freeze baseline | Record source workbook SHA-256; configure test runners; verify Neo4j isolation guardrails. | Source hash baseline recorded; no DB connections configured. |
| **M1: Pre-Cleaning Audit** | Inspect 21 source sheets non-destructively | Implement `audit_workbook.py`; execute audit; generate `neo4j/reports/workbook_audit.md`. | Source hash unchanged; all 21 sheets documented with exact metrics. |
| **M2: Core Entity Normalization** | Extract & normalize physical entity records | Implement extraction for Categories, Machines, Specifications, Applications, Attachments, Parts; separate Orderable Parts from Part Families. | `categories.csv`, `machines.csv`, `specifications.csv`, `applications.csv`, `attachments.csv`, `parts.csv` generated. 0 duplicate PKs. |
| **M3: Relationship & Matrix Normalization** | Extract & normalize graph edges and matrices | Implement extraction for Fitment, Services, Machine-Service, Maintenance, Digital Services, Relationships, Provenance; classify relationships. | `machine_part_fitment.csv`, `services.csv`, `machine_service.csv`, `maintenance.csv`, `digital_services.csv`, `relationships.csv`, `provenance.csv` generated. 0 dangling FKs in CORE. |
| **M4: Clean Excel Workbook Assembly** | Build 16-sheet master Excel foundation | Assemble `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` with sheets `00_README` through `16_REVIEW_REQUIRED`. | Openpyxl loads cleanly; exactly 16 sheets in specified order. |
| **M5: Comprehensive Reporting Engine** | Generate final audit and conflict artifacts | Generate `data_quality_report.md`, `CLEANUP_REPORT.md`, `schema_candidates.md`, `fitment_conflicts.csv`, `service_relationship_conflicts.csv`. | All reports populated with concrete metrics and justifications. |
| **M6: E2E Verification & Determinism Gate** | Final automated verification & sign-off | Run Tiers 1-5 verification harness; execute determinism double-run byte-check. | 100% tests pass; byte-identical outputs; source immutability certified. |

---

## 6. Strict Neo4j Isolation Guardrail Plan

To uphold the explicit requirement that no connection to Neo4j or Neo4j Aura occurs:
1. **Zero Database Client Drivers**: The pipeline scripts (`audit_workbook.py`, `export_clean_data.py`) must NOT import `neo4j` or `py2neo`. The only dependencies permitted are `openpyxl`, `pandas` (or standard `csv`), `hashlib`, `re`, `os`, `sys`, `pathlib`, `argparse`.
2. **Offline Data Generation Only**: All artifacts are written directly to local file paths (`neo4j/data/*.csv`, `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`, `neo4j/reports/*.md`).
3. **Automated Port Lock Assertion**: The verification test harness must include an assertion verifying that no TCP sockets to port `7687` (Bolt) or `7474` (Neo4j HTTP) are attempted during script execution.

---
**Report compiled and verified by explorer_survey_3.**
