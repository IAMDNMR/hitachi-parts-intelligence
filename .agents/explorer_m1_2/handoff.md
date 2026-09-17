# Handoff Report: Explorer M1-2 (Source Immutability & Audit Metrics)

**Agent**: `explorer_m1_2`  
**Milestone**: Milestone 1 (Discovery & Source Audit)  
**Deliverable**: Data structures, metric extraction algorithms, openpyxl memory safety, and determinism controls for `audit_workbook.py`.  
**Type**: Hard Handoff  

---

## 1. Observation

1. **Source File Immutability Constraint**:
   - `ORIGINAL_REQUEST.md:11-12`: "Authoritative source workbook (must remain untouched): C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx (796 KB, 21 sheets)".
   - `ORIGINAL_REQUEST.md:58`: "- [ ] Original file C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx remains completely unmodified (byte/timestamp check)."
   - `PROJECT.md:48`: "Feature 2: Source Immutability Verifier: Computes SHA-256 hash and st_mtime before reading; asserts identical hash immediately after closing".

2. **21-Sheet Audit Metrics Mandate**:
   - `ORIGINAL_REQUEST.md:16-17`: "Inspect all 21 sheets in the workbook. Generate neo4j/reports/workbook_audit.md documenting for every sheet: row count, column count, column headers, non-empty counts, empty counts, duplicate rows, duplicate IDs, suspicious/URL/e-commerce/research fields, fields useful for technical entities, fields useful for graph relationships, and fields to remove or normalize."

3. **Determinism Protocols & Edge Cases**:
   - `ORIGINAL_REQUEST.md:48-49`: "Pipeline must be fully deterministic: running audit_workbook.py and export_clean_data.py twice produces byte-identical CSV and report outputs."
   - `spec_miner_survey_1/report.md:410-415`: Requires zero dynamic timestamps (`datetime.now()`), fixed float precision (`f"{rate:.2f}%"`), deterministic multi-column sorting, and explicit LF (`\n`) newlines.
   - `explorer_survey_2/report.md:119-122`: Identifies sentinel string `"NOT PUBLICLY STATED"` across technical specifications.
   - `explorer_survey_3/report.md:61-75`: Identifies openpyxl `read_only=True, data_only=True` streaming pattern and notes that `ws.max_row` and `ws.max_column` can be unreliable in streaming mode.

4. **Strict Neo4j Isolation Guardrail**:
   - `ORIGINAL_REQUEST.md:52-53`: "Under NO circumstances connect to Neo4j, call Neo4j Aura, create Neo4j constraints, indexes, nodes, or edges during this task. Work stops after the cleaned Excel, CSVs, and reports are verified on disk."

---

## 2. Logic Chain

1. **Memory Safety & Streaming Derivation** (from Observation 1 & 3):
   - Loading 21 sheets into openpyxl DOM mode instantiates hundreds of thousands of cell, style, and font objects in memory, ballooning memory usage and risking performance degradation.
   - Using `openpyxl.load_workbook(path, read_only=True, data_only=True)` with `ws.iter_rows(values_only=True)` bypasses object tree creation and evaluates formulas to cached scalar values.
   - Because `ws.max_row` and `ws.max_column` in openpyxl `read_only` mode can be `None` or inaccurate when worksheet XML dimension tags are missing or out of sync, row and column counts must be calculated dynamically while streaming tuples.
   - To avoid resource leaks and file locks on the source zip container, the workbook must be enclosed in `try...finally: wb.close()`.

2. **Metric Extraction Algorithms Derivation** (from Observation 2 & 3):
   - **Active Data Rows**: Phantom empty rows at the bottom of sheets (common in Excel) distort column fill rates. Rows must be tested with `is_row_empty()`: completely blank rows are tallied in `empty_row_count`, while active data rows form the denominator for column fill rates.
   - **Primary Key Uniqueness**: Candidate PKs are mapped from a canonical dictionary (`01_CATEGORIES` -> `category_id`, `02_MACHINE_MASTER` -> `machine_id`, etc.) with fallback to `*_id` column detection. Tracking frequencies in a hash set/map allows counting both distinct collided keys and total duplicate rows, with top-10 sorted duplicate keys emitted.
   - **Full Duplicate Rows**: Generating a SHA-256 hash of each row's normalized string tuple enables $O(N)$ row-duplicate detection with minimal memory overhead.
   - **URL Leakage Engine**: A strict regular expression `r'(https?://[^\s"\'<>]+|www\.[^\s"\'<>]+|(?:[a-zA-Z0-9-]+\.)+(?:com|eu|org|net|de|co\.uk|jp)(?:/[^\s"\'<>]*)?)'` detects web links without falsely matching hyphenated model codes (e.g., `ZX250-7`) or decimal numbers (e.g., `28.5`).
   - **Sentinel Value Detection**: Matching against a controlled set (`NOT PUBLICLY STATED`, `N/A`, `-`, `TBD`, etc.) classifies non-empty text cells that represent missing data, preserving clear distinction between raw fill rate and effective data availability.
   - **Column Utility Classification**: A 5-class taxonomy (`TECHNICAL_ENTITY_ATTRIBUTE`, `GRAPH_RELATIONSHIP_POINTER`, `PROVENANCE_METADATA`, `CONTROLLED_VOCAB_FIELD`, `NOISE_TO_REMOVE`) categorizes each column based on header keywords, URL counts, and data types.

