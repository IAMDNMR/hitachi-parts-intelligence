# Original User Request

## Initial Request — 2026-09-17T10:28:38Z

Clean, normalize, deduplicate, and validate the 21-sheet HCME After-Sales data foundation workbook (HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx), producing a clean, graph-ready Excel workbook (HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx), normalized import CSV files, and comprehensive audit and data quality reports. Do NOT connect to Neo4j or create database nodes/relationships.

Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service
Integrity mode: development

## Source Workbook
Authoritative source workbook (must remain untouched):
C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx (796 KB, 21 sheets)

## Requirements

### R1. Comprehensive 21-Sheet Source Audit
Inspect all 21 sheets in the workbook. Generate neo4j/reports/workbook_audit.md documenting for every sheet: row count, column count, column headers, non-empty counts, empty counts, duplicate rows, duplicate IDs, suspicious/URL/e-commerce/research fields, fields useful for technical entities, fields useful for graph relationships, and fields to remove or normalize.

### R2. Core Technical Entity & Relationship Normalization
- Categories: Clean machine hierarchy ((:Category)-[:CHILD_OF]->(:Category)), normalize naming and whitespace.
- Machines & Models: Clean 02_MACHINE_MASTER. Preserve difference between catalogue page records (Machine ID, e.g. MC-001) and individual model codes (Models Covered, Model Count). Do not invent or merge distinct model codes.
- Specifications: Clean 03_MACHINE_SPECIFICATIONS. Retain genuine technical specifications (weight, power, capacity, digging force, dimensions). Strip e-commerce importance and UI ranking. Preserve blank/null for "NOT PUBLICLY STATED" without inventing fake values.
- Applications: Normalize casing/whitespace (e.g., canonical Demolition).
- Attachments: Clean 05_ATTACHMENTS retaining id, name, type, application, compatibility level. Remove URLs and UI clutter. Do not invent part numbers or dimensions.
- Parts: Clean 06_PART_MASTER. Maintain strict separation between ORDERABLE_OEM_PART (published part numbers) and PRODUCT_LINE_PART_FAMILY (informational product lines). Do not manufacture part numbers or turn product lines into fake SKUs.
- Fitment: Clean 07_MACHINE_PART_FITMENT. Normalize evidence to controlled vocabulary: EXACT_MODEL, MODEL_RANGE, CATEGORY, DERIVED, NOT_STATED. Flag any conflicting fitment in reports/fitment_conflicts.csv with resolution = 'REVIEW_REQUIRED'.
- Services & Digital Services: Clean 08_SERVICE_CAPABILITIES, 09_MACHINE_SERVICE_MATRIX, and 12_MACHINE_DIGITAL_SERVICES. Strip URLs and UI clutter. Retain location capabilities and applicability evidence.
- Maintenance & Part Requirements: Clean 10_MAINTENANCE_SCHEDULE and 11_SERVICE_PART_REQUIREMENTS. Document candidate graph entities in reports/schema_candidates.md.
- Relationships: Clean 13_AFTER_SALES_RELATIONSHIPS. Classify each row into CORE, DUPLICATE, DERIVED, RESEARCH_ONLY, INVALID, UNRESOLVED.
- Provenance: Retain compact provenance metadata (source_name, evidence_type, confidence) without carrying URL strings into core graph nodes.

### R3. Graph-Ready Dataset Output Generation
Generate:
1. HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx containing 16 clean sheets:
   - 00_README, 01_CATEGORIES, 02_MACHINES, 03_SPECIFICATIONS, 04_APPLICATIONS, 05_ATTACHMENTS, 06_PARTS, 07_MACHINE_PART_FITMENT, 08_SERVICES, 09_MACHINE_SERVICE, 10_MAINTENANCE, 11_SERVICE_PART_REQUIREMENTS, 12_DIGITAL_SERVICES, 13_RELATIONSHIPS, 14_PROVENANCE, 15_DATA_QUALITY, 16_REVIEW_REQUIRED.
2. Machine-readable CSV files in neo4j/data/:
   - categories.csv, machines.csv, specifications.csv, applications.csv, attachments.csv, parts.csv, machine_part_fitment.csv, services.csv, machine_service.csv, maintenance.csv, service_part_requirements.csv, digital_services.csv, relationships.csv, provenance.csv.

### R4. Comprehensive Audit & Data Quality Reporting
Create:
- neo4j/reports/workbook_audit.md (pre-cleaning 21-sheet analysis)
- neo4j/reports/data_quality_report.md (source vs clean counts, removals, duplicates, fitment breakdown, zero unresolved dangling edges)
- neo4j/CLEANUP_REPORT.md (exhaustive log of removed fields, merged rows, normalized values, provenance strategy)
- neo4j/reports/schema_candidates.md (node and edge candidate review with justifications)
- reports/fitment_conflicts.csv and reports/service_relationship_conflicts.csv (if conflicts exist)

### R5. Determinism & Integrity Verification
- Pipeline must be fully deterministic: running audit_workbook.py and export_clean_data.py twice produces byte-identical CSV and report outputs.
- Verify 100% referential integrity across all CSVs: every source ID and target ID in relationships exists in the corresponding entity CSV.
- Zero URL strings or UI ranking metadata in core technical CSV columns.

### R6. Strict Neo4j Isolation Guardrail
Under NO circumstances connect to Neo4j, call Neo4j Aura, create Neo4j constraints, indexes, nodes, or edges during this task. Work stops after the cleaned Excel, CSVs, and reports are verified on disk.

## Acceptance Criteria

### Data Completeness & Schema Integrity
- [ ] Original file C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx remains completely unmodified (byte/timestamp check).
- [ ] HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx is generated with all 16 specified sheets and can be read by openpyxl.
- [ ] All 14 CSV files exist in neo4j/data/ with valid UTF-8 encoding and standard comma delimiters.
- [ ] Zero duplicate IDs in categories.csv, machines.csv, attachments.csv, parts.csv, services.csv, digital_services.csv.
- [ ] Zero dangling foreign keys in relationships.csv, machine_part_fitment.csv, machine_service.csv, and service_part_requirements.csv.
- [ ] All parts with published part numbers have record_class = 'ORDERABLE_OEM_PART'; product lines without part numbers have record_class = 'PRODUCT_LINE_PART_FAMILY'. No manufactured part numbers.
- [ ] Controlled fitment evidence vocabulary strictly enforced: EXACT_MODEL, MODEL_RANGE, CATEGORY, DERIVED, NOT_STATED.
- [ ] Zero full URL strings in core entity CSV files (machines.csv, parts.csv, attachments.csv, services.csv, digital_services.csv, specifications.csv).

### Audit & Documentation Reports
- [ ] neo4j/reports/workbook_audit.md covers all 21 source sheets with exact row/column metrics.
- [ ] neo4j/reports/data_quality_report.md reports before/after row counts, deduplications, and fitment breakdown.
- [ ] neo4j/CLEANUP_REPORT.md details every removed field, normalized value, and rejected/conflict record.
- [ ] neo4j/reports/schema_candidates.md reviews node candidates and provides evidence-backed recommendations.
- [ ] Re-running the cleaning script produces identical output files (deterministic check passes).
- [ ] No network calls made to Neo4j Aura; zero nodes/relationships created in any database.
