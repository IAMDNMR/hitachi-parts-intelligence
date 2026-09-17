# Handoff Report — explorer_survey_3 (Pipeline & Integrity Explorer)

## 1. Observation
1. **Authoritative User Request**:
   - `ORIGINAL_REQUEST.md:5`: "Clean, normalize, deduplicate, and validate the 21-sheet HCME After-Sales data foundation workbook (HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx), producing a clean, graph-ready Excel workbook (HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx), normalized import CSV files, and comprehensive audit and data quality reports. Do NOT connect to Neo4j or create database nodes/relationships."
   - `ORIGINAL_REQUEST.md:12`: Source workbook path is `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx (796 KB, 21 sheets)`.
   - `ORIGINAL_REQUEST.md:34-37`: Requires 16 sheets in `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` (`00_README` through `16_REVIEW_REQUIRED`) and exactly 14 CSV files in `neo4j/data/` (`categories.csv`, `machines.csv`, `specifications.csv`, `applications.csv`, `attachments.csv`, `parts.csv`, `machine_part_fitment.csv`, `services.csv`, `machine_service.csv`, `maintenance.csv`, `service_part_requirements.csv`, `digital_services.csv`, `relationships.csv`, `provenance.csv`).
   - `ORIGINAL_REQUEST.md:41-45`: Requires 4 markdown reports (`workbook_audit.md`, `data_quality_report.md`, `CLEANUP_REPORT.md`, `schema_candidates.md`) and 2 conflict CSVs (`reports/fitment_conflicts.csv`, `reports/service_relationship_conflicts.csv`).
   - `ORIGINAL_REQUEST.md:48-53`: Strict determinism ("running audit_workbook.py and export_clean_data.py twice produces byte-identical CSV and report outputs"), 100% referential integrity, zero URL strings in core CSV columns, and strict Neo4j isolation ("Under NO circumstances connect to Neo4j, call Neo4j Aura, create Neo4j constraints, indexes, nodes, or edges during this task").

2. **Existing Domain Catalog Artifacts**:
   - `frontend/data/machineCatalogue.js:3-9`: Notes 77 product-page records (`MC-001` through `MC-077`), 85 model codes, and 7 visual categories (`Mini`, `Medium`, `Large`, `Wheel Loaders`, `Mining Excavators`, `Special Application`, etc.).
   - `frontend/data/partsStoreCatalogue.js:584-593`: Shows raw data patterns containing URLs in source fields (e.g. `source: 'Filters | https://www.hitachicm.com/eu/en/parts/filters/'`) that require stripping from core entity attributes.
   - `frontend/tests/partsStore.test.mjs:19-21`: "Nothing here may be invented — a price, a stock count, a part number, a fitment, or a product that doesn't exist in the source data at all".

---

## 2. Logic Chain
1. **From Observation 1 (R1 & Immutability)**:
   Because the source file `HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` must remain completely unmodified, `audit_workbook.py` must use openpyxl in streaming `read_only=True, data_only=True` mode, and bracket execution with SHA-256 and `st_mtime` assertions.
2. **From Observation 1 (R1 & Determinism)**:
   Because running the audit script twice must produce byte-identical reports, `audit_workbook.py` cannot embed dynamic system timestamps (`datetime.now()`). Instead, it must stamp the static SHA-256 hash of the input file. Output columns and sheets must follow fixed Excel order, sets must be sorted, floats must be formatted with fixed precision, and line endings must be forced to `\n`.
3. **From Observation 1 & 2 (R2, R3 & Transformation Pipeline)**:
   The transformation script `export_clean_data.py` requires a multi-stage architecture:
   - Segregate orderable parts (`ORDERABLE_OEM_PART` with part numbers) from product lines (`PRODUCT_LINE_PART_FAMILY` without part numbers).
   - Enforce controlled vocabulary for fitment (`EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`) and relationship classification (`CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`).
   - Strip URLs and UI rankings from core entity CSVs.
   - Route contradictions to `reports/fitment_conflicts.csv` and `reports/service_relationship_conflicts.csv`.
4. **From Observation 1 (R5 & Referential Integrity)**:
   The 14 CSV files form a strict relational graph. Primary keys must be unique. Foreign keys in child tables (`machines -> categories`, `fitment -> machines & parts`, `service_part_requirements -> maintenance & parts`, `CORE relationships -> entities`) must resolve 100% with zero dangling edges.
5. **From Observation 1 (R6 & Neo4j Isolation)**:
   To prevent any accidental Neo4j calls, scripts must avoid importing database drivers (`neo4j`, `py2neo`), and the test harness must assert zero outbound network socket activity to port 7687 or Neo4j Aura endpoints.

---

## 3. Caveats
- No caveats. The investigation verified all pipeline, interface, determinism, reporting, and integrity requirements from the source request and existing codebase.

---

## 4. Conclusion
1. `audit_workbook.py` and `export_clean_data.py` have been fully specified with complete CLI parameter sets, safe read-only openpyxl configurations, deterministic output rules, and fail-safe return codes.
2. The foreign key referential integrity graph across all 14 target CSVs, controlled vocabulary constraints, and URL leakage filters are established.
3. A 5-tier verification harness (`tests/verify_pipeline_integrity.py`) and a 7-stage milestone execution roadmap (M0 to M6) have been designed for the project orchestrator.
4. Comprehensive findings have been written to `report.md`.

---

## 5. Verification Method
1. Inspect the architectural report:
   `view_file(AbsolutePath="c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_3\report.md")`
2. Verify all 4 mission requirements are covered:
   - CLI & metric extraction for `audit_workbook.py` (Sections 2.1 & 2.2)
   - Transformations & determinism for `export_clean_data.py` (Sections 3.1 - 3.4)
   - Referential integrity graph & validation checks across 14 CSVs (Section 4)
   - Verification test harness & milestone strategy (Section 5)
3. Invalidation conditions:
   - Any requirement for an interactive or write-mode connection to Neo4j.
   - Non-deterministic output formatting (e.g. wall-clock timestamps in markdown reports).
   - Uncontrolled foreign key references or dangling edges in `CORE` relationships.
