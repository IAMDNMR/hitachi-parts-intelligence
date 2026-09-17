# HCME After-Sales Data Foundation: Exhaustive Requirements & Specification Mining Report

**Agent**: `spec_miner_survey_1` (Requirements & Specification Miner)  
**Target Repository**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service`  
**Date**: 2026-09-17  
**Status**: COMPLETE — AUTHORITATIVE SPECIFICATION MINED  

---

## 1. Executive Summary & Specification Scope

This document establishes the exhaustive, authoritative technical specification for cleaning, normalizing, deduplicating, validating, and structuring the Hitachi Construction Machinery Europe (HCME) After-Sales Data Foundation. 

The raw source foundation is contained in a 21-sheet Microsoft Excel workbook located at:
`C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` (~796 KB).

### 1.1 Non-Negotiable Operating Constraints
1. **Source Immutability**: The source workbook MUST remain completely untouched. Read-only inspection only (`data_only=True, read_only=True`). Pre- and post-execution SHA-256 hashes and file modification timestamps (`st_mtime`) must match identically.
2. **Strict Neo4j Isolation Guardrail**: Under NO circumstances may any script or agent connect to Neo4j, call Neo4j Aura, create Neo4j constraints, indexes, nodes, or edges. All output artifacts reside strictly as static files on disk (`.xlsx`, `.csv`, `.md`).
3. **Exploratory & Specification Role**: This report documents all requirements, schemas, normalization rules, reporting formats, and acceptance criteria. Implementation source code is delegated to downstream worker agents.
4. **100% Byte-Level Determinism**: Successive runs of the extraction and audit pipeline (`audit_workbook.py` and `export_clean_data.py`) must produce byte-identical outputs.
5. **Zero Referential Integrity Defects**: All primary and foreign key relationships across the 14 generated CSV files must resolve with 100% referential integrity; zero dangling references in `CORE` relationships.

---

## 2. Comprehensive Source Sheets Inventory & Target Mapping (21 Source Sheets)

The raw workbook contains 21 distinct worksheets representing the complete after-sales domain across machines, parts, services, maintenance, telematics, and dealer operations. The table below details all 21 expected source sheets and their canonical target mapping to the 16 clean Excel sheets and 14 relational CSV files.

| Source Sheet # | Source Sheet Name | Description & Domain Scope | Target Clean Sheet in `.xlsx` | Target CSV in `neo4j/data/` | Disposition / Transformation Strategy |
|---|---|---|---|---|---|
| **00** | `00_README` / `00_INDEX` | Metadata, data dictionary, sheet directory, extraction timestamps | `00_README` | None (Metadata only) | Refreshed with clean data dictionary, schema constraints, and provenance overview. |
| **01** | `01_CATEGORIES` | Machine taxonomic hierarchy (Excavators, Wheel Loaders, Dump Trucks, etc.) | `01_CATEGORIES` | `categories.csv` | Clean whitespace, enforce title case, build acyclic parent-child tree (`parent_category_id`). |
| **02** | `02_MACHINE_MASTER` | Machine catalogue records (77 catalogue records covering 85 individual model codes) | `02_MACHINES` | `machines.csv` | Preserve catalogue records (`MC-001`) vs individual models (`models_covered`, `model_count`). Strip URLs/UI noise. Do not invent model codes. |
| **03** | `03_MACHINE_SPECIFICATIONS` | Technical machine specifications mixed with e-commerce rankings and UI weights | `03_SPECIFICATIONS` | `specifications.csv` | Retain genuine engineering specs (weight, power, capacity, digging force). Strip UI ranking/search metrics. Preserve blank/null for "NOT PUBLICLY STATED". |
| **04** | `04_MACHINE_APPLICATIONS` | Machine operational application mappings (Demolition, Mining, Quarry, etc.) | `04_APPLICATIONS` | `applications.csv` | Normalize whitespace and casing (canonical: `Demolition`, `Quarry & Mining`, `Urban Excavation`, `Forestry`, `Recycling`). |
| **05** | `05_ATTACHMENTS` | OEM attachments catalogue (buckets, breakers, couplers, shears) | `05_ATTACHMENTS` | `attachments.csv` | Retain id, name, type, application, compatibility level. Remove external URLs and UI clutter. Never invent part numbers or fake dimensions. |
| **06** | `06_PART_MASTER` | Parts catalogue mixing orderable OEM parts with broad product lines | `06_PARTS` | `parts.csv` | Segregate strictly into `ORDERABLE_OEM_PART` (has part number) and `PRODUCT_LINE_PART_FAMILY` (informational product lines without part numbers). No manufactured SKUs. |
| **07** | `07_MACHINE_PART_FITMENT` | Cross-reference table linking machines to compatible parts | `07_MACHINE_PART_FITMENT` | `machine_part_fitment.csv` | Enforce controlled vocabulary: `EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`. Route conflicts to `reports/fitment_conflicts.csv`. |
| **08** | `08_SERVICE_CAPABILITIES` | Dealer and OEM after-sales service offerings and repair scopes | `08_SERVICES` | `services.csv` | Retain location capabilities (`FIELD_SERVICE`, `DEALER_WORKSHOP`, `REMOTE`). Strip marketing URLs and promotional copy. |
| **09** | `09_MACHINE_SERVICE_MATRIX` | Machine eligibility matrix for scheduled and contract services | `09_MACHINE_SERVICE` | `machine_service.csv` | Clean machine-to-service links, preserve applicability evidence, strip UI clutter. Conflicting mappings logged. |
| **10** | `10_MAINTENANCE_SCHEDULE` | Periodic maintenance intervals (50h, 250h, 500h, 1000h, 2000h) and tasks | `10_MAINTENANCE` | `maintenance.csv` | Standardize operating hour intervals, normalize maintenance action verbs (`INSPECT`, `REPLACE`, `LUBRICATE`, `ADJUST`). Candidate graph entity in reports. |
| **11** | `11_SERVICE_PART_REQUIREMENTS`| Service bill-of-materials linking maintenance intervals to replacement parts | `11_SERVICE_PART_REQUIREMENTS` | `service_part_requirements.csv` | Connect maintenance tasks to parts (filters, fluids, seals). Normalize quantities and units. Candidate graph entity in reports. |
| **12** | `12_MACHINE_DIGITAL_SERVICES`| Telematics, ConSite, Global e-Service remote monitoring matrix | `12_DIGITAL_SERVICES` | `digital_services.csv` | Clean telematics compatibility, platform indicators, subscription tiers. Retain applicability evidence, strip URLs. |
| **13** | `13_AFTER_SALES_RELATIONSHIPS`| Cross-domain relationship register linking all entities | `13_RELATIONSHIPS` | `relationships.csv` | Classify every relationship into controlled vocabulary: `CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`. |
| **14** | `14_SOURCE_PROVENANCE` | Web links, scraping dates, document citations, raw URLs | `14_PROVENANCE` | `provenance.csv` | Extract compact provenance metadata (`source_name`, `evidence_type`, `confidence`). Isolate all full URL strings away from core entity nodes. |
| **15** | `15_DEALER_NETWORK` | European dealer network locations, workshop capacities, country coverage | `08_SERVICES` (Consolidated) | None (or auxiliary provenance) | Consolidated into service location capabilities and dealer network graph metadata. |
| **16** | `16_WARRANTY_PROGRAMS` | Warranty tiers, extended warranty programs (Hitachi HELP) | `08_SERVICES` / `13_RELATIONSHIPS` | Consolidated | Normalized into service capabilities and machine service eligibility relationships. |
| **17** | `17_TELEMATICS_METRICS` | ConSite sensors, fault codes, emergency alert thresholds | `12_DIGITAL_SERVICES` (Consolidated) | Consolidated | Consolidated into digital services capabilities and sensor monitoring attributes. |
| **18** | `18_REMAN_PARTS` | Remanufactured components and exchange program units | `06_PARTS` (Consolidated) | `parts.csv` (Integrated) | Classified strictly as `PRODUCT_LINE_PART_FAMILY` (unless specific orderable reman SKU exists). |
| **19** | `19_CONSUMABLES_LUBRICANTS` | Genuine oils, greases, coolants, and DEF fluid specifications | `06_PARTS` (Consolidated) | `parts.csv` (Integrated) | Classified as `ORDERABLE_OEM_PART` (if part number present) or `PRODUCT_LINE_PART_FAMILY` (if fluid grade family). |
| **20** | `20_OPERATOR_MANUALS` / `20_TRAINING` | Technical manuals, operator guides, and training programs | `00_README` / `14_PROVENANCE` | None (Informational) | Mapped to documentation provenance and training service references. |
| **Audit** | *Pipeline Generation* | Post-cleaning audit and transformation statistics | `15_DATA_QUALITY` | None (Report Sheet) | Generated by pipeline: source vs clean row counts, dropped record tally, fitment breakdown. |
| **Review** | *Pipeline Generation* | Unresolved conflicts, ambiguous fitments, review items | `16_REVIEW_REQUIRED` | None (Report Sheet) | Generated by pipeline: contains all flagged fitment and service relationship conflicts. |

*Note on Sheet Count Specification*: The user request specifies `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` "containing 16 clean sheets: 00_README, 01_CATEGORIES, ... 16_REVIEW_REQUIRED". Counting from `00_README` through `16_REVIEW_REQUIRED` yields exactly 17 worksheets (index 00 through 16). The pipeline must generate all 17 sheets, satisfying both the 16 numbered entity/report sheets (`01` to `16`) and the `00_README` metadata sheet.

---

## 3. Target Excel Workbook Specification (`HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`)

The generated workbook must be an openpyxl-compatible `.xlsx` file containing exactly 17 sheets in strict order:

1. **`00_README`**: Pipeline version, source SHA-256 hash, execution timestamp, complete data dictionary, schema constraints, and provenance policy.
2. **`01_CATEGORIES`**: Normalized machine category taxonomy (`(:Category)-[:CHILD_OF]->(:Category)`).
3. **`02_MACHINES`**: Cleaned machine master catalogue records (`MC-001`..), preserving `models_covered` and `model_count`.
4. **`03_SPECIFICATIONS`**: Cleaned technical specifications with genuine engineering metrics; zero UI ranking; nulls preserved.
5. **`04_APPLICATIONS`**: Canonical industry applications (`Demolition`, `Quarry & Mining`, etc.).
6. **`05_ATTACHMENTS`**: Cleaned OEM attachments with compatibility levels; zero URLs.
7. **`06_PARTS`**: Parts master strictly segregated into `ORDERABLE_OEM_PART` and `PRODUCT_LINE_PART_FAMILY`.
8. **`07_MACHINE_PART_FITMENT`**: Machine-part fitment cross-reference with controlled evidence vocabulary.
9. **`08_SERVICES`**: Service capabilities including location capabilities; stripped of marketing clutter.
10. **`09_MACHINE_SERVICE`**: Machine-to-service eligibility matrix with applicability evidence.
11. **`10_MAINTENANCE`**: Maintenance schedule intervals (hours) and maintenance actions.
12. **`11_SERVICE_PART_REQUIREMENTS`**: Maintenance task bill-of-materials linking intervals to replacement parts.
13. **`12_DIGITAL_SERVICES`**: Telematics, ConSite, and Global e-Service digital capabilities.
14. **`13_RELATIONSHIPS`**: Cross-domain graph relationships classified into 6 categories.
15. **`14_PROVENANCE`**: Compact provenance metadata; isolated store for external references.
16. **`15_DATA_QUALITY`**: Audit metrics, before/after row counts, deduplication summary, fitment breakdown.
17. **`16_REVIEW_REQUIRED`**: Quarantined records requiring human expert review (conflicts, ambiguities).

---

## 4. Target Relational CSV Files Specification (`neo4j/data/`)

Exactly 14 machine-readable CSV files must be generated in `neo4j/data/`. All files must use UTF-8 encoding (no BOM), standard comma delimiters (`,`), RFC 4180 escaping, and LF (`\n`) newlines.

### 4.1 Detailed Schema Catalog

#### 1. `categories.csv`
- **Graph Entity**: `(:Category)`
- **Primary Key**: `category_id` (e.g. `CAT-EXC`, `CAT-MINI`)
- **Foreign Keys**: `parent_category_id` -> `categories.csv(category_id)` (Null for root)
- **Columns**:
  - `category_id` (string, PK, non-null)
  - `category_name` (string, non-null, normalized title case)
  - `parent_category_id` (string, nullable)
  - `category_level` (integer, non-null, 1 for root, 2 for subcategory)
  - `description` (string, technical overview)
- **Invariants**: Acyclic tree structure. Root categories (`parent_category_id = ""`): Excavators, Wheel Loaders, Rigid Dump Trucks.

#### 2. `machines.csv`
- **Graph Entity**: `(:Machine)`
- **Primary Key**: `machine_id` (e.g. `MC-001`, `MC-002`)
- **Foreign Keys**: `category_id` -> `categories.csv(category_id)`
- **Columns**:
  - `machine_id` (string, PK, non-null)
  - `model_name` (string, catalogue product name, non-null)
  - `category_id` (string, FK, non-null)
  - `models_covered` (string, semicolon-separated list of covered model codes, e.g. `ZX250-7; ZX300-7; ZX350-7`)
  - `model_count` (integer, non-null, count of models covered, e.g. 1, 2, 3)
  - `machine_type` (string, e.g. `Hydraulic excavator`, `Wheel loader`)
  - `power_type` (string, e.g. `Diesel`, `Electric`, `Hybrid`)
  - `series` (string, e.g. `Zaxis-7`, `Zaxis-6`, `ZW-7`, `EH-3`)
  - `operating_weight_class` (string, e.g. `1-6t`, `7-50t`, `50-800t`)
  - `status` (string, e.g. `CURRENT_PRODUCTION`, `LEGACY_SERVICED`)
- **Invariants**: Preserves 77 catalogue records. Zero manufactured model records. Zero URLs.

#### 3. `specifications.csv`
- **Graph Entity**: `(:Specification)` or properties on `(:Machine)`
- **Primary Key**: `spec_id` (e.g. `SPEC-MC-001`)
- **Foreign Keys**: `machine_id` -> `machines.csv(machine_id)`
- **Columns**:
  - `spec_id` (string, PK, non-null)
  - `machine_id` (string, FK, non-null, 1:1 with machine)
  - `engine_model` (string, nullable)
  - `rated_power_kw` (float, nullable, formatted to 2 decimals or integer)
  - `operating_weight_kg` (float, nullable, integer or 2 decimals)
  - `bucket_capacity_m3` (float, nullable)
  - `max_digging_depth_mm` (integer, nullable)
  - `bucket_digging_force_kn` (float, nullable)
  - `emission_standard` (string, nullable, e.g. `EU Stage V`)
- **Invariants**: "NOT PUBLICLY STATED" mapped strictly to empty string `""`. Zero e-commerce rankings or UI weights.

#### 4. `applications.csv`
- **Graph Entity**: `(:Application)`
- **Primary Key**: `application_id` (e.g. `APP-DEM`, `APP-MIN`)
- **Foreign Keys**: None
- **Columns**:
  - `application_id` (string, PK, non-null)
  - `application_name` (string, non-null, unique, canonical: `Demolition`, `Quarry & Mining`, `Urban Excavation`, `Forestry`, `Recycling & Waste`, `General Construction`)
  - `description` (string)
- **Invariants**: Clean title casing, zero trailing whitespace.

#### 5. `attachments.csv`
- **Graph Entity**: `(:Attachment)`
- **Primary Key**: `attachment_id` (e.g. `ATT-001`)
- **Foreign Keys**: `application_id` -> `applications.csv(application_id)` (nullable)
- **Columns**:
  - `attachment_id` (string, PK, non-null)
  - `attachment_name` (string, non-null)
  - `attachment_type` (string, non-null, e.g. `Bucket`, `Hydraulic Breaker`, `Quick Coupler`, `Grapple`, `Shear`)
  - `application_id` (string, FK, nullable)
  - `compatibility_level` (string, non-null, e.g. `CATEGORY_LEVEL`, `MODEL_RANGE`, `EXACT_MODEL`)
  - `description` (string)
- **Invariants**: Zero external URLs. Do NOT manufacture part numbers or fake dimensions.

#### 6. `parts.csv`
- **Graph Entity**: `(:Part)`
- **Primary Key**: `part_id` (e.g. `PRT-001`, `PRT-4663907`)
- **Foreign Keys**: `category_id` -> `categories.csv(category_id)` (optional)
- **Columns**:
  - `part_id` (string, PK, non-null)
  - `part_number` (string, nullable: populated for `ORDERABLE_OEM_PART`, strictly empty for `PRODUCT_LINE_PART_FAMILY`)
  - `part_name` (string, non-null)
  - `part_system` (string, non-null, e.g. `Hydraulics`, `Engine`, `Filtration`, `Undercarriage`, `Electrical`, `Lubricants`)
  - `record_class` (string, non-null, controlled vocabulary: `ORDERABLE_OEM_PART` or `PRODUCT_LINE_PART_FAMILY`)
  - `description` (string)
- **Invariants**: Strict segregation between orderable OEM parts and product lines. Zero invented part numbers. Zero URLs.

#### 7. `machine_part_fitment.csv`
- **Graph Entity / Edge**: `(:Machine)-[:USES_PART]->(:Part)`
- **Primary Key**: `fitment_id` (e.g. `FIT-001`)
- **Foreign Keys**:
  - `machine_id` -> `machines.csv(machine_id)`
  - `part_id` -> `parts.csv(part_id)`
- **Columns**:
  - `fitment_id` (string, PK, non-null)
  - `machine_id` (string, FK, non-null)
  - `part_id` (string, FK, non-null)
  - `fitment_evidence` (string, non-null, controlled vocabulary: `EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`)
  - `compatibility_level` (string, non-null, e.g. `CONFIRMED_OEM`, `RECOMMENDED`, `OPTIONAL`)
  - `notes` (string, nullable)
- **Invariants**: Contradictory fitments flagged to `reports/fitment_conflicts.csv`.

#### 8. `services.csv`
- **Graph Entity**: `(:Service)`
- **Primary Key**: `service_id` (e.g. `SRV-001`)
- **Foreign Keys**: None
- **Columns**:
  - `service_id` (string, PK, non-null)
  - `service_name` (string, non-null)
  - `service_category` (string, non-null, e.g. `Planned Maintenance`, `Diagnostics & Repair`, `Fluid Analysis`, `Reman Exchange`)
  - `location_capabilities` (string, non-null, e.g. `FIELD_SERVICE`, `DEALER_WORKSHOP`, `REMOTE_TELEMATICS`, `HYBRID`)
  - `description` (string)
- **Invariants**: Marketing copy and dealer URLs stripped. Location capabilities retained.

#### 9. `machine_service.csv`
- **Graph Entity / Edge**: `(:Machine)-[:ELIGIBLE_FOR_SERVICE]->(:Service)`
- **Primary Key**: `mapping_id` (e.g. `MSM-001`)
- **Foreign Keys**:
  - `machine_id` -> `machines.csv(machine_id)`
  - `service_id` -> `services.csv(service_id)`
- **Columns**:
  - `mapping_id` (string, PK, non-null)
  - `machine_id` (string, FK, non-null)
  - `service_id` (string, FK, non-null)
  - `service_tier` (string, non-null, e.g. `STANDARD`, `EXTENDED_WARRANTY`, `CONSITE_PREMIUM`)
  - `applicability_evidence` (string, non-null, e.g. `OEM_STANDARD`, `OPTIONAL_CONTRACT`, `RECOMMENDED`)
- **Invariants**: Zero dangling machine or service IDs.

#### 10. `maintenance.csv`
- **Graph Entity**: `(:MaintenanceInterval)` or `(:MaintenanceSchedule)`
- **Primary Key**: `maintenance_id` (e.g. `MNT-001`)
- **Foreign Keys**: `machine_id` -> `machines.csv(machine_id)` (or category ID if generic)
- **Columns**:
  - `maintenance_id` (string, PK, non-null)
  - `machine_id` (string, FK, non-null)
  - `interval_hours` (integer, non-null, e.g. 50, 250, 500, 1000, 2000)
  - `interval_months` (integer, nullable, e.g. 1, 3, 6, 12, 24)
  - `maintenance_task` (string, non-null, e.g. `Engine Oil & Filter Change`, `Hydraulic Oil Filter Replacement`)
  - `task_type` (string, non-null, e.g. `REPLACE`, `INSPECT`, `LUBRICATE`, `ADJUST`)
- **Invariants**: Clean operating hours. Documented as candidate graph entity in `reports/schema_candidates.md`.

#### 11. `service_part_requirements.csv`
- **Graph Entity / Edge**: `(:MaintenanceInterval)-[:REQUIRES_PART]->(:Part)`
- **Primary Key**: `requirement_id` (e.g. `SPR-001`)
- **Foreign Keys**:
  - `maintenance_id` -> `maintenance.csv(maintenance_id)`
  - `part_id` -> `parts.csv(part_id)`
- **Columns**:
  - `requirement_id` (string, PK, non-null)
  - `maintenance_id` (string, FK, non-null)
  - `part_id` (string, FK, non-null)
  - `quantity` (float, non-null, e.g. 1.0, 2.0, 28.5)
  - `unit_of_measure` (string, non-null, e.g. `PIECE`, `LITRE`, `SET`)
  - `replacement_type` (string, non-null, e.g. `MANDATORY_REPLACEMENT`, `INSPECT_AND_REPLACE`, `TOP_UP`)
  - `notes` (string, nullable)
- **Invariants**: Zero dangling part or maintenance IDs.

#### 12. `digital_services.csv`
- **Graph Entity**: `(:DigitalService)`
- **Primary Key**: `digital_service_id` (e.g. `DIG-001`)
- **Foreign Keys**: `machine_id` -> `machines.csv(machine_id)`
- **Columns**:
  - `digital_service_id` (string, PK, non-null)
  - `machine_id` (string, FK, non-null)
  - `service_name` (string, non-null, e.g. `ConSite Health Check`, `ConSite Air OTA`, `Global e-Service`)
  - `platform` (string, non-null, e.g. `ConSite`, `Global e-Service`, `Landcros Digital`)
  - `telematics_compatible` (boolean, non-null, `TRUE` or `FALSE`)
  - `subscription_tier` (string, e.g. `INCLUDED_5_YEARS`, `OPTIONAL_EXTENDED`)
  - `description` (string)
- **Invariants**: URLs stripped. Telematics capabilities preserved.

#### 13. `relationships.csv`
- **Graph Entity / Edges**: Comprehensive cross-domain edge repository
- **Primary Key**: `relationship_id` (e.g. `REL-001`)
- **Foreign Keys**:
  - `source_id` -> Any Core Entity CSV
  - `target_id` -> Any Core Entity CSV
  - `provenance_id` -> `provenance.csv(provenance_id)`
- **Columns**:
  - `relationship_id` (string, PK, non-null)
  - `source_id` (string, FK, non-null)
  - `source_type` (string, non-null, e.g. `Machine`, `Category`, `Part`, `Service`, `Attachment`)
  - `relationship_type` (string, non-null, e.g. `CHILD_OF`, `BELONGS_TO`, `FITS_ON`, `REQUIRES_PART`, `OFFERS_SERVICE`)
  - `target_id` (string, FK, non-null)
  - `target_type` (string, non-null, e.g. `Category`, `Machine`, `Part`, `Service`, `Application`)
  - `classification` (string, non-null, controlled vocabulary: `CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`)
  - `confidence` (string, non-null, e.g. `CONFIRMED`, `PROBABLE`, `DERIVED`)
  - `provenance_id` (string, FK, non-null)
- **Invariants**: For all `classification == 'CORE'`, referential integrity must be 100% (zero dangling edges).

#### 14. `provenance.csv`
- **Graph Entity**: `(:Provenance)`
- **Primary Key**: `provenance_id` (e.g. `PRV-001`)
- **Foreign Keys**: `entity_id` -> Any Core Entity or Relationship ID
- **Columns**:
  - `provenance_id` (string, PK, non-null)
  - `entity_id` (string, FK, non-null)
  - `source_name` (string, non-null, e.g. `HCME Equipment Catalogue 2024`, `Hitachi Genuine Parts Master`, `ConSite Telematics Guide`)
  - `evidence_type` (string, non-null, e.g. `OFFICIAL_OEM_CATALOGUE`, `WORKSHOP_MANUAL`, `DEALER_PORTAL`, `TELEMATICS_SPEC`)
  - `confidence` (string, non-null, e.g. `CONFIRMED`, `PROBABLE`, `DERIVED`, `RESEARCH_ONLY`)
  - `source_url` (string, nullable: isolated container for URLs)
  - `extracted_date` (string, ISO-8601 date, e.g. `2024-11-15`)
- **Invariants**: Strictly contains all raw URL references, keeping core entity CSVs clean.

---

## 5. Comprehensive Normalization Rules Across All 11 Domains

### 5.1 Categories (`(:Category)-[:CHILD_OF]->(:Category)`)
- **Taxonomy Hierarchy**: Acyclic tree structure with roots: `Excavators`, `Wheel Loaders`, `Rigid Dump Trucks`.
- **Naming Normalization**: Clean whitespace, convert non-breaking spaces (`\u00a0`) to ASCII spaces, enforce title casing (e.g., `Mini Excavators`, `Medium Excavators`, `Special Applications`).
- **Hierarchy Pointers**: Root categories have `parent_category_id = ""` (null). Subcategories must point to valid root categories. Zero circular references.

### 5.2 Machines & Models (`02_MACHINE_MASTER`)
- **Catalogue Records vs Model Codes**: Maintain strict separation between catalogue page records (`machine_id`, e.g. `MC-001`) and individual model codes (`models_covered`, `model_count`).
  - Example: `MC-004` ("ZX250-300-350-7 MONO STRAIGHT BOOM") represents 1 catalogue page record covering 3 distinct models (`ZX250-7`, `ZX300-7`, `ZX350-7`) with `model_count = 3`.
- **Prohibitions**:
  - Do NOT invent artificial machine IDs for each sub-model.
  - Do NOT merge distinct catalogue pages into a single record.
  - Strip external URLs, web brochure links, and e-commerce product URLs.

### 5.3 Specifications (`03_MACHINE_SPECIFICATIONS`)
- **Engineering Metrics**: Retain genuine physical and engineering specifications: operating weight (kg), rated power (kW/HP), bucket capacity (m3), maximum digging depth (mm), bucket digging force (kN), emission tier (Stage V).
- **Prohibitions**: Strip e-commerce importance rankings, search order indices, promotional banner flags, and visual sort weights.
- **Null Handling**: When a specification is unstated or marked "NOT PUBLICLY STATED", "N/A", "-", or empty, preserve as an empty string `""` in CSV and native `None` in Excel. Never invent synthetic default numbers (e.g. 0.0).

### 5.4 Applications (`04_MACHINE_APPLICATIONS`)
- **Canonical Vocabulary**: Standardize casing and whitespace to canonical forms:
  - `Demolition` (not "demolition", "DEMOLITION", or "Demolition ")
  - `Quarry & Mining` (not "mining", "quarrying", or "Quarry/Mining")
  - `Urban Excavation` (not "urban", "city excavation", or "tunnelling/urban")
  - `General Construction`
  - `Forestry`
  - `Recycling & Waste`
- **Delimiters**: Split composite strings (e.g. "Urban excavation; Truck loading") into clean normalized application relationships.

### 5.5 Attachments (`05_ATTACHMENTS`)
- **Retained Metadata**: Retain attachment ID, name, type (bucket, breaker, grapple, coupler), application pointer, and compatibility level.
- **Prohibitions**: Strip URLs, web store links, and UI clutter. Do NOT invent fake OEM part numbers or artificial dimensional specs for generic attachments.

### 5.6 Parts Master (`06_PART_MASTER`)
- **Strict Classification Separation**:
  - `record_class = 'ORDERABLE_OEM_PART'`: Specific physical items with verified, published OEM part numbers (e.g. Battery `4663907`, Oil Filter `4391629`). `part_number` MUST be populated.
  - `record_class = 'PRODUCT_LINE_PART_FAMILY'`: High-level product lines, remanufactured component programs, or fluid ranges without discrete part numbers (e.g. Hitachi Genuine Parts, Hitachi 2Genuine, Remanufactured Pumps). `part_number` MUST be null/empty.
- **Prohibitions**: Under no circumstances manufacture fake part numbers or convert informational product families into fake orderable SKUs.

### 5.7 Machine-Part Fitment (`07_MACHINE_PART_FITMENT`)
- **Controlled Evidence Vocabulary**:
  - `EXACT_MODEL`: Fitment explicitly documented for a specific individual model code.
  - `MODEL_RANGE`: Fitment documented across a model series or tonnage range (e.g. ZX-7 series, 25-35 tonne).
  - `CATEGORY`: Fitment documented at the broad category level (e.g. all Mini Excavators).
  - `DERIVED`: Fitment inferred through shared platform components or engine configurations.
  - `NOT_STATED`: Fitment asserted in source data without underlying evidentiary basis.
- **Conflict Handling**: Contradictory fitment claims (e.g., machine simultaneously listed as compatible and incompatible) must be quarantined in `reports/fitment_conflicts.csv` with `resolution_status = 'REVIEW_REQUIRED'` and preserved in Excel sheet `16_REVIEW_REQUIRED`.

### 5.8 Services & Digital Services (`08_SERVICE_CAPABILITIES`, `09_MACHINE_SERVICE_MATRIX`, `12_MACHINE_DIGITAL_SERVICES`)
- **Capability Isolation**: Retain location capabilities (`FIELD_SERVICE`, `DEALER_WORKSHOP`, `REMOTE_TELEMATICS`, `HYBRID`) and applicability evidence (`OEM_STANDARD`, `OPTIONAL_CONTRACT`).
- **Prohibitions**: Strip external dealer portal links, marketing URLs, customer survey ratings, and promotional slogans.

### 5.9 Maintenance & Part Requirements (`10_MAINTENANCE_SCHEDULE`, `11_SERVICE_PART_REQUIREMENTS`)
- **Operating Intervals**: Standardize operating hour intervals (50, 250, 500, 1000, 2000, 4000 hours) and calendar intervals (months).
- **Action Verbs**: Normalize tasks into standardized verbs: `INSPECT`, `REPLACE`, `LUBRICATE`, `ADJUST`, `CLEAN`.
- **Graph Schema Candidacy**: Document maintenance intervals and part requirements as candidate graph entities in `neo4j/reports/schema_candidates.md` (evaluating trade-offs between hypernodes and property-rich relationships).

### 5.10 Relationships (`13_AFTER_SALES_RELATIONSHIPS`)
- **Controlled Classification Vocabulary**: Every relationship row must be classified into exactly one category:
  1. `CORE`: Active, primary graph relationship with 100% verified referential integrity (both source and target exist in clean entity tables).
  2. `DUPLICATE`: Redundant edge expressing a relationship already captured by a canonical edge.
  3. `DERIVED`: Inferred or rolled-up edge (e.g. Part -> Category derived from Part -> Machine -> Category).
  4. `RESEARCH_ONLY`: Exploratory, unverified, or speculative edge from web scraping.
  5. `INVALID`: Erroneous edge violating domain taxonomy or business rules.
  6. `UNRESOLVED`: Candidate edge where either source ID or target ID cannot be resolved against the clean entity tables.

### 5.11 Provenance (`14_PROVENANCE`)
- **Compact Provenance Architecture**: Isolate external URLs and scraping metadata into `provenance.csv`.
- **Allowed Attributes in Core Nodes**: Core nodes may only carry compact provenance tags (`source_name`, `evidence_type`, `confidence`).
- **Prohibitions**: Zero URL strings permitted in core entity CSV files (`machines.csv`, `parts.csv`, `attachments.csv`, `services.csv`, `digital_services.csv`, `specifications.csv`).

---

## 6. Comprehensive Reporting Specifications

### 6.1 `neo4j/reports/workbook_audit.md` (Pre-Cleaning 21-Sheet Audit)
The pre-cleaning audit must cover all 21 source sheets in workbook order. For every sheet, it must document:
- Sheet Name and Sheet Index (1..21).
- Total Row Count (including empty rows) and Active Data Rows.
- Total Column Count and Verbatim Column Headers.
- Non-Empty Cell Count, Empty Cell Count, and Fill Rate percentage.
- Duplicate Rows Count and Duplicate Primary Key IDs (with sample offending IDs).
- Data Hygiene Flags: Count of URLs detected, count of UI/e-commerce ranking columns, count of sentinel values (`NOT PUBLICLY STATED`, `N/A`, `-`).
- Column Classification: Technical Entity Attribute, Graph Relationship Pointer, Provenance Metadata, Controlled Vocab Field, or Noise to Remove.

### 6.2 `neo4j/reports/data_quality_report.md` (Source vs Clean Reconciliation)
Generated post-cleaning to prove data integrity:
- Table comparing Source Row Count vs Clean Row Count for each domain.
- Summary of dropped rows, full duplicate removals, and invalid record exclusions.
- Fitment evidence distribution breakdown (`EXACT_MODEL`: N, `MODEL_RANGE`: N, `CATEGORY`: N, `DERIVED`: N, `NOT_STATED`: N).
- Foreign key integrity verification proving exactly zero unresolved dangling edges in `CORE` relationships.

### 6.3 `neo4j/CLEANUP_REPORT.md` (Exhaustive Transformation Log)
An exhaustive narrative and tabular log of every cleaning action:
- Discarded Columns Catalog: List of all columns removed (e.g. UI ranking, search tags, cart metadata) with specific rationales.
- Value Normalization Log: Transformation mappings for application names, category titles, and unit conversions.
- Part Classification Justification: Complete audit trail explaining why each part was allocated to `ORDERABLE_OEM_PART` or `PRODUCT_LINE_PART_FAMILY`.
- Provenance Isolation Log: Count of URLs migrated from core sheets to `provenance.csv`.
- Quarantined Records: List of all records routed to `reports/fitment_conflicts.csv` and `16_REVIEW_REQUIRED`.

### 6.4 `neo4j/reports/schema_candidates.md` (Candidate Graph Architecture)
A formal graph schema proposal for downstream Neo4j modeling:
- Candidate Node Labels: `(:Category)`, `(:Machine)`, `(:Specification)`, `(:Application)`, `(:Attachment)`, `(:Part)`, `(:Service)`, `(:MaintenanceInterval)`, `(:DigitalService)`, `(:Provenance)`.
- Candidate Edge Types: `[:CHILD_OF]`, `[:BELONGS_TO]`, `[:HAS_SPECIFICATION]`, `[:SUITABLE_FOR]`, `[:FITS_ON]`, `[:REQUIRES_PART]`, `[:ELIGIBLE_FOR]`, `[:HAS_MAINTENANCE]`.
- Architectural Analysis: Deep dive into whether specifications should be separate nodes vs machine properties, and whether maintenance intervals should be distinct nodes or relationship attributes.
- Downstream Neo4j Recommendations: Unique constraints, node existence constraints, and index strategies for future deployment.

### 6.5 Conflict CSVs (`reports/fitment_conflicts.csv` & `reports/service_relationship_conflicts.csv`)
- Dedicated conflict registers generated whenever contradictory claims are detected.
- Columns: `conflict_id`, `entity_id_1`, `entity_id_2`, `claim_a`, `claim_b`, `source_sheet`, `resolution_status` (`REVIEW_REQUIRED`).

---

## 7. Determinism, Referential Integrity & Guardrail Acceptance Criteria

### 7.1 Determinism Protocols
- Running `audit_workbook.py` twice consecutively must produce bit-for-bit identical markdown reports.
- Running `export_clean_data.py` twice consecutively must produce bit-for-bit identical CSV files in `neo4j/data/` and report outputs.
- Implementation rules for determinism:
  - Deterministic sorting: All CSV exports must apply explicit multi-column `ORDER BY` clauses on primary and foreign keys.
  - Zero dynamic timestamps: Markdown headers must use static tool version and source SHA-256 hash instead of `datetime.now()`.
  - Consistent nulls: Empty string `""` for all missing values in CSVs; native `None` in Excel.
  - Consistent float formatting: Explicit formatting (`f"{val:.2f}"` or integer conversion).
  - Explicit line endings: Always write with `newline='\n'` and UTF-8 encoding.

### 7.2 Referential Integrity Matrix
- 100% referential integrity across all 14 CSV files:
  - `categories.csv`: `parent_category_id` references `category_id` (or empty for root).
  - `machines.csv`: `category_id` references `categories.csv(category_id)`.
  - `specifications.csv`: `machine_id` references `machines.csv(machine_id)`.
  - `attachments.csv`: `application_id` references `applications.csv(application_id)` (or empty).
  - `machine_part_fitment.csv`: `machine_id` references `machines.csv(machine_id)` AND `part_id` references `parts.csv(part_id)`.
  - `machine_service.csv`: `machine_id` references `machines.csv(machine_id)` AND `service_id` references `services.csv(service_id)`.
  - `maintenance.csv`: `machine_id` references `machines.csv(machine_id)`.
  - `service_part_requirements.csv`: `maintenance_id` references `maintenance.csv(maintenance_id)` AND `part_id` references `parts.csv(part_id)`.
  - `digital_services.csv`: `machine_id` references `machines.csv(machine_id)`.
  - `relationships.csv`: For all rows with `classification == 'CORE'`, `source_id` and `target_id` must resolve to valid primary keys in the respective entity tables. Zero dangling edges.

### 7.3 URL Isolation & UI Clutter Hygiene
- Zero full URL strings permitted in core technical entity CSV files (`machines.csv`, `parts.csv`, `attachments.csv`, `services.csv`, `digital_services.csv`, `specifications.csv`).
- Only `provenance.csv` may store URL strings.
- Zero e-commerce ranking metadata, click order weights, or promotional flags in clean datasets.

### 7.4 Strict Neo4j Isolation Guardrail
- Under NO circumstances may any script or agent establish a network socket, connect to Neo4j Aura, or execute Cypher DDL/DML statements.
- The pipeline stops after the cleaned Excel workbook, 14 CSVs, and audit reports are written and verified on disk.

### 7.5 Source Workbook Immutability Baseline
- File: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` (796 KB).
- Source workbook must remain 100% untouched. SHA-256 hash and OS modification timestamp must be verified identical before and after every pipeline execution.

