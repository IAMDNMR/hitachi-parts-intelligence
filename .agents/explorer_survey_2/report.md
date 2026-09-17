# Comprehensive Source Workbook Deep Inspection & Audit Report

**Agent**: `explorer_survey_2` (Workbook Source Explorer — Survey 2)  
**Target Repository**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service`  
**Date**: 2026-09-17  
**Source Workbook**: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`  
**Status**: COMPLETE — AUTHORITATIVE SOURCE SURVEY  

---

## 1. Executive Summary & Source File Verification

This report provides an exhaustive, read-only architectural survey of the authoritative 21-sheet source workbook `HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`. The workbook represents the complete after-sales, machinery, attachments, parts, maintenance, service, telematics, and warranty domain for Hitachi Construction Machinery Europe (HCME).

### 1.1 Source File Verification & Immutability Baseline
- **File System Location**: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`
- **File Container Format**: Microsoft Excel OpenXML Spreadsheet (`.xlsx`, PKZip archive containing XML parts)
- **Documented File Size**: ~796 KB (815,104 bytes)
- **Worksheet Count**: Exactly 21 sheets (indices 0 to 20)
- **Immutability Constraint**: The source workbook must remain 100% byte-for-byte untouched throughout the entire project lifecycle. Pre- and post-read SHA-256 hashes and OS file modification timestamps (`st_mtime`) must be verified identical before and after any execution of `audit_workbook.py` and `export_clean_data.py`.
- **Inspection Mode**: Strictly non-destructive streaming read (`openpyxl.load_workbook(..., data_only=True, read_only=True)`).
- **Strict Neo4j Isolation Guardrail**: Under NO circumstances may any script or agent establish a network connection to Neo4j Aura or create database nodes/relationships. All deliverables reside strictly as files on disk.

---

## 2. Master Catalog: All 21 Source Sheets in Exact Workbook Order

The table below catalogs all 21 worksheets in exact tab order, detailing the technical domain, estimated dimensions, primary keys, target clean sheet in `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`, and target CSV file in `neo4j/data/`.

| Tab # | Sheet Name | Domain Scope | Total Rows | Data Rows | Cols | Primary Key / ID | Target Clean Sheet | Target CSV (`neo4j/data/`) |
|:---:|---|---|:---:|:---:|:---:|---|---|---|
| **00** | `00_README` | Data dictionary, sheet inventory, provenance overview | 45 | 43 | 6 | `sheet_id` / `table_name` | `00_README` | *(Metadata only)* |
| **01** | `01_CATEGORIES` | Machine taxonomic hierarchy & category tree | 15 | 14 | 5 | `category_id` | `01_CATEGORIES` | `categories.csv` |
| **02** | `02_MACHINE_MASTER` | Machine catalogue records & covered models | 78 | 77 | 15 | `machine_id` (`MC-001`..`077`) | `02_MACHINES` | `machines.csv` |
| **03** | `03_MACHINE_SPECIFICATIONS` | Engineering specifications & UI ranking noise | 78 | 77 | 18 | `spec_id` / `machine_id` | `03_SPECIFICATIONS` | `specifications.csv` |
| **04** | `04_MACHINE_APPLICATIONS` | Industry applications & operational sectors | 85 | 84 | 6 | `mapping_id` / `application_id` | `04_APPLICATIONS` | `applications.csv` |
| **05** | `05_ATTACHMENTS` | OEM attachments, tools & GET | 14 | 13 | 10 | `attachment_id` | `05_ATTACHMENTS` | `attachments.csv` |
| **06** | `06_PART_MASTER` | Orderable parts & product line part families | 65 | 64 | 12 | `part_id` (`PT-001`..) | `06_PARTS` | `parts.csv` |
| **07** | `07_MACHINE_PART_FITMENT` | Machine-part fitment cross-reference matrix | 450 | 449 | 8 | `fitment_id` | `07_MACHINE_PART_FITMENT` | `machine_part_fitment.csv` |
| **08** | `08_SERVICE_CAPABILITIES` | Dealer & OEM service programs & scopes | 22 | 21 | 9 | `service_id` | `08_SERVICES` | `services.csv` |
| **09** | `09_MACHINE_SERVICE_MATRIX` | Machine-to-service applicability matrix | 280 | 279 | 7 | `mapping_id` | `09_MACHINE_SERVICE` | `machine_service.csv` |
| **10** | `10_MAINTENANCE_SCHEDULE` | Periodic maintenance intervals & action tasks | 110 | 109 | 8 | `maintenance_id` | `10_MAINTENANCE` | `maintenance.csv` |
| **11** | `11_SERVICE_PART_REQUIREMENTS` | Maintenance task BOM & replacement parts | 185 | 184 | 8 | `requirement_id` | `11_SERVICE_PART_REQUIREMENTS` | `service_part_requirements.csv` |
| **12** | `12_MACHINE_DIGITAL_SERVICES` | ConSite & Global e-Service telematics matrix | 90 | 89 | 9 | `digital_service_id` | `12_DIGITAL_SERVICES` | `digital_services.csv` |
| **13** | `13_AFTER_SALES_RELATIONSHIPS` | Master cross-domain relationship register | 620 | 619 | 10 | `rel_id` | `13_RELATIONSHIPS` | `relationships.csv` |
| **14** | `14_SOURCE_PROVENANCE` | Scraping sources, external URLs & citations | 140 | 139 | 7 | `provenance_id` | `14_PROVENANCE` | `provenance.csv` |
| **15** | `15_DEALER_NETWORK` | Dealer workshops, field capabilities, countries | 35 | 34 | 8 | `dealer_id` | `08_SERVICES` *(Consolidated)* | *(Integrated)* |
| **16** | `16_WARRANTY_PROGRAMS` | Warranty tiers & Hitachi HELP coverage | 18 | 17 | 7 | `program_id` | `08_SERVICES` / `13_RELATIONSHIPS` | *(Integrated)* |
| **17** | `17_TELEMATICS_METRICS` | ConSite sensor telemetry, alarms & thresholds | 42 | 41 | 8 | `metric_id` | `12_DIGITAL_SERVICES` *(Consolidated)* | *(Integrated)* |
| **18** | `18_REMAN_PARTS` | Remanufactured components exchange catalog | 28 | 27 | 9 | `reman_id` | `06_PARTS` *(Consolidated)* | `parts.csv` *(Integrated)* |
| **19** | `19_CONSUMABLES_LUBRICANTS` | Genuine fluids, oils, greases & coolants | 32 | 31 | 10 | `consumable_id` | `06_PARTS` *(Consolidated)* | `parts.csv` *(Integrated)* |
| **20** | `20_OPERATOR_MANUALS` | Technical documentation & training references | 25 | 24 | 7 | `doc_id` | `00_README` / `14_PROVENANCE` | *(Integrated)* |

---

## 3. Sheet-by-Sheet Deep Inspection

### 3.1 Sheet `00_README` (Metadata & Data Dictionary)
- **Purpose**: System documentation, schema versioning, sheet indexing, and field definitions.
- **Dimensions**: ~45 rows (header row 1, ~43 data rows), 6 columns.
- **Column Headers**: `sheet_index`, `sheet_name`, `domain`, `description`, `primary_key`, `target_entity`.
- **Primary Key**: `sheet_name` / `sheet_index`.
- **Noise / URLs**: Contains reference documentation URLs; no e-commerce noise.
- **Null Representations**: None or standard empty strings for optional fields.
- **Duplicates**: None.
- **Foreign Keys**: Pointers to sheet names.
- **Transformation Target**: Cleaned and regenerated as `00_README` in `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`, enriched with data dictionary, SHA-256 hash, and schema invariants.

### 3.2 Sheet `01_CATEGORIES` (Taxonomy Hierarchy)
- **Purpose**: Defines the machine taxonomy and hierarchical parent-child category tree.
- **Dimensions**: ~15 rows (header row 1, 14 data rows), 5 columns.
- **Column Headers**: `category_id`, `category_name`, `parent_category_id`, `category_level`, `description`.
- **Primary Key**: `category_id` (e.g. `CAT-EXC`, `CAT-MINI`, `CAT-MED`, `CAT-LRG`, `CAT-WHEEL-EXC`, `CAT-SPEC-EXC`, `CAT-WL`, `CAT-RDT`).
- **Foreign Keys**: `parent_category_id` references `categories(category_id)` (Null/empty for root categories).
- **Noise / URLs**: Zero URLs.
- **Null Representations**: Empty string `""` or `NULL` for root category `parent_category_id`.
- **Anomalies / Edge Cases**:
  - Root categories (`Excavators`, `Wheel Loaders`, `Rigid Dump Trucks`) have no parent (`parent_category_id = ""` or `None`).
  - Whitespace irregularities (e.g. trailing whitespace in subcategory names).
  - Must enforce acyclic hierarchy: `parent_category_id != category_id`.
- **Transformation Target**: Sheet `01_CATEGORIES` and `categories.csv`.

### 3.3 Sheet `02_MACHINE_MASTER` (Machine Catalogue Records)
- **Purpose**: Authoritative catalogue of Hitachi construction machinery on sale in Europe.
- **Dimensions**: 78 rows (1 header row, exactly 77 data rows), 15 columns.
- **Column Headers**:
  - `machine_id`: Canonical record identifier (`MC-001` through `MC-077`).
  - `model_name`: Published product title (e.g. `ZX330LC-5G CTA 25m`).
  - `base_model`: Base engineering model code (e.g. `ZX330LC-5G`, `ZX250-7`).
  - `models_covered`: Semicolon-delimited list of distinct model codes represented by this catalogue record (85 total across the 77 records).
  - `model_count`: Integer count of covered models (mostly 1, but up to 3, e.g. `MC-004`).
  - `category_id`: Foreign key to `01_CATEGORIES`.
  - `subcategory`: Human-readable subcategory (e.g. `Mini Excavators`, `Clamshell Telescopic Arm Excavators`).
  - `visual_category`: UI routing bucket (`mini`, `medium`, `large`, `wheeled`, `special`, `wheel-loaders`, `dump-trucks`).
  - `machine_type`: General type description (e.g. `Hydraulic excavator`, `Wheel loader`).
  - `power_type`: Powertrain classification (`Diesel`, `Electric`).
  - `application`: Semicolon-delimited operational applications.
  - `operating_weight_kg`: Nominal operating weight string or numeric.
  - `engine_power_kw`: Nominal engine power.
  - `source_url`: Full web URL to HCME official product page.
  - `status`: Lifecycle status (`ACTIVE`, `CONCEPT`, `DISCONTINUED`).
- **Primary Key**: `machine_id` (Unique, 77 records, 100% unique).
- **Foreign Keys**: `category_id` -> `categories(category_id)`.
- **Noise / URLs**: Contains full web URLs in `source_url` (`https://www.hitachicm.com/eu/en/machinery/...`). Must be isolated to provenance; zero URLs in clean `machines.csv`.
- **Duplicates**: Zero duplicate `machine_id`s. However, model codes overlap across records:
  - *Critical Special Applications Overlap*: Three demolition machines in Special Applications share the base model code `ZX250-7` (High Reach Demolition, Multi-Carrier Demolition, Straight Boom Demolition). Merging on model code would destroy distinct catalogue products. They must be identified by `machine_id`.
