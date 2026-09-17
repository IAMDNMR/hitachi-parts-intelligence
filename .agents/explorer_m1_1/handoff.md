# Handoff Report: Milestone 1 Architecture Strategy (`audit_workbook.py`)

**Agent**: `explorer_m1_1` (Milestone 1 Lead Explorer)  
**Milestone**: M1 (Discovery & Pre-Cleaning Source Audit)  
**Working Directory**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1`  
**Date**: 2026-09-17  
**Type**: Hard Handoff (Task Complete)  

---

## 1. Observation

1. **Source Workbook & Constraints**:
   - `ORIGINAL_REQUEST.md` (lines 10-12): Authoritative source workbook is located at `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` (796 KB, 21 sheets) and must remain completely untouched.
   - `ORIGINAL_REQUEST.md` (lines 16-17, R1): "Inspect all 21 sheets in the workbook. Generate neo4j/reports/workbook_audit.md documenting for every sheet: row count, column count, column headers, non-empty counts, empty counts, duplicate rows, duplicate IDs, suspicious/URL/e-commerce/research fields, fields useful for technical entities, fields useful for graph relationships, and fields to remove or normalize."
   - `ORIGINAL_REQUEST.md` (lines 52-53, R6): "Under NO circumstances connect to Neo4j, call Neo4j Aura, create Neo4j constraints, indexes, nodes, or edges during this task. Work stops after the cleaned Excel, CSVs, and reports are verified on disk."
   - `ORIGINAL_REQUEST.md` (lines 47-50, R5): Determinism requirement: running `audit_workbook.py` twice produces byte-identical outputs.

2. **Project Interface Contracts**:
   - `PROJECT.md` (lines 93-102):
     ```
     CLI: audit_workbook.py
     Invocation: python audit_workbook.py [--input <path>] [--output <path>] [--verify-source]
     Default --input: C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx
     Default --output: neo4j/reports/workbook_audit.md
     Behavior:
       - Opens workbook in read-only, data-only mode (openpyxl.load_workbook(path, read_only=True, data_only=True)).
       - Asserts source file modification time and SHA-256 hash are identical before and after execution.
       - Outputs Markdown audit covering all 21 sheets with standardized metrics.
       - Returns exit code 0 on success, non-zero on failure.
     ```

3. **21-Sheet Domain Mapping**:
   - `spec_miner_survey_1/report.md` (lines 30-54) and `explorer_survey_2/report.md` (lines 30-52): Catalog all 21 sheets in exact workbook order from `00_README` through `20_OPERATOR_MANUALS`.
   - Primary key candidates, active row counts (e.g. 77 machine catalogue records, 13 attachments, 64 parts), and hygiene risks (sentinel string `"NOT PUBLICLY STATED"`, UI rankings, full URLs).

4. **Explorer Division of Labor**:
   - `explorer_m1_1` (current): Overall architecture, modular decomposition, sheet-by-sheet audit methodology, immutability check.
   - `explorer_m1_2`: Profiling algorithms, memory efficiency, determinism controls.
   - `explorer_m1_3`: Exact Markdown report layout, CLI parsing, exit code contracts.

---

## 2. Logic Chain

1. **Safety & Immutability (Premise from Obs 1 & 2)**:
   - To guarantee the source workbook is never modified, `audit_workbook.py` must take a pre-read cryptographic fingerprint (`hashlib.sha256` in 64KB blocks, plus `os.stat` `st_mtime` and `st_size`).
   - The file must be loaded strictly with `openpyxl.load_workbook(..., read_only=True, data_only=True)` which opens the underlying zip archive in read mode without write hooks.
   - Immediately after closing the workbook via `wb.close()`, the fingerprint must be recomputed and asserted. If any mismatch occurs, the script must abort immediately with exit code `3`.

2. **Memory Efficiency & Streaming (Premise from Obs 2 & 3)**:
   - With 21 sheets and hundreds of rows/columns, streaming rows via `sheet.iter_rows(values_only=True)` processes cells in a single pass without holding entire DOM structures in RAM.

3. **Multi-Class Column Classification (Premise from Obs 1 & 3)**:
   - R1 explicitly requires identifying fields useful for technical entities, fields useful for graph relationships, and fields to remove or normalize.
   - A deterministic rule engine can categorize each column into 5 mutually exclusive classes:
     1. `TECHNICAL_ENTITY_ATTRIBUTE`
     2. `GRAPH_RELATIONSHIP_POINTER`
     3. `PROVENANCE_METADATA`
     4. `CONTROLLED_VOCAB_FIELD`
     5. `NOISE_TO_REMOVE`

4. **Determinism Enforcement (Premise from Obs 1 & 2)**:
   - Dynamic timestamps (such as `datetime.now()`) introduce non-deterministic file output across runs.
   - By anchoring report headers with the static SHA-256 hash of the input file and fixed tool metadata, sorting all sample sets/keys, formatting numbers with explicit fixed precision (`f"{rate:.2f}%"`), and writing with UTF-8 LF (`\n`), the markdown report is guaranteed 100% bit-for-bit reproducible across consecutive runs.

5. **Strict Neo4j Isolation (Premise from Obs 1)**:
   - The script requires only Python standard libraries (`argparse`, `hashlib`, `os`, `sys`, `pathlib`, `re`) and `openpyxl`. Zero database drivers are imported or called.

---

## 3. Caveats

1. **Read-Only Explorer Scope**: In accordance with the Explorer archetype instructions, this agent produced the technical architecture, modular decomposition, and sheet-by-sheet audit methodology. No production code was modified or executed.
2. **Dynamic Trailing Row Handling**: In openpyxl streaming mode, `sheet.max_row` can occasionally overestimate rows if empty formatting extends beyond data. The streaming auditor must filter trailing rows where all values are `None` or whitespace.
3. **Encoding & Excel Nuances**: Some text cells in raw spreadsheets contain non-breaking spaces (`\u00a0`) or carriage returns (`\r\n`). The scanner must detect these during data hygiene profiling.

---

## 4. Conclusion

The implementation strategy for `audit_workbook.py` and `neo4j/reports/workbook_audit.md` is fully defined and documented in:
- `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1\report.md`

The worker agent assigned to implement `audit_workbook.py` can directly follow this 5-module blueprint (`argparse` CLI, `SourceVerifier`, `StreamingScanner`, `MetricsEngine`, `ReportFormatter`) to produce the audit report while strictly complying with the source immutability, determinism, and Neo4j isolation guardrails.

---

## 5. Verification Method

Downstream workers, reviewers, and challengers can independently verify this strategy using the following verification steps:

1. **Static Architecture & File Review**:
   - Inspect `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1\report.md` for complete coverage of all 21 sheets and 5 modular components.
2. **Implementation Execution**:
   - Once `audit_workbook.py` is implemented by worker:
     ```bash
     python audit_workbook.py --input "C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx" --output "neo4j/reports/workbook_audit.md"
     ```
   - Assert exit code is `0`.
3. **Artifact Integrity Verification**:
   - Verify `neo4j/reports/workbook_audit.md` exists and contains 21 distinct sheet sections.
   - Verify zero database connections were made.
4. **Immutability & Determinism Verification**:
   - Compute SHA-256 of source workbook before and after run; assert equality.
   - Run `audit_workbook.py` twice consecutively into two output locations and assert identical SHA-256 hashes:
     ```bash
     python audit_workbook.py -o run1.md
     python audit_workbook.py -o run2.md
     # Assert run1.md SHA256 == run2.md SHA256
     ```
