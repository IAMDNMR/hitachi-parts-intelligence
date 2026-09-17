# Implementation Strategy & Technical Architecture Report: Source Audit (`audit_workbook.py`)

**Agent**: `explorer_m1_1` (Lead Explorer — Milestone 1)  
**Milestone**: M1 (Discovery & Pre-Cleaning Source Audit)  
**Working Directory**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1`  
**Target Script**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\audit_workbook.py`  
**Target Report**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\neo4j\reports\workbook_audit.md`  
**Authoritative Source**: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`  
**Date**: 2026-09-17  

---

## 1. Executive Summary & Problem Formulation

Milestone 1 establishes the discovery and non-destructive audit baseline for the HCME After-Sales Data Foundation project. The objective is to design and implement `audit_workbook.py`, a robust CLI utility that performs a complete structural, technical, and data quality inspection across all 21 worksheets in the authoritative source workbook without modifying a single byte.

### 1.1 Non-Negotiable Project Constraints
1. **Zero Source Modification**: The authoritative source file (`HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`, ~796 KB) must remain completely untouched. Pre- and post-execution SHA-256 hashes and filesystem timestamps (`st_mtime`) must match identically.
2. **Strict Neo4j Isolation**: Under NO circumstances may `audit_workbook.py` import `neo4j` drivers, make network calls, or connect to Neo4j Aura. All operations are strictly local and filesystem-bound.
3. **100% Byte-for-Byte Determinism**: Running `audit_workbook.py` multiple times against the identical source file must produce bit-for-bit identical markdown output in `neo4j/reports/workbook_audit.md`.
4. **Complete 21-Sheet Audit Coverage**: Every single sheet (from `00_README` to `20_OPERATOR_MANUALS`) must be audited for dimensions, headers, fill rates, types, duplicates, hygiene noise, and graph classification.

---

## 2. Modular Architecture for `audit_workbook.py`