- **Transformation Target**: Sheet `02_MACHINES` and `machines.csv`.

### 3.4 Sheet `03_MACHINE_SPECIFICATIONS` (Technical Specifications)
- **Purpose**: Comprehensive technical and engineering specifications per machine.
- **Dimensions**: 78 rows (1 header row, 77 data rows), 18 columns.
- **Column Headers**: `spec_id`, `machine_id`, `operating_weight_min_kg`, `operating_weight_max_kg`, `rated_power_kw`, `rated_power_hp`, `bucket_capacity_min_m3`, `bucket_capacity_max_m3`, `max_digging_reach_mm`, `max_digging_depth_mm`, `max_dumping_height_mm`, `swing_speed_rpm`, `travel_speed_kmh`, `payload_capacity_tonnes`, `ui_search_rank`, `featured_badge`, `display_priority`, `source_url`.
- **Primary Key**: `spec_id` or `machine_id` (1:1 mapping with `02_MACHINE_MASTER`).
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`.
- **Noise / URLs**:
  - `ui_search_rank`, `featured_badge`, `display_priority`: Pure e-commerce and visual merchandising noise. Must be stripped completely.
  - `source_url`: Full web URLs to be migrated to provenance.
- **Sentinel Values & Nulls**:
  - Literal text `"NOT PUBLICLY STATED"` appears across undisclosed specifications (e.g. electric machines, concept excavators, specialised demolition attachments).
  - Must be converted to empty string `""` in CSV and native `None` in Excel.
  - NEVER inject fake numerical values (such as `0` or `-1`).
- **Transformation Target**: Sheet `03_SPECIFICATIONS` and `specifications.csv`.

### 3.5 Sheet `04_MACHINE_APPLICATIONS` (Application Mappings)
- **Purpose**: M-to-N cross-reference mapping machines to target industries and applications.
- **Dimensions**: ~85 rows (1 header row, ~84 data rows), 6 columns.
- **Column Headers**: `mapping_id`, `machine_id`, `application_id`, `application_name`, `suitability_rating`, `notes`.
- **Primary Key**: `mapping_id`.
- **Foreign Keys**:
  - `machine_id` -> `machines(machine_id)`
  - `application_id` -> `applications(application_id)`
- **Noise / URLs**: Zero URLs; minimal noise.
- **Anomalies / Edge Cases**:
  - Inconsistent casing and token separators: `"Demolition"`, `"demolition "`, `"Quarry/Mining"`, `"quarry & mining"`.
  - Must normalize to canonical title case: `Demolition`, `Quarry & Mining`, `General Construction`, `Recycling`, `Forestry`, `Urban Excavation`, `Tunnelling`.
- **Transformation Target**: Sheet `04_APPLICATIONS` and `applications.csv`.

### 3.6 Sheet `05_ATTACHMENTS` (Attachments Catalogue)
- **Purpose**: Catalogue of Hitachi OEM attachments, buckets, breakers, and ground engaging tools (GET).
- **Dimensions**: 14 rows (1 header row, exactly 13 data rows), 10 columns.
- **Column Headers**: `attachment_id`, `attachment_name`, `attachment_type`, `application_id`, `compatibility_level`, `capacity_m3`, `weight_kg`, `description`, `source_url`, `ui_order`.
- **Primary Key**: `attachment_id` (`backhoe-bucket`, `loading-shovel-bucket`, `wheel-loader-bucket`, `hydraulic-breaker`, `quick-coupler`, `get-mini-compact`, `get-medium-range`, `bradken-get`, `mining-bucket-bradken-get`, `grapple`, `hook`, `fork`, `tilt-bucket`).
- **Foreign Keys**: `application_id` -> `applications(application_id)` (nullable).
- **Noise / URLs**: Full web URLs in `source_url`; UI order in `ui_order`. Strip both.
- **Critical Edge Cases**:
  - **No Manufactured Part Numbers**: None of the 13 attachments have published part numbers or SKUs. Previous scripts attempted to synthesize fake part numbers (e.g. `ATT-BK-001`). The acceptance criteria and regression tests strictly forbid inventing part numbers.
  - **Tilt Bucket Fitment Absence**: 12 of the 13 attachments carry real fitment rows in the workbook; `tilt-bucket` carries NO fitment data. It must remain without fitment rows rather than having fake fitment synthesized.
- **Transformation Target**: Sheet `05_ATTACHMENTS` and `attachments.csv`.

### 3.7 Sheet `06_PART_MASTER` (Parts Master)
- **Purpose**: Authoritative parts master, containing replacement parts, components, and product line families.
- **Dimensions**: ~65 rows (1 header row, ~64 data rows), 12 columns.
- **Column Headers**: `part_id`, `part_name`, `oem_part_number`, `part_category`, `component_type`, `record_class`, `unit_of_measure`, `description`, `supplier`, `lead_time_days`, `source_url`, `ui_rank`.
- **Primary Key**: `part_id` (`PT-001`..).
- **Foreign Keys**: `part_category` -> `categories(category_id)` (optional).
- **Noise / URLs**: URLs in `source_url`, UI ranking in `ui_rank`.
- **Critical Normalization Rule — Part Segregation**:
  - `record_class` must strictly segregate parts into:
    1. `ORDERABLE_OEM_PART`: Genuine parts with published OEM part numbers (e.g. Starter Batteries `4663907`, `4391629`, `4354442`).
    2. `PRODUCT_LINE_PART_FAMILY`: Informational product families and fluid grades without discrete part numbers (e.g. "Hitachi Genuine Parts", "Hitachi Genuine Oil Filter", "Genuine Undercarriage", "Remanufactured Components", "Hitachi Genuine Engine Oil DH-2").
  - Under NO circumstances may fake SKUs be invented for product line families.
- **Regression Guard**:
  - The test suite explicitly tests that 26 plausible-sounding fake parts (e.g. `main-control-valve`, `swing-motor`, `travel-motor`, `turbocharger`, `track-roller`) are NEVER injected into the parts catalogue.
- **Transformation Target**: Sheet `06_PARTS` and `parts.csv`.

### 3.8 Sheet `07_MACHINE_PART_FITMENT` (Cross-Reference Matrix)
- **Purpose**: Maps machines to compatible parts and attachments, recording compatibility strength.
- **Dimensions**: ~450 rows (1 header row, ~449 data rows), 8 columns.
- **Column Headers**: `fitment_id`, `machine_id`, `part_id`, `fitment_level`, `fitment_evidence`, `verified_by`, `notes`, `source_row`.
- **Primary Key**: `fitment_id`.
- **Foreign Keys**:
  - `machine_id` -> `machines(machine_id)`
  - `part_id` -> `parts(part_id)`
- **Controlled Vocabulary Enforcement**:
  - `fitment_evidence` must be strictly mapped to: `EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`.
  - Raw strings like `"EXACT MODEL"`, `"MODEL/RANGE"`, `"confirmed by dealer forum post"` must be normalized.
- **Conflict Handling**:
  - Any contradictory fitment claims (e.g. compatible in row A, incompatible in row B) must be quarantined in `reports/fitment_conflicts.csv` and flagged with `resolution_status = 'REVIEW_REQUIRED'`.
- **Transformation Target**: Sheet `07_MACHINE_PART_FITMENT` and `machine_part_fitment.csv`.

### 3.9 Sheet `08_SERVICE_CAPABILITIES` (Service Offerings)
- **Purpose**: Defines OEM and dealer service capabilities, preventative maintenance programs, and repairs.
- **Dimensions**: ~22 rows (1 header row, ~21 data rows), 9 columns.
- **Column Headers**: `service_id`, `service_name`, `service_category`, `location_capabilities`, `description`, `sla_hours`, `certification_required`, `source_url`, `marketing_copy`.
- **Primary Key**: `service_id` (`SRV-001`..).
- **Foreign Keys**: None.
- **Controlled Vocabulary**:
  - `location_capabilities`: `FIELD_SERVICE`, `DEALER_WORKSHOP`, `REMOTE`.
- **Noise / URLs**: Marketing slogans, promotional copy, and portal links. Strip completely.
- **Transformation Target**: Sheet `08_SERVICES` and `services.csv`.

### 3.10 Sheet `09_MACHINE_SERVICE_MATRIX` (Service Eligibility)
- **Purpose**: Machine-to-service mapping specifying eligibility for maintenance agreements and warranty services.
- **Dimensions**: ~280 rows (1 header row, ~279 data rows), 7 columns.
- **Column Headers**: `mapping_id`, `machine_id`, `service_id`, `eligibility_tier`, `applicability_evidence`, `mandatory_flag`, `notes`.
- **Primary Key**: `mapping_id`.
- **Foreign Keys**:
  - `machine_id` -> `machines(machine_id)`
  - `service_id` -> `services(service_id)`
- **Integrity Rule**: 100% referential integrity; every mapping must resolve to a valid machine and service.
- **Transformation Target**: Sheet `09_MACHINE_SERVICE` and `machine_service.csv`.

### 3.11 Sheet `10_MAINTENANCE_SCHEDULE` (Maintenance Intervals)
- **Purpose**: Operating hour maintenance schedules (50h, 250h, 500h, 1000h, 2000h) and action checklists.
- **Dimensions**: ~110 rows (1 header row, ~109 data rows), 8 columns.
- **Column Headers**: `maintenance_id`, `machine_id`, `interval_hours`, `interval_months`, `system_code`, `maintenance_action`, `task_description`, `mandatory_flag`.
- **Primary Key**: `maintenance_id`.
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`.
- **Normalization Rules**:
  - `interval_hours` must be parsed to clean numeric integers (50, 250, 500, 1000, 2000).
  - `maintenance_action` normalized to action verbs: `INSPECT`, `REPLACE`, `LUBRICATE`, `ADJUST`, `CLEAN`.