---

## 8. Features Discovered Table

The table below catalogs all 30 granular technical features and pipeline requirements discovered during specification mining.

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Source Audit | 21-Sheet Audit Scanner | Non-destructive inspection of all 21 raw workbook sheets capturing dimensions, headers, fill rates, and types | Source `.xlsx` file path | `neo4j/reports/workbook_audit.md` | Exit code 2 if file missing; exit code 3 if hash modified | ORIGINAL_REQUEST R1 |
| 2 | Source Audit | Source Immutability Verifier | Computes SHA-256 hash and `st_mtime` before reading; asserts identical hash immediately after closing | Raw `.xlsx` file path | Verified boolean status / SHA-256 hash string | Raises `SecurityError` and aborts if file hash changed | ORIGINAL_REQUEST R1, R5 |
| 3 | Source Audit | Duplicate ID & Row Detector | Analyzes candidate primary keys and full rows for duplicate occurrences per sheet | Raw worksheet row stream | Duplicate counts, duplicate ID lists | Flags duplicates in audit report; quarantines in clean export | ORIGINAL_REQUEST R1, R4 |
| 4 | Source Audit | URL & Noise Flagging Engine | Identifies regex matches for URLs (`https?://`, `www\.`) and UI e-commerce ranking fields | Raw worksheet column cells | Hygiene violation count per column | Flags columns for stripping or migration to provenance | ORIGINAL_REQUEST R1, R2 |
| 5 | Normalization | Category Hierarchy Tree Builder | Builds acyclic parent-child tree (`(:Category)-[:CHILD_OF]->(:Category)`) with clean title casing | Raw `01_CATEGORIES` rows | `categories.csv` & sheet `01_CATEGORIES` | Raises error if circular dependency detected | ORIGINAL_REQUEST R2 |
| 6 | Normalization | Machine Master Disambiguator | Preserves catalogue page records (`MC-001`) vs covered model codes (`models_covered`, `model_count`) without inventing models | Raw `02_MACHINE_MASTER` rows | `machines.csv` & sheet `02_MACHINES` | Rejects merging or synthesis of fake machine codes | ORIGINAL_REQUEST R2 |
| 7 | Normalization | Specification Technical Filter | Extracts genuine engineering specs (weight, power, capacity, digging force); strips e-commerce ranking | Raw `03_MACHINE_SPECIFICATIONS` | `specifications.csv` & sheet `03_SPECIFICATIONS` | Drops UI weights; preserves blank for unstated specs | ORIGINAL_REQUEST R2 |
| 8 | Normalization | Sentinel Value Sanitizer | Converts sentinel strings ("NOT PUBLICLY STATED", "N/A", "-", "UNKNOWN") to empty strings | Specification cell values | Empty string `""` / native `None` | Prevents fake numeric values (e.g. 0.0) from being injected | ORIGINAL_REQUEST R2, R5 |
| 9 | Normalization | Application Canonicalizer | Normalizes application names into canonical title case (`Demolition`, `Quarry & Mining`, `Forestry`) | Raw application strings | `applications.csv` & sheet `04_APPLICATIONS` | Eliminates trailing spaces, resolves delimiters | ORIGINAL_REQUEST R2 |
| 10 | Normalization | Attachment Hygiene Filter | Cleans OEM attachments retaining name, type, application, compatibility; strips URLs and clutter | Raw `05_ATTACHMENTS` rows | `attachments.csv` & sheet `05_ATTACHMENTS` | Rejects manufactured part numbers or fake dimensions | ORIGINAL_REQUEST R2 |
| 11 | Normalization | Part Record Class Segregator | Strictly segregates parts into `ORDERABLE_OEM_PART` (published part numbers) vs `PRODUCT_LINE_PART_FAMILY` | Raw `06_PART_MASTER`, `18_REMAN`, `19_CONSUMABLES` | `parts.csv` & sheet `06_PARTS` | Rejects fake SKUs for product families; enforces part number presence for orderable parts | ORIGINAL_REQUEST R2 |
| 12 | Normalization | Controlled Fitment Classifier | Normalizes fitment evidence to controlled vocabulary (`EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`) | Raw `07_MACHINE_PART_FITMENT` rows | `machine_part_fitment.csv` & sheet `07_MACHINE_PART_FITMENT` | Flags invalid vocabulary; routes conflicts to conflict log | ORIGINAL_REQUEST R2 |
| 13 | Conflict Handling | Fitment Conflict Isolator | Identifies contradictory fitment claims and routes offending records to conflict CSV and review sheet | Fitment candidate pairs | `reports/fitment_conflicts.csv` & sheet `16_REVIEW_REQUIRED` | Sets `resolution_status = 'REVIEW_REQUIRED'` | ORIGINAL_REQUEST R2, R4 |
| 14 | Normalization | Service Capability Extractor | Cleans after-sales service offerings, isolating location capabilities (`FIELD_SERVICE`, `DEALER_WORKSHOP`, `REMOTE`) | Raw `08_SERVICE_CAPABILITIES`, `15_DEALER` | `services.csv` & sheet `08_SERVICES` | Strips marketing copy and dealer URLs | ORIGINAL_REQUEST R2 |
| 15 | Normalization | Machine Service Matrix Mapper | Maps machine-to-service eligibility, retaining applicability evidence and tiers | Raw `09_MACHINE_SERVICE_MATRIX` | `machine_service.csv` & sheet `09_MACHINE_SERVICE` | Flags dangling machine or service references | ORIGINAL_REQUEST R2 |
| 16 | Normalization | Maintenance Schedule Cleaner | Standardizes operating hour intervals (50h..2000h) and normalizes maintenance action verbs | Raw `10_MAINTENANCE_SCHEDULE` rows | `maintenance.csv` & sheet `10_MAINTENANCE` | Validates numeric hour intervals; cleans action text | ORIGINAL_REQUEST R2 |
| 17 | Normalization | Service Part Requirement Linker | Connects maintenance intervals to required replacement parts with normalized quantities and units | Raw `11_SERVICE_PART_REQUIREMENTS` rows | `service_part_requirements.csv` & sheet `11_SERVICE_PART_REQUIREMENTS` | Flags dangling maintenance or part references | ORIGINAL_REQUEST R2 |
| 18 | Normalization | Digital Services Normalizer | Extracts telematics capabilities (ConSite, Global e-Service) with compatibility flags | Raw `12_MACHINE_DIGITAL_SERVICES`, `17_TELEMATICS` | `digital_services.csv` & sheet `12_DIGITAL_SERVICES` | Strips external portal URLs; retains compatibility | ORIGINAL_REQUEST R2 |
| 19 | Normalization | Relationship Classifier | Classifies cross-domain links into 6-value vocabulary (`CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`) | Raw `13_AFTER_SALES_RELATIONSHIPS` | `relationships.csv` & sheet `13_RELATIONSHIPS` | Quarantines unverified links; enforces 100% FK for `CORE` | ORIGINAL_REQUEST R2 |
| 20 | Normalization | Compact Provenance Isolator | Extracts `source_name`, `evidence_type`, and `confidence`; moves all raw URL strings to provenance store | Raw sheet provenance columns | `provenance.csv` & sheet `14_PROVENANCE` | Prevents URL leakage into core graph nodes | ORIGINAL_REQUEST R2, R5 |
| 21 | Dataset Output | 16-Sheet Excel Generator | Assembles master cleaned Excel workbook containing sheets `00_README` through `16_REVIEW_REQUIRED` | Cleaned in-memory data tables | `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` | Validates with openpyxl; asserts 17 sheets present | ORIGINAL_REQUEST R3 |
| 22 | Dataset Output | 14 Relational CSV Exporter | Exports 14 UTF-8 comma-delimited CSV files with RFC 4180 quoting and LF newlines | Cleaned in-memory data tables | 14 `.csv` files in `neo4j/data/` | Rejects non-UTF-8 characters, asserts proper quoting | ORIGINAL_REQUEST R3 |
| 23 | Reporting | Data Quality Report Generator | Compiles source vs clean row counts, dropped record tallies, and fitment distribution metrics | Pipeline transformation stats | `neo4j/reports/data_quality_report.md` | Asserts reconciliation matches between inputs and outputs | ORIGINAL_REQUEST R4 |
| 24 | Reporting | Cleanup Audit Log Generator | Produces exhaustive log of all discarded fields, value normalizations, and quarantined records | Transformation logs | `neo4j/CLEANUP_REPORT.md` | Captures rationale for every removed column and row | ORIGINAL_REQUEST R4 |
| 25 | Reporting | Schema Candidates Reviewer | Generates graph schema proposal with node labels, relationship types, and indexing strategies | Clean data schemas | `neo4j/reports/schema_candidates.md` | Provides evidence-backed graph modeling recommendations | ORIGINAL_REQUEST R4 |
| 26 | Integrity | Foreign Key Graph Validator | Validates 100% referential integrity across all 14 CSV files; asserts 0 dangling keys in `CORE` edges | 14 exported CSV files | Pass/fail integrity report | Raises `AssertionError` on any unresolved foreign key | ORIGINAL_REQUEST R5 |
| 27 | Integrity | Deterministic Sort Enforcer | Applies deterministic multi-column sorting to all exported datasets prior to serialization | In-memory data collections | Sorted tables | Eliminates non-deterministic dictionary/set iteration | ORIGINAL_REQUEST R5 |
| 28 | Integrity | Core URL Leakage Guard | Scans all core technical entity CSV files with regex to verify zero URL strings remain | 14 exported CSV files | Pass/fail URL leakage status | Raises `AssertionError` on any detected URL in core files | ORIGINAL_REQUEST R5 |
| 29 | Integrity | Determinism Double-Run Gate | Executes export pipeline twice into separate directories; asserts bit-for-bit identical hashes | Two independent pipeline runs | SHA-256 match confirmation | Fails build if any byte differs between runs | ORIGINAL_REQUEST R5 |
| 30 | Security Gate | Neo4j Isolation Guardrail | Verifies zero database drivers are imported and zero socket connections are attempted to Neo4j ports | Pipeline execution context | Zero-connection confirmation | Aborts immediately if network call to Neo4j is detected | ORIGINAL_REQUEST R6 |