To ensure maintainability, testability, and determinism, `audit_workbook.py` is decomposed into 5 discrete, decoupled modules:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          audit_workbook.py                             │
├────────────────────────────────────────────────────────────────────────┤
│  1. CLI & Argument Parser (argparse)                                   │
│     ├── Inputs: --input (-i), --output (-o), --verify-source, --quiet  │
│     └── Exit Codes: 0 (Success), 1 (Arg Error), 2 (Missing), 3 (Tamper)│
├────────────────────────────────────────────────────────────────────────┤
│  2. Source Immutability Verifier (SourceVerifier)                      │
│     ├── SHA-256 chunked streaming reader (64 KB buffers)               │
│     ├── os.stat mtime and size baseline capture                        │
│     └── Pre/Post execution cryptographic comparison assertion          │
├────────────────────────────────────────────────────────────────────────┤
│  3. Memory-Safe Streaming Workbook Scanner (StreamingScanner)          │
│     ├── openpyxl.load_workbook(path, read_only=True, data_only=True)   │
│     ├── Sheet dimension & active row bounding                         │
│     └── Streaming iter_rows(values_only=True) row evaluation          │
├────────────────────────────────────────────────────────────────────────┤
│  4. Metrics & Profiling Engine (MetricsEngine)                         │
│     ├── Column-wise fill rate & null/empty counting                    │
│     ├── Python primitive type inference per cell                       │
│     ├── Candidate PK detection & full-row duplicate hashing            │
│     ├── URL regex & UI clutter detection                               │
│     └── Column graph classification rules (5 target classes)           │
├────────────────────────────────────────────────────────────────────────┤
│  5. Deterministic Markdown Formatter (ReportFormatter)                 │
│     ├── Static report header with SHA-256 hash (no dynamic timestamps) │
│     ├── Global 21-sheet summary table                                  │
│     ├── Deep sheet-by-sheet metric sections (tab order 0..20)          │
│     └── UTF-8 LF serialization                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Module 1: CLI & Argument Parser
- Uses standard library `argparse.ArgumentParser`.
- Supports the following options:
  - `--input`, `-i`: Path to the source `.xlsx` workbook (default: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`).
  - `--output`, `-o`: Destination path for the markdown audit report (default: `neo4j/reports/workbook_audit.md`).
  - `--verify-source`: Boolean flag (default `True`) controlling pre/post SHA-256 and timestamp verification.
  - `--quiet`, `-q`: Boolean flag (default `False`) suppressing stdout output except errors.
- Exit code semantics:
  - `0`: Success (all sheets audited, metrics calculated, source untouched, report written).
  - `1`: Invalid arguments or runtime execution error.
  - `2`: Source file not found or unreadable.
  - `3`: Immutability violation (file hash or timestamp changed during execution).

### 2.2 Module 2: Source Immutability Verifier (`SourceVerifier`)
- **Pre-execution Phase**:
  ```python
  def get_file_fingerprint(filepath: str) -> dict:
      stat = os.stat(filepath)
      hasher = hashlib.sha256()
      with open(filepath, "rb") as f:
          while chunk := f.read(65536):
              hasher.update(chunk)
      return {
          "sha256": hasher.hexdigest(),
          "mtime": stat.st_mtime,
          "size": stat.st_size
      }
  ```
- **Post-execution Verification**:
  Recomputes fingerprint immediately after `openpyxl` workbook is closed. Asserts:
  - `pre["sha256"] == post["sha256"]`
  - `pre["mtime"] == post["mtime"]`
  - `pre["size"] == post["size"]`
  If any comparison fails, raises `ImmutabilityViolationError` and exits with code `3`.

### 2.3 Module 3: Memory-Safe Streaming Workbook Scanner (`StreamingScanner`)
- Uses `openpyxl.load_workbook(path, read_only=True, data_only=True)`.
  - `read_only=True`: Streams sheet XML on-demand without loading full DOM into memory, preventing memory bloat.
  - `data_only=True`: Evaluates cached formula values rather than formula expressions.
- Enumerates sheets in exact order: `wb.sheetnames`. Asserts sheet count is 21.
- For each sheet, streams rows via `sheet.iter_rows(values_only=True)`.
- Explicitly calls `wb.close()` upon completion.

### 2.4 Module 4: Metrics & Profiling Engine (`MetricsEngine`)
Processes each row stream in a single pass:
1. **Header Identification**:
   - First non-empty row is identified as the header row.
   - Cleans header names (strips whitespace, preserves verbatim strings).
   - Empty column headers are assigned synthetic labels: `_col_{idx}`.
2. **Row & Cell Counting**:
   - Tracks total rows encountered.
   - Identifies and excludes trailing completely empty rows (`all(c is None or str(c).strip() == '' for c in row)`).
   - Distinguishes raw row count from active data rows.
3. **Column Fill Rates & Type Inference**:
   - For each column: non-empty count, empty/null count, fill rate percentage: `(non_empty / data_rows) * 100`.
   - Distinct cell value count (cardinality).
   - Inferred types set: evaluates each cell value (`str`, `int`, `float`, `bool`, `datetime`, `NoneType`).
4. **Duplicate Analysis**:
   - Candidate Primary Key: evaluated for the first column or columns named `*_id`, `sheet_name`, or `code`.
   - Primary key uniqueness: verifies if unique count equals active data row count.
   - Collects sample duplicate IDs (sorted, maximum 5).
   - Full-row duplicate detection: computes 64-bit row content hashes to identify exact duplicate rows.
5. **Data Hygiene & Pattern Flagging**:
   - **URL Regex**: `re.compile(r'(https?://[^\s,]+|www\.[^\s,]+|[a-zA-Z0-9.-]+\.(?:com|eu|org|net|de|co\.uk)(?:/[^\s,]*)?)', re.IGNORECASE)`.
   - **UI / E-Commerce Clutter**: Flags columns whose header names match `ui_rank`, `featured`, `search_rank`, `priority`, `cart`, `badge`, `display_priority`, `marketing_copy`.
   - **Sentinel Value Detection**: Counts occurrences of `"NOT PUBLICLY STATED"`, `"N/A"`, `"NA"`, `"-"`, `"TBD"`, `"UNKNOWN"`.
   - **Whitespace / Encoding Defects**: Detects `\u00a0` (non-breaking spaces), `\r`, multi-space runs, leading/trailing whitespace.
6. **Column Graph Utility Classification**:
   Maps every column into one of 5 controlled classes:
   - `TECHNICAL_ENTITY_ATTRIBUTE`: Core node property (e.g. `operating_weight_kg`, `rated_power_kw`).
   - `GRAPH_RELATIONSHIP_POINTER`: Graph edge pointer / foreign key (e.g. `category_id`, `machine_id`, `part_id`).
   - `PROVENANCE_METADATA`: Audit citation or source reference (e.g. `source_url`, `source_name`, `extraction_date`).
   - `CONTROLLED_VOCAB_FIELD`: Controlled enum field requiring vocabulary mapping (e.g. `fitment_evidence`, `record_class`, `classification`).
   - `NOISE_TO_REMOVE`: Ephemeral marketing or UI clutter to discard (e.g. `ui_search_rank`, `featured_badge`).

### 2.5 Module 5: Deterministic Markdown Formatter (`ReportFormatter`)
- Generates `neo4j/reports/workbook_audit.md`.
- Enforces determinism:
  - **Static Header**: Contains tool name, source file name, and static SHA-256 hash. Zero dynamic timestamps (`datetime.now()`).
  - **Deterministic Ordering**: Sheets strictly ordered 00 to 20; columns ordered 1 to N; duplicate samples and types sorted alphabetically.
  - **Deterministic Formatting**: Percentages formatted as `f"{val:.2f}%"`, integers as decimals, missing values as `""`.
  - **Encoding & Newlines**: Always writes with `utf-8` encoding and standard `\n` (LF) line endings.

---

## 3. Exhaustive Sheet-by-Sheet Audit Specification (All 21 Source Sheets)

The table and detailed specifications below establish the audit expectations and classification baseline across all 21 worksheets:

### 3.1 Master Catalog of 21 Source Sheets

| Tab # | Sheet Name | Expected Domain | Est. Rows | Est. Cols | Primary Key Candidate | Target Clean Sheet | Target CSV |
|:---:|---|---|:---:|:---:|---|---|---|
| **00** | `00_README` | System Metadata & Data Dictionary | 45 | 6 | `sheet_name` / `sheet_index` | `00_README` | *(Metadata)* |
| **01** | `01_CATEGORIES` | Machine Category Taxonomy Hierarchy | 15 | 5 | `category_id` | `01_CATEGORIES` | `categories.csv` |
| **02** | `02_MACHINE_MASTER` | Machine Catalogue Master Records | 78 | 15 | `machine_id` | `02_MACHINES` | `machines.csv` |
| **03** | `03_MACHINE_SPECIFICATIONS`| Engineering Specs & UI Rankings | 78 | 18 | `spec_id` / `machine_id` | `03_SPECIFICATIONS` | `specifications.csv` |
| **04** | `04_MACHINE_APPLICATIONS` | Application Mappings & Sectors | 85 | 6 | `mapping_id` | `04_APPLICATIONS` | `applications.csv` |
| **05** | `05_ATTACHMENTS` | OEM Attachments Catalogue | 14 | 10 | `attachment_id` | `05_ATTACHMENTS` | `attachments.csv` |
| **06** | `06_PART_MASTER` | Parts Master & Product Line Families | 65 | 12 | `part_id` | `06_PARTS` | `parts.csv` |
| **07** | `07_MACHINE_PART_FITMENT` | Machine-to-Part Fitment Matrix | 450 | 8 | `fitment_id` | `07_MACHINE_PART_FITMENT` | `machine_part_fitment.csv` |
| **08** | `08_SERVICE_CAPABILITIES` | After-Sales Service Offerings | 22 | 9 | `service_id` | `08_SERVICES` | `services.csv` |
| **09** | `09_MACHINE_SERVICE_MATRIX`| Machine Service Eligibility Matrix | 280 | 7 | `mapping_id` | `09_MACHINE_SERVICE` | `machine_service.csv` |
| **10** | `10_MAINTENANCE_SCHEDULE` | Periodic Maintenance Intervals | 110 | 8 | `maintenance_id` | `10_MAINTENANCE` | `maintenance.csv` |
| **11** | `11_SERVICE_PART_REQUIREMENTS` | Maintenance Task Part BOM | 185 | 8 | `requirement_id` | `11_SERVICE_PART_REQUIREMENTS` | `service_part_requirements.csv` |
| **12** | `12_MACHINE_DIGITAL_SERVICES`| ConSite & Telematics Matrix | 90 | 9 | `digital_service_id` | `12_DIGITAL_SERVICES` | `digital_services.csv` |
| **13** | `13_AFTER_SALES_RELATIONSHIPS` | Master Relationship Register | 620 | 10 | `rel_id` | `13_RELATIONSHIPS` | `relationships.csv` |
| **14** | `14_SOURCE_PROVENANCE` | Citations, Sources & Scraping URLs | 140 | 7 | `provenance_id` | `14_PROVENANCE` | `provenance.csv` |
| **15** | `15_DEALER_NETWORK` | Dealer Workshops & Field Service | 35 | 8 | `dealer_id` | `08_SERVICES` *(Consolidated)* | *(Integrated)* |
| **16** | `16_WARRANTY_PROGRAMS` | Warranty Tiers & Hitachi HELP | 18 | 7 | `program_id` | `08_SERVICES` / `13_RELATIONSHIPS` | *(Integrated)* |
| **17** | `17_TELEMATICS_METRICS` | Telemetry Sensors & Thresholds | 42 | 8 | `metric_id` | `12_DIGITAL_SERVICES` *(Consolidated)*| *(Integrated)* |
| **18** | `18_REMAN_PARTS` | Reman Exchange Components | 28 | 9 | `reman_id` | `06_PARTS` *(Consolidated)* | `parts.csv` *(Integrated)* |
| **19** | `19_CONSUMABLES_LUBRICANTS`| Genuine Oils, Greases & Coolants | 32 | 10 | `consumable_id` | `06_PARTS` *(Consolidated)* | `parts.csv` *(Integrated)* |
| **20** | `20_OPERATOR_MANUALS` | Manuals & Operator Training | 25 | 7 | `doc_id` | `00_README` / `14_PROVENANCE` | *(Integrated)* |

---

### 3.2 Granular Sheet-by-Sheet Audit Criteria

#### Sheet 00: `00_README`
- **Domain**: System metadata, data dictionary, sheet directory.
- **Expected Columns**: `sheet_index`, `sheet_name`, `domain`, `description`, `primary_key`, `target_entity`.
- **Primary Key**: `sheet_name` or `sheet_index` (unique across 21 rows).
- **Classification**:
  - `sheet_index`, `sheet_name`, `domain`, `description`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `target_entity`: `GRAPH_RELATIONSHIP_POINTER`
- **Hygiene & Anomalies**: Documentation URLs present in text descriptions; no e-commerce noise.
- **Audit Objective**: Capture pre-cleaning documentation state; ensure dictionary completeness.

#### Sheet 01: `01_CATEGORIES`
- **Domain**: Machine taxonomic hierarchy (`(:Category)-[:CHILD_OF]->(:Category)`).
- **Expected Columns**: `category_id`, `category_name`, `parent_category_id`, `category_level`, `description`.
- **Primary Key**: `category_id` (e.g. `CAT-EXC`, `CAT-MINI`, `CAT-MED`, `CAT-LRG`, `CAT-WL`, `CAT-RDT`).
- **Classification**:
  - `category_id`, `category_name`, `category_level`, `description`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `parent_category_id`: `GRAPH_RELATIONSHIP_POINTER`
- **Hygiene & Anomalies**:
  - Root categories (`Excavators`, `Wheel Loaders`, `Rigid Dump Trucks`) have empty/null `parent_category_id`.
  - Whitespace irregularities (trailing spaces in subcategory strings).
  - Acyclic hierarchy invariant: `parent_category_id != category_id`.
- **Audit Objective**: Verify primary key uniqueness (14 rows), identify root categories, flag trailing whitespace.

#### Sheet 02: `02_MACHINE_MASTER`
- **Domain**: Hitachi machine catalogue pages and model code mappings.
- **Expected Columns**: `machine_id`, `model_name`, `base_model`, `models_covered`, `model_count`, `category_id`, `subcategory`, `visual_category`, `machine_type`, `power_type`, `application`, `operating_weight_kg`, `engine_power_kw`, `source_url`, `status`.
- **Primary Key**: `machine_id` (`MC-001` through `MC-077`, 100% unique, exactly 77 data rows).
- **Classification**:
  - `machine_id`, `model_name`, `base_model`, `models_covered`, `model_count`, `subcategory`, `machine_type`, `power_type`, `operating_weight_kg`, `engine_power_kw`, `status`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `category_id`: `GRAPH_RELATIONSHIP_POINTER` (`BELONGS_TO`)
  - `application`: `GRAPH_RELATIONSHIP_POINTER` (`SUITABLE_FOR`)
  - `source_url`: `PROVENANCE_METADATA` (Isolate to `provenance.csv`)
  - `visual_category`: `NOISE_TO_REMOVE` (UI routing artifact)
- **Hygiene & Anomalies**:
  - **Critical Disambiguation**: 77 catalogue records cover 85 model codes. For example, `MC-004` covers `ZX250-7; ZX300-7; ZX350-7` (`model_count = 3`).
  - **Special Applications Overlap**: Three distinct demolition excavators share base model code `ZX250-7` (High Reach, Multi-Carrier, Straight Boom). Merging on model code destroys distinct catalogue records.
  - URL present in `source_url`.
- **Audit Objective**: Audit row count (77), assert uniqueness of `machine_id`, record model count distribution, flag `source_url`.

#### Sheet 03: `03_MACHINE_SPECIFICATIONS`
- **Domain**: Genuine engineering specifications mixed with UI/e-commerce ranking noise.
- **Expected Columns**: `spec_id`, `machine_id`, `operating_weight_min_kg`, `operating_weight_max_kg`, `rated_power_kw`, `rated_power_hp`, `bucket_capacity_min_m3`, `bucket_capacity_max_m3`, `max_digging_reach_mm`, `max_digging_depth_mm`, `max_dumping_height_mm`, `swing_speed_rpm`, `travel_speed_kmh`, `payload_capacity_tonnes`, `ui_search_rank`, `featured_badge`, `display_priority`, `source_url`.
- **Primary Key**: `spec_id` (1:1 with `machine_id`, 77 rows).
- **Classification**:
  - `spec_id`, all engineering specification metrics: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `machine_id`: `GRAPH_RELATIONSHIP_POINTER` (`HAS_SPECIFICATION`)
  - `source_url`: `PROVENANCE_METADATA`
  - `ui_search_rank`, `featured_badge`, `display_priority`: `NOISE_TO_REMOVE`
- **Hygiene & Anomalies**:
  - Sentinels `"NOT PUBLICLY STATED"`, `"N/A"`, `"-"` present across unstated electric or concept specs. Must convert to `""` / `None`.
  - Pure e-commerce clutter columns (`ui_search_rank`, `featured_badge`, `display_priority`) must be cataloged for removal.
- **Audit Objective**: Document fill rates across all technical columns, count sentinel value occurrences, flag UI clutter columns.

#### Sheet 04: `04_MACHINE_APPLICATIONS`
- **Domain**: Operational sectors and machine suitability mappings.
- **Expected Columns**: `mapping_id`, `machine_id`, `application_id`, `application_name`, `suitability_rating`, `notes`.
- **Primary Key**: `mapping_id`.
- **Classification**:
  - `mapping_id`, `suitability_rating`, `notes`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `machine_id`, `application_id`: `GRAPH_RELATIONSHIP_POINTER` (`SUITABLE_FOR`)
  - `application_name`: `CONTROLLED_VOCAB_FIELD`
- **Hygiene & Anomalies**:
  - Inconsistent casing and delimiters (e.g. `"Demolition"`, `"demolition "`, `"Quarry/Mining"`).
  - Trailing spaces and compound strings.
- **Audit Objective**: Identify non-canonical application names, verify foreign key references to `02_MACHINE_MASTER`.

#### Sheet 05: `05_ATTACHMENTS`
- **Domain**: OEM attachments catalogue (buckets, breakers, couplers, shears).
- **Expected Columns**: `attachment_id`, `attachment_name`, `attachment_type`, `application_id`, `compatibility_level`, `capacity_m3`, `weight_kg`, `description`, `source_url`, `ui_order`.
- **Primary Key**: `attachment_id` (13 distinct attachments, e.g. `backhoe-bucket`, `hydraulic-breaker`).
- **Classification**:
  - `attachment_id`, `attachment_name`, `attachment_type`, `capacity_m3`, `weight_kg`, `description`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `application_id`: `GRAPH_RELATIONSHIP_POINTER`
  - `compatibility_level`: `CONTROLLED_VOCAB_FIELD`
  - `source_url`: `PROVENANCE_METADATA`
  - `ui_order`: `NOISE_TO_REMOVE`
- **Hygiene & Anomalies**:
  - **No Part Numbers**: None of the 13 attachments have published part numbers. Do NOT manufacture synthetic SKUs.
  - **Tilt Bucket Absence**: `tilt-bucket` has zero fitment records in `07_MACHINE_PART_FITMENT`.
  - Full URLs in `source_url`.
- **Audit Objective**: Assert exactly 13 attachments, confirm null part number status, flag `source_url` and `ui_order`.

#### Sheet 06: `06_PART_MASTER`
- **Domain**: Parts catalogue mixing orderable OEM parts and high-level product line families.
- **Expected Columns**: `part_id`, `part_name`, `oem_part_number`, `part_category`, `component_type`, `record_class`, `unit_of_measure`, `description`, `supplier`, `lead_time_days`, `source_url`, `ui_rank`.
- **Primary Key**: `part_id` (`PT-001`..).
- **Classification**:
  - `part_id`, `part_name`, `oem_part_number`, `component_type`, `unit_of_measure`, `description`, `supplier`, `lead_time_days`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `part_category`: `GRAPH_RELATIONSHIP_POINTER`
  - `record_class`: `CONTROLLED_VOCAB_FIELD` (`ORDERABLE_OEM_PART` vs `PRODUCT_LINE_PART_FAMILY`)
  - `source_url`: `PROVENANCE_METADATA`
  - `ui_rank`: `NOISE_TO_REMOVE`
- **Hygiene & Anomalies**:
  - Conflation of discrete parts (e.g. Starter Battery `4663907`) with broad lines (e.g. "Hitachi Genuine Parts", "Genuine Undercarriage").
  - Hallucination guard: 26 prohibited fake part names (e.g. `main-control-valve`, `swing-motor`) must not appear.
- **Audit Objective**: Audit distribution of populated vs empty `oem_part_number`, verify `record_class` tagging, detect UI noise.

#### Sheet 07: `07_MACHINE_PART_FITMENT`
- **Domain**: Machine-to-part compatibility matrix.
- **Expected Columns**: `fitment_id`, `machine_id`, `part_id`, `fitment_level`, `fitment_evidence`, `verified_by`, `notes`, `source_row`.
- **Primary Key**: `fitment_id` (~450 rows).
- **Classification**:
  - `fitment_id`, `notes`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `machine_id`, `part_id`: `GRAPH_RELATIONSHIP_POINTER` (`USES_PART`)
  - `fitment_level`, `fitment_evidence`: `CONTROLLED_VOCAB_FIELD` (`EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`)
  - `verified_by`, `source_row`: `PROVENANCE_METADATA`
- **Hygiene & Anomalies**:
  - Raw evidence vocabulary drift (`"EXACT MODEL"`, `"MODEL/RANGE"`, `"confirmed by dealer forum post"`).
  - Potential conflicting fitment claims (same machine + part asserting contradictory compatibility).
- **Audit Objective**: Profile `fitment_evidence` frequency distribution, detect non-controlled vocabulary strings, identify conflicting pairs.

#### Sheet 08: `08_SERVICE_CAPABILITIES`
- **Domain**: Dealer and OEM after-sales service programs, preventative maintenance, inspection scopes.
- **Expected Columns**: `service_id`, `service_name`, `service_category`, `location_capabilities`, `description`, `sla_hours`, `certification_required`, `source_url`, `marketing_copy`.
- **Primary Key**: `service_id` (`SRV-001`..).
- **Classification**:
  - `service_id`, `service_name`, `service_category`, `description`, `sla_hours`, `certification_required`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `location_capabilities`: `CONTROLLED_VOCAB_FIELD` (`FIELD_SERVICE`, `DEALER_WORKSHOP`, `REMOTE`)
  - `source_url`: `PROVENANCE_METADATA`
  - `marketing_copy`: `NOISE_TO_REMOVE`
- **Hygiene & Anomalies**: Marketing slogans, promotional blurbs, dealer portal links.
- **Audit Objective**: Count location capability occurrences, flag promotional copy for stripping.

#### Sheet 09: `09_MACHINE_SERVICE_MATRIX`
- **Domain**: Machine-to-service eligibility cross-reference.
- **Expected Columns**: `mapping_id`, `machine_id`, `service_id`, `eligibility_tier`, `applicability_evidence`, `mandatory_flag`, `notes`.
- **Primary Key**: `mapping_id` (~280 rows).
- **Classification**:
  - `mapping_id`, `mandatory_flag`, `notes`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `machine_id`, `service_id`: `GRAPH_RELATIONSHIP_POINTER` (`ELIGIBLE_FOR_SERVICE`)
  - `eligibility_tier`, `applicability_evidence`: `CONTROLLED_VOCAB_FIELD`
- **Hygiene & Anomalies**: Unresolvable machine or service foreign key candidates.
- **Audit Objective**: Verify candidate foreign keys against `02_MACHINE_MASTER` and `08_SERVICE_CAPABILITIES`.

#### Sheet 10: `10_MAINTENANCE_SCHEDULE`
- **Domain**: Periodic maintenance intervals (50h..2000h) and scheduled tasks.
- **Expected Columns**: `maintenance_id`, `machine_id`, `interval_hours`, `interval_months`, `system_code`, `maintenance_action`, `task_description`, `mandatory_flag`.
- **Primary Key**: `maintenance_id` (~110 rows).
- **Classification**:
  - `maintenance_id`, `interval_hours`, `interval_months`, `system_code`, `task_description`, `mandatory_flag`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `machine_id`: `GRAPH_RELATIONSHIP_POINTER` (`HAS_MAINTENANCE`)
  - `maintenance_action`: `CONTROLLED_VOCAB_FIELD` (`INSPECT`, `REPLACE`, `LUBRICATE`, `ADJUST`, `CLEAN`)
- **Hygiene & Anomalies**: Non-standard interval strings (e.g. `"Every 500 hours or 6 months"`).
- **Audit Objective**: Profile hour intervals and task verbs, confirm candidate graph entity viability.

#### Sheet 11: `11_SERVICE_PART_REQUIREMENTS`
- **Domain**: Maintenance task Bill-of-Materials linking intervals to required replacement parts.
- **Expected Columns**: `requirement_id`, `maintenance_id`, `part_id`, `quantity`, `unit_of_measure`, `optional_flag`, `notes`, `source_doc`.
- **Primary Key**: `requirement_id` (~185 rows).
- **Classification**:
  - `requirement_id`, `quantity`, `unit_of_measure`, `optional_flag`, `notes`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `maintenance_id`, `part_id`: `GRAPH_RELATIONSHIP_POINTER` (`REQUIRES_PART`)
  - `source_doc`: `PROVENANCE_METADATA`
- **Hygiene & Anomalies**: Inconsistent units of measure (`PIECE`, `L`, `LITRE`, `SET`), potential dangling part references.
- **Audit Objective**: Audit quantity numeric parseability, profile unit values, cross-check foreign keys.

#### Sheet 12: `12_MACHINE_DIGITAL_SERVICES`
- **Domain**: Telematics capabilities (ConSite, Global e-Service, OTA).
- **Expected Columns**: `digital_service_id`, `machine_id`, `platform_name`, `telematics_hardware`, `monitoring_tier`, `report_frequency`, `applicability_evidence`, `source_url`, `ui_status`.
- **Primary Key**: `digital_service_id` (~90 rows).
- **Classification**:
  - `digital_service_id`, `platform_name`, `telematics_hardware`, `monitoring_tier`, `report_frequency`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `machine_id`: `GRAPH_RELATIONSHIP_POINTER` (`HAS_DIGITAL_SERVICE`)
  - `applicability_evidence`: `CONTROLLED_VOCAB_FIELD`
  - `source_url`: `PROVENANCE_METADATA`
  - `ui_status`: `NOISE_TO_REMOVE`
- **Hygiene & Anomalies**: External web portal login URLs and marketing status flags.
- **Audit Objective**: Audit telematics platform coverage and URL leakage.

#### Sheet 13: `13_AFTER_SALES_RELATIONSHIPS`
- **Domain**: Master cross-domain relationship ledger across all entities.
- **Expected Columns**: `rel_id`, `source_type`, `source_id`, `relationship_type`, `target_type`, `target_id`, `classification`, `evidence_type`, `confidence`, `notes`.
- **Primary Key**: `rel_id` (~620 rows).
- **Classification**:
  - `rel_id`, `notes`: `TECHNICAL_ENTITY_ATTRIBUTE`
  - `source_id`, `target_id`: `GRAPH_RELATIONSHIP_POINTER`
  - `source_type`, `target_type`, `relationship_type`: `GRAPH_RELATIONSHIP_POINTER` / Metadata
  - `classification`: `CONTROLLED_VOCAB_FIELD` (`CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`)
  - `evidence_type`, `confidence`: `PROVENANCE_METADATA`
- **Hygiene & Anomalies**:
  - Duplicate edges, research-only links, unmapped external IDs causing dangling edges.
  - Referential integrity gate: Only `CORE` edges with 100% verified endpoints may be exported.
- **Audit Objective**: Profile relationship classification distribution, audit foreign key validity for `CORE` candidates.

#### Sheet 14: `14_SOURCE_PROVENANCE`
- **Domain**: Centralized provenance store, citations, scraping timestamps, confidence.
- **Expected Columns**: `provenance_id`, `entity_id`, `source_name`, `source_url`, `extraction_date`, `evidence_type`, `confidence`.
- **Primary Key**: `provenance_id` (~140 rows).
- **Classification**:
  - `provenance_id`, `source_name`, `extraction_date`: `PROVENANCE_METADATA`
  - `entity_id`: `GRAPH_RELATIONSHIP_POINTER` (resolves to any entity/relationship ID)
  - `source_url`: `PROVENANCE_METADATA` (Isolated URL store)
  - `evidence_type`, `confidence`: `CONTROLLED_VOCAB_FIELD`
- **Hygiene & Anomalies**: Sole authorized repository for raw URL strings.
- **Audit Objective**: Verify URL formatting and entity resolution.

#### Sheet 15: `15_DEALER_NETWORK`
- **Domain**: European dealer network, workshops, field service vans, countries.
- **Expected Columns**: `dealer_id`, `dealer_name`, `country`, `city`, `field_service_vans`, `workshop_bays`, `contact_phone`, `source_url`.
- **Primary Key**: `dealer_id` (~35 rows).
- **Classification**: Consolidated into `08_SERVICES` (location capabilities) and service metadata. Contact phone is noise to remove.
- **Audit Objective**: Capture workshop capacity and location metrics; flag contact phone as noise.

#### Sheet 16: `16_WARRANTY_PROGRAMS`
- **Domain**: Hitachi HELP and warranty programs.
- **Expected Columns**: `program_id`, `program_name`, `duration_months`, `operating_hours_limit`, `coverage_scope`, `deductible`, `source_url`.
- **Primary Key**: `program_id` (~18 rows).
- **Classification**: Consolidated into `08_SERVICES` and `13_RELATIONSHIPS` (warranty eligibility edges).
- **Audit Objective**: Audit warranty terms and coverage hours.

#### Sheet 17: `17_TELEMATICS_METRICS`
- **Domain**: ConSite telemetry parameters, sensor alarms, alert thresholds.
- **Expected Columns**: `metric_id`, `metric_name`, `sensor_type`, `unit`, `warning_threshold`, `critical_threshold`, `system_component`, `notes`.
- **Primary Key**: `metric_id` (~42 rows).
- **Classification**: Consolidated into `12_DIGITAL_SERVICES` telemetry attributes.
- **Audit Objective**: Profile telemetry sensor types and threshold definitions.

#### Sheet 18: `18_REMAN_PARTS`
- **Domain**: Remanufactured components and exchange program units.
- **Expected Columns**: `reman_id`, `component_name`, `reman_type`, `warranty_months`, `core_return_required`, `applicable_machine_types`, `notes`, `source_url`, `ui_rank`.
- **Primary Key**: `reman_id` (~28 rows).
- **Classification**: Integrated into `06_PARTS` as `PRODUCT_LINE_PART_FAMILY`. `ui_rank` is noise to remove.
- **Audit Objective**: Verify absence of manufactured SKUs; confirm exclusion of Rigid Dump Trucks from reman applicability.

#### Sheet 19: `19_CONSUMABLES_LUBRICANTS`
- **Domain**: Genuine engine oils, hydraulic oils, coolants, greases.
- **Expected Columns**: `consumable_id`, `product_name`, `fluid_grade`, `pack_sizes`, `oem_part_number`, `change_interval_hours`, `viscosity`, `source_url`, `notes`, `ui_order`.
- **Primary Key**: `consumable_id` (~32 rows).
- **Classification**: Integrated into `06_PARTS`: `ORDERABLE_OEM_PART` if `oem_part_number` populated, else `PRODUCT_LINE_PART_FAMILY`. `ui_order` is noise.
- **Audit Objective**: Detect which fluids have published part numbers vs fluid grades.

#### Sheet 20: `20_OPERATOR_MANUALS`
- **Domain**: Technical manuals, operator handbooks, training programs.
- **Expected Columns**: `doc_id`, `title`, `machine_model_or_family`, `doc_type`, `language`, `publication_year`, `source_url`.
- **Primary Key**: `doc_id` (~25 rows).
- **Classification**: Integrated into documentation provenance in `00_README` and `14_PROVENANCE`.
- **Audit Objective**: Document publication dates and document types.

---

## 4. Strict Immutability & Safety Verification Protocol

To guarantee and prove that the source workbook is never modified:

### 4.1 Immutability Guardrail Implementation
```python
import hashlib
import os
import sys

def verify_source_integrity(filepath: str, baseline_fingerprint: dict) -> None:
    current_stat = os.stat(filepath)
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    current_hash = hasher.hexdigest()

    if (
        current_hash != baseline_fingerprint["sha256"]
        or current_stat.st_mtime != baseline_fingerprint["mtime"]
        or current_stat.st_size != baseline_fingerprint["size"]
    ):
        sys.stderr.write(
            f"FATAL IMMUTABILITY VIOLATION: Source file '{filepath}' was modified!\n"
            f"Expected SHA256: {baseline_fingerprint['sha256']}\n"
            f"Observed SHA256: {current_hash}\n"
            f"Expected mtime:  {baseline_fingerprint['mtime']}\n"
            f"Observed mtime:  {current_stat.st_mtime}\n"
        )
        sys.exit(3)
```

### 4.2 Read-Only File Handle Safety
- Always open via `openpyxl.load_workbook(..., read_only=True, data_only=True)`.
- Never invoke `wb.save()`.
- Wrap workbook streaming inside a `try...finally` block ensuring `wb.close()` is always executed.

---

## 5. Strict Neo4j Isolation Guardrail Compliance

To satisfy Feature 30 and Requirement R6:
- `audit_workbook.py` must contain **ZERO** imports of `neo4j`, `py2neo`, or any database connection drivers.
- The script operates purely on local filesystem files via Python standard library and `openpyxl`.
- No socket connections to port 7687 (Bolt) or 7474 (HTTP) are initiated.
- Downstream reviewers and test harnesses will verify this via static AST analysis and network socket inspection.

---

## 6. Implementation Plan for Downstream Worker Agent

1. **Script Creation**: Implement `audit_workbook.py` in the workspace root (`c:\Users\iamdn\OneDrive\Desktop\Parts&Service\audit_workbook.py`).
2. **Pre-flight Check**: Verify input workbook exists at `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`.
3. **Execution**: Run `python audit_workbook.py --input C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx --output neo4j/reports/workbook_audit.md`.
4. **Validation**:
   - Assert exit code 0.
   - Assert `neo4j/reports/workbook_audit.md` exists and contains sections for all 21 sheets.
   - Assert source workbook SHA-256 and modification time remain completely untouched.
   - Run twice to verify byte-identical output (determinism test).