- **Transformation Target**: Sheet `10_MAINTENANCE` and `maintenance.csv`.

### 3.12 Sheet `11_SERVICE_PART_REQUIREMENTS` (Service BOM)
- **Purpose**: Service bill-of-materials connecting maintenance tasks to required replacement parts (filters, fluids, gaskets).
- **Dimensions**: ~185 rows (1 header row, ~184 data rows), 8 columns.
- **Column Headers**: `requirement_id`, `maintenance_id`, `part_id`, `quantity`, `unit_of_measure`, `optional_flag`, `notes`, `source_doc`.
- **Primary Key**: `requirement_id`.
- **Foreign Keys**:
  - `maintenance_id` -> `maintenance(maintenance_id)`
  - `part_id` -> `parts(part_id)`
- **Transformation Target**: Sheet `11_SERVICE_PART_REQUIREMENTS` and `service_part_requirements.csv`.

### 3.13 Sheet `12_MACHINE_DIGITAL_SERVICES` (Telematics Matrix)
- **Purpose**: Connects machines to digital services (ConSite, Global e-Service, remote fleet monitoring).
- **Dimensions**: ~90 rows (1 header row, ~89 data rows), 9 columns.
- **Column Headers**: `digital_service_id`, `machine_id`, `platform_name`, `telematics_hardware`, `monitoring_tier`, `report_frequency`, `applicability_evidence`, `source_url`, `ui_status`.
- **Primary Key**: `digital_service_id`.
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`.
- **Noise / URLs**: External portal login links and promotional claims. Strip URLs to provenance.
- **Transformation Target**: Sheet `12_DIGITAL_SERVICES` and `digital_services.csv`.

### 3.14 Sheet `13_AFTER_SALES_RELATIONSHIPS` (Graph Relationship Register)
- **Purpose**: Comprehensive cross-domain relationship ledger recording graph edges between all entities.
- **Dimensions**: ~620 rows (1 header row, ~619 data rows), 10 columns.
- **Column Headers**: `rel_id`, `source_type`, `source_id`, `relationship_type`, `target_type`, `target_id`, `classification`, `evidence_type`, `confidence`, `notes`.
- **Primary Key**: `rel_id`.
- **Foreign Keys**:
  - `source_id` -> Polymorphic FK resolving to entity matching `source_type`.
  - `target_id` -> Polymorphic FK resolving to entity matching `target_type`.
- **Controlled Vocabulary Enforcement**:
  - `classification` must be strictly mapped to:
    `CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`.
- **Strict Referential Integrity Gate**:
  - All records with `classification == 'CORE'` must have 100% resolvable source and target foreign keys.
  - Zero dangling references permitted in `CORE`.
  - Records with unresolvable endpoints must be classified as `UNRESOLVED` or `INVALID`.
- **Transformation Target**: Sheet `13_RELATIONSHIPS` and `relationships.csv`.

### 3.15 Sheet `14_SOURCE_PROVENANCE` (Provenance Store)
- **Purpose**: Centralized storage for citation metadata, external web URLs, scraping timestamps, and confidence scores.
- **Dimensions**: ~140 rows (1 header row, ~139 data rows), 7 columns.
- **Column Headers**: `provenance_id`, `entity_id`, `source_name`, `source_url`, `extraction_date`, `evidence_type`, `confidence`.
- **Primary Key**: `provenance_id`.
- **Foreign Keys**: `entity_id` -> Resolves to any core entity ID or relationship ID.
- **Permitted URL Store**:
  - This is the **ONLY** core CSV file permitted to contain raw URL strings (`https://...`).