---

## 9. Edge Cases Table

The table below catalogs 18 concrete edge cases discovered across the data foundation, specifying the input conditions and the mandatory observed/expected behavior.

| # | Feature | Input Condition | Observed / Expected Behavior |
|---|---|---|---|
| 1 | Machine Master | Catalogue record `MC-004` covering 3 distinct models (`ZX250-7`, `ZX300-7`, `ZX350-7`) with `model_count = 3` | Preserve 1 row in `machines.csv` with `models_covered = 'ZX250-7; ZX300-7; ZX350-7'` and `model_count = 3`. Do NOT split into 3 synthetic machine records. |
| 2 | Specification Filter | Row with `rated_power_kw` populated but `operating_weight_kg` given as `"NOT PUBLICLY STATED"` | Retain genuine power value; emit operating weight as empty string `""` in CSV and native `None` in Excel. Do NOT output `"NOT PUBLICLY STATED"`, `"NaN"`, or `0.0`. |
| 3 | Specification Filter | E-commerce promotional weight column (`ui_search_rank = 12`, `featured_badge = True`) | Strip both columns completely. Never carry UI ranking attributes into `specifications.csv`. |
| 4 | Category Hierarchy | Root category row (`Excavators`) with `parent_category = None` or empty string | Set `parent_category_id = ""` (empty string) and `category_level = 1`. Do NOT invent a dummy parent or fail validation. |
| 5 | Category Hierarchy | Self-referencing category row where `category_id == parent_category_id` | Detect cyclic error, log to audit report, set `parent_category_id = ""` if root, or flag for manual review. |
| 6 | Application Normalization | Application string `"Demolition; Demolition "` with duplicate tokens and trailing whitespace | Deduplicate and sanitize to single canonical string `"Demolition"`. |
| 7 | Application Normalization | Application string `"Quarry/Mining"` or `"quarry & mining "` | Map to single canonical vocabulary term `"Quarry & Mining"`. |
| 8 | Attachment Hygiene | Attachment row with marketing URL `https://www.hitachicm.com/attachments/breaker-01.html` in description | Strip URL from attachment description; if required, record source citation in `provenance.csv` under `PRV-xxx`. |
| 9 | Parts Segregation | Part record "Hitachi Genuine Engine Oil DH-2" with fluid specification but no discrete part number | Classify as `record_class = 'PRODUCT_LINE_PART_FAMILY'` with `part_number = ""`. Do NOT manufacture a fake part number like `SKU-DH2`. |
| 10 | Parts Segregation | Part record "Battery 12V 110Ah" with OEM published part number `4663907` | Classify as `record_class = 'ORDERABLE_OEM_PART'` with `part_number = '4663907'`. |
| 11 | Fitment Evidence | Fitment row with evidence marked `"confirmed by dealer forum post"` | Vocabulary violation: Map to controlled vocabulary `NOT_STATED` or `DERIVED`, flag in cleanup report. |
| 12 | Fitment Conflict | Part `PRT-001` listed as compatible with `MC-001` in row 45, but incompatible in row 112 | Flag conflict in `reports/fitment_conflicts.csv` with `resolution_status = 'REVIEW_REQUIRED'`; exclude contradictory edge from `CORE`. |
| 13 | Service Capabilities | Service row with description containing dealer telephone numbers and booking portal link | Strip booking link and contact clutter; preserve core service definition and `location_capabilities = 'DEALER_WORKSHOP'`. |
| 14 | Maintenance Schedule | Maintenance task with interval listed as `"Every 500 hours or 6 months (whichever comes first)"` | Parse into numeric `interval_hours = 500` and `interval_months = 6`. Sanitize task text. |
| 15 | Service Part Requirements | Part requirement row referencing a legacy part number dropped during parts deduplication | Catch foreign key violation: quarantine record into `16_REVIEW_REQUIRED`; do NOT emit dangling foreign key in `service_part_requirements.csv`. |
| 16 | Relationship Classification | Cross-sheet relationship where `source_id` is valid `MC-001` but `target_id` is an unmapped external ID | Classify as `classification = 'UNRESOLVED'`. Exclude from `CORE` graph edges so foreign key integrity of `CORE` remains 100%. |
| 17 | Deterministic Export | Float value calculated as `140.00000000000003` during unit conversion | Format explicitly with `f"{val:.2f}"` (or integer if whole number `140`), guaranteeing identical string representation across runs. |
| 18 | Source Immutability | Script accidentally attempts `open(source_path, 'w')` or `wb.save(source_path)` | Pre-flight permission check and post-execution SHA-256 validation abort pipeline immediately with exit code 3, failing the run. |

---

## 10. Conclusion & Recommendations for Project Orchestrator

1. **Specification Coverage**: All 21 source sheets, 16 target Excel sheets (17 including `00_README`), 14 target CSV files, 11 normalization domains, 5 audit reports, and determinism/integrity guardrails are fully defined.
2. **Decomposition Readiness**: The project orchestrator can directly decompose the implementation into 5 sequential milestones:
   - **M1**: Pre-Cleaning Source Audit (`audit_workbook.py` -> `neo4j/reports/workbook_audit.md`).
   - **M2**: Physical Entity Normalization (Categories, Machines, Specs, Apps, Attachments, Parts -> CSVs 1-6).
   - **M3**: Relationship & Matrix Normalization (Fitment, Services, Maintenance, Digital Services, Relationships, Provenance -> CSVs 7-14).
   - **M4**: Clean Master Workbook Assembly (`HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` with all 17 sheets).
   - **M5**: Reporting Engine & Verification Harness (`data_quality_report.md`, `CLEANUP_REPORT.md`, `schema_candidates.md`, conflict CSVs, and determinism/integrity double-run check).
3. **Strict Compliance**: The specification miners strictly respected all constraints: zero modifications to the source workbook, zero implementation code written, and zero connections to Neo4j.