3. **100% Byte-Level Determinism Derivation** (from Observation 3):
   - Including `datetime.now()` or execution durations in generated markdown causes consecutive runs to produce different files, failing determinism checks. Replacing timestamps with the static cryptographic SHA-256 hash of the input file achieves 100% static reproducibility.
   - Python set iteration order is non-deterministic between processes (`PYTHONHASHSEED`). All sets (inferred types, duplicate samples) must be explicitly sorted before rendering.
   - Enforcing `newline='\n'` and `encoding='utf-8'` prevents Windows CRLF vs Linux LF differences.
   - Formatting all floats with fixed precision (`f"{val:.2f}%"`) prevents trailing floating-point representation drift.

4. **Source Immutability Protocol Derivation** (from Observation 1):
   - Computing SHA-256 via 64KB chunked reading and capturing `st_mtime_ns` both before opening and after closing openpyxl proves mathematically that 0 bytes were modified. If a mismatch is detected, the script raises `SourceImmutabilityError` and terminates with exit code 3.

---

## 3. Caveats

1. **Merged Cells in Read-Only Mode**: Openpyxl does not populate merged cell ranges in `read_only=True` mode. In Excel XML, secondary cells in a merged range yield `None`. This primarily affects header rows if a user merged columns in row 1; our algorithm assigns a fallback `UNNAMED_COL_{col_idx}` so execution never crashes.
2. **Formula Cache Dependency**: With `data_only=True`, openpyxl reads cached formula values saved by Microsoft Excel. If an Excel file was created by an external library that did not calculate formulas, cell values may evaluate to `None`. The audit script detects and flags formula errors like `#VALUE!`.
3. **Primary Key Fallback Heuristics**: While all 21 sheets have canonical PK mappings in `CANONICAL_SHEET_PK_MAP`, any unmapped custom sheet falls back to checking column names ending in `_id` or `id`. If no matching header exists, candidate PK is reported as None without throwing an exception.

---

## 4. Conclusion

1. The data structures, metric extraction algorithms, openpyxl memory safety rules, and determinism controls for `audit_workbook.py` are fully designed, specified, and documented in `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_2\report.md`.
2. The design enables `audit_workbook.py` to:
   - Audit all 21 sheets non-destructively in streaming mode.
   - Calculate exact dimensions, fill rates, PK duplicates, full row duplicates, URL counts, sentinel counts, and column classifications.
   - Achieve 100% byte-for-byte reproducibility across runs (Feature 29).
   - Guarantee source immutability via pre/post SHA-256 and `st_mtime_ns` checks (Feature 2).
   - Strictly adhere to Neo4j isolation guardrails (Feature 30).
3. The specification is ready for immediate implementation by the Milestone 1 worker agent.

---

## 5. Verification Method

To verify the design and implementation independently:

1. **Inspect Report Artifact**:
   - Read `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_2\report.md` to review the dataclass definitions, algorithm implementations, and reference code blueprint.
2. **Deterministic Run Verification (when worker implements `audit_workbook.py`)**:
   ```bash
   python audit_workbook.py --input C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx --output neo4j/reports/workbook_audit.md
   python audit_workbook.py --input C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx --output neo4j/reports/workbook_audit_run2.md
   # Verify bit-for-bit identical hashes:
   python -c "import hashlib; h1=hashlib.sha256(open('neo4j/reports/workbook_audit.md','rb').read()).hexdigest(); h2=hashlib.sha256(open('neo4j/reports/workbook_audit_run2.md','rb').read()).hexdigest(); assert h1 == h2, f'{h1} != {h2}'; print('Deterministic check PASSED:', h1)"
   ```
3. **Source Immutability Check**:
   - Verify that `HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` has an identical SHA-256 and modification time before and after the run.
4. **Opaque-Box Test Harness**:
   - Run `python tests/test_e2e_harness.py --tier 1` once published by `test_writer_m_test`.