- **Transformation Target**: Sheet `14_PROVENANCE` and `provenance.csv`.

### 3.16 Sheets `15` through `20` (Operational, Reman, Consumables & Documentation)
- **`15_DEALER_NETWORK`**:
  - Dimensions: ~35 rows, 8 cols.
  - Primary Key: `dealer_id`.
  - Disposition: Consolidated into `08_SERVICES` (location capabilities) and service graph metadata.
- **`16_WARRANTY_PROGRAMS`**:
  - Dimensions: ~18 rows, 7 cols.
  - Primary Key: `program_id`.
  - Disposition: Consolidated into `08_SERVICES` and `13_RELATIONSHIPS` (warranty eligibility edges).
- **`17_TELEMATICS_METRICS`**:
  - Dimensions: ~42 rows, 8 cols.
  - Primary Key: `metric_id`.
  - Disposition: Consolidated into `12_DIGITAL_SERVICES` telematics attributes.
- **`18_REMAN_PARTS`**:
  - Dimensions: ~28 rows, 9 cols.
  - Primary Key: `reman_id`.
  - Disposition: Deduplicated and integrated into `06_PARTS` / `parts.csv` as `PRODUCT_LINE_PART_FAMILY`.
- **`19_CONSUMABLES_LUBRICANTS`**:
  - Dimensions: ~32 rows, 10 cols.
  - Primary Key: `consumable_id`.
  - Disposition: Deduplicated and integrated into `06_PARTS` / `parts.csv` (`ORDERABLE_OEM_PART` if OEM number exists, else `PRODUCT_LINE_PART_FAMILY`).
- **`20_OPERATOR_MANUALS`**:
  - Dimensions: ~25 rows, 7 cols.
  - Primary Key: `doc_id`.
  - Disposition: Integrated into documentation provenance in `00_README` and `14_PROVENANCE`.

---

## 4. Notable Data Quality Anomalies, Noise Patterns & Cleaning Edge Cases

Through cross-validation of project constraints, regression tests, and data models, the following 12 critical data quality anomalies and edge cases are documented:

### 4.1 Machine Disambiguation (Catalogue Records vs Model Codes)
- **Observation**: 77 catalogue records (`MC-001` through `MC-077`) represent 85 distinct model codes.
- **Risk**: Merging machines based on base model codes collapses distinct catalogue entries. For example, three distinct demolition excavators in Special Applications share the base model code `ZX250-7`:
  1. `ZX250-7 High Reach Demolition`
  2. `ZX250-7 Multi-Carrier Demolition`
  3. `ZX250-7 Straight Boom Demolition`
- **Cleaning Strategy**: Preserve `machine_id` (`MC-xxx`) as primary key. Retain `models_covered` and `model_count`. Never merge distinct catalogue records.

### 4.2 Sentinel Values in Specifications
- **Observation**: Undisclosed technical values contain literal string sentinels: `"NOT PUBLICLY STATED"`, `"N/A"`, `"-"`, `"TBD"`.
- **Risk**: Naive numeric parsing converts these strings into `0.0`, `-1.0`, or causes runtime parsing exceptions.
- **Cleaning Strategy**: Map all sentinel strings to empty string `""` in CSV files and native Python `None` in Excel cells.

### 4.3 E-Commerce and UI Clutter
- **Observation**: Columns such as `ui_search_rank`, `featured_badge`, `display_priority`, `marketing_copy`, and `shopping_cart_flag` are present in source sheets `03`, `06`, `08`.
- **Risk**: Pollutes the clean graph data foundation with ephemeral website UI state.
- **Cleaning Strategy**: Strip all UI ranking and marketing columns during extraction. Document all removed columns in `neo4j/CLEANUP_REPORT.md`.

### 4.4 URL Leakage Across Core Entities
- **Observation**: Raw URLs (`https://www.hitachicm.com/...` and Scene7 image links) appear embedded in 8 different source sheets.
- **Acceptance Criterion**: Zero full URL strings permitted in core technical entity CSV files (`machines.csv`, `parts.csv`, `attachments.csv`, `services.csv`, `digital_services.csv`, `specifications.csv`).
- **Cleaning Strategy**: Extract and isolate all URLs into `provenance.csv` and sheet `14_PROVENANCE`. Retain only clean local entity identifiers in core files.

### 4.5 Attachment SKU Hallucination Guard
- **Observation**: None of the 13 official attachments (`05_ATTACHMENTS`) possess published OEM part numbers.
- **Regression Guard**: Previous attempts hallucinated synthetic SKUs (e.g. `ATT-BK-001`). The test suite (`partsStore.test.mjs`) strictly forbids this.
- **Cleaning Strategy**: Set `part_number` to empty string `""` / `None` for all attachments. Preserve only verified attributes.

### 4.6 Missing Fitment for Tilt Bucket
- **Observation**: While 12 attachments carry real fitment rows in `07_MACHINE_PART_FITMENT`, `tilt-bucket` has zero fitment records in the source workbook.
- **Cleaning Strategy**: Do NOT invent fitment rows for `tilt-bucket`. Leave fitment empty and handle compatibility as general/unspecified in UI.

### 4.7 Parts Master Classification (`ORDERABLE_OEM_PART` vs `PRODUCT_LINE_PART_FAMILY`)
- **Observation**: Sheet `06_PART_MASTER` conflates individual orderable parts with broad product lines.
- **Cleaning Strategy**:
  - Enforce `record_class`:
    - `ORDERABLE_OEM_PART`: Must have non-empty published OEM part number.
    - `PRODUCT_LINE_PART_FAMILY`: Must have empty part number.
  - Ban invented SKUs.

### 4.8 Remanufactured Components Machine Exclusion
- **Observation**: The Remanufactured Components family (`PT-024`) applies broadly across excavators and wheel loaders (74 of 77 machines), but specifically excludes Rigid Dump Trucks (`MC-054` to `MC-056`).
- **Cleaning Strategy**: Accurately capture category-level fitment for the 74 machines while excluding dump trucks, avoiding blanket "fits all machines" claims.

### 4.9 Controlled Vocabulary Enforcement for Fitment Evidence
- **Observation**: Raw evidence descriptions contain inconsistent phrases (`"exact model"`, `"confirmed by forum"`, `"derived from range"`).
- **Cleaning Strategy**: Normalize strictly to the 5 allowed enum values:
  `EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`.
  Route conflicts to `reports/fitment_conflicts.csv`.

### 4.10 Relationship Classification & Dangling Key Elimination
- **Observation**: Raw sheet `13_AFTER_SALES_RELATIONSHIPS` contains duplicate edges, research links, and unverified mappings with unmapped external IDs.
- **Cleaning Strategy**: Classify every edge into `CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`. Only `CORE` edges with 100% verified endpoints are exported to the active graph. Zero dangling edges in `CORE`.

### 4.11 Consumables and Reman Sheet Duplication
- **Observation**: Sheets 18 and 19 contain rows that overlap with `06_PART_MASTER`.
- **Cleaning Strategy**: Deduplicate by part identity and merge attributes into `06_PARTS` / `parts.csv` during the M2 normalization stage.

### 4.12 Byte-for-Byte Determinism Invariant
- **Observation**: Excel and CSV generation scripts can introduce non-deterministic file output due to set iteration order, fluctuating float formatting, or dynamic timestamps.
- **Cleaning Strategy**:
  - Implement deterministic multi-column sorting on all exports (`ORDER BY id ASC`).
  - Zero dynamic timestamps (`datetime.now()`) in generated markdown reports.
  - Fixed float formatting (`f"{val:.2f}"`).
  - Explicit UTF-8 encoding with LF (`\n`) newlines.

---

## 5. Cross-Sheet Referential Integrity Map

The diagram below illustrates the 100% referential integrity contract across the 14 generated CSV files:

```
                       ┌─────────────────────────┐
                       │     categories.csv      │◄───────┐
                       └───────────┬─────────────┘        │ parent_category_id
                                   │                      │
                                   │ category_id          │
                                   ▼                      │
                       ┌─────────────────────────┐        │
             ┌─────────┤      machines.csv       ├────────┘
             │         └───────────┬─────────────┘
             │                     │
             │ machine_id          │ machine_id
             ▼                     ▼
     ┌───────────────┐     ┌───────────────┐
     │specifications │     │    fitment    │
     └───────────────┘     └───────┬───────┘
                                   │ part_id
                                   ▼
                           ┌───────────────┐
                           │   parts.csv   │
                           └───────▲───────┘
                                   │ part_id
                           ┌───────┴───────┐
                           │ service_part_ │
                           │ requirements  │
                           └───────▲───────┘
                                   │ maintenance_id
                                   ▼
                           ┌───────────────┐
                           │  maintenance  │
                           └───────▲───────┘
                                   │ machine_id
                           ┌───────┴───────┐
                           │machine_service│
                           └───────┬───────┘
                                   │ service_id
                                   ▼
                           ┌───────────────┐
                           │   services    │
                           └───────────────┘
```

---

## 6. Target Dataset Architecture

### 6.1 Clean Excel Workbook (`HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`)
Must contain exactly 17 worksheets (indices 00 to 16):
1. `00_README`: Version metadata, source SHA-256 hash, data dictionary, schema constraints.
2. `01_CATEGORIES`: Clean machine category taxonomy and hierarchy.
3. `02_MACHINES`: Clean machine master catalogue records (`MC-001`..`077`).
4. `03_SPECIFICATIONS`: Technical specifications without UI rankings; nulls preserved.
5. `04_APPLICATIONS`: Canonical industry applications.
6. `05_ATTACHMENTS`: Clean OEM attachments with compatibility levels; zero URLs.
7. `06_PARTS`: Segregated parts (orderable parts vs product-line part families).
8. `07_MACHINE_PART_FITMENT`: Normalized fitment matrix with controlled evidence tags.
9. `08_SERVICES`: Dealer and OEM service capabilities.
10. `09_MACHINE_SERVICE`: Machine-to-service mapping matrix.
11. `10_MAINTENANCE`: Maintenance intervals and action schedule.
12. `11_SERVICE_PART_REQUIREMENTS`: Consumable and replacement part requirements per service.
13. `12_DIGITAL_SERVICES`: Telematics, ConSite, and Global e-Service capabilities.
14. `13_RELATIONSHIPS`: Graph relationship catalog with classification tags.
15. `14_PROVENANCE`: Compact provenance metadata isolated from graph nodes.
16. `15_DATA_QUALITY`: Audit KPIs, transformation metrics, before/after counts.
17. `16_REVIEW_REQUIRED`: Quarantined conflicts, ambiguous fitments, review items.

### 6.2 14 Relational CSV Files (`neo4j/data/`)
1. `categories.csv`
2. `machines.csv`
3. `specifications.csv`
4. `applications.csv`
5. `attachments.csv`
6. `parts.csv`
7. `machine_part_fitment.csv`
8. `services.csv`
9. `machine_service.csv`
10. `maintenance.csv`
11. `service_part_requirements.csv`
12. `digital_services.csv`
13. `relationships.csv`
14. `provenance.csv`

---

## 7. Conclusions & Implementation Recommendations

1. **Workbook Readiness**: All 21 sheets have been systematically audited, cataloged, and mapped to the target 17-sheet Excel workbook and 14 CSV files.
2. **Strict Guardrail Compliance**:
   - The source workbook at `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` has remained strictly untouched.
   - Zero connections or calls to Neo4j Aura have occurred.
3. **Downstream Milestone Decomposition**:
   - **Milestone 1**: Implement `audit_workbook.py` to generate `neo4j/reports/workbook_audit.md`.
   - **Milestone 2**: Implement physical entity normalization (Categories, Machines, Specifications, Applications, Attachments, Parts -> CSVs 1-6).
   - **Milestone 3**: Implement relationship and matrix normalization (Fitment, Services, Maintenance, Digital Services, Relationships, Provenance -> CSVs 7-14).
   - **Milestone 4**: Assemble `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` with all 17 sheets.
   - **Milestone 5**: Generate comprehensive reporting artifacts (`data_quality_report.md`, `CLEANUP_REPORT.md`, `schema_candidates.md`, conflict CSVs) and execute the double-run determinism gate.

---
*Report compiled and verified by explorer_survey_2.*
