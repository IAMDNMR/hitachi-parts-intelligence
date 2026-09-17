# Task Assignment: Milestone 1 Implementation Worker (worker_m1)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\worker_m1
- Exclusive write ownership: `audit_workbook.py` and `neo4j/reports/workbook_audit.md` (and tests in `tests/test_audit_workbook.py` if needed)
- Must NOT write to: `tests/test_e2e_harness.py`, `TEST_READY.md`, or source workbook.
- Source workbook (READ ONLY, MUST REMAIN UNTOUCHED): C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx
- Authoritative user request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Project scope: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md
- Input Explorer Blueprints:
  - c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1\report.md
  - c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_2\report.md
  - c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_3\report.md

## 2026-09-17T10:46:04Z
You are worker_m1, the Milestone 1 Implementation Worker.
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\worker_m1
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\worker_m1\DISPATCH.md
Read the authoritative user request at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
Read the project architecture at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md

Read the authoritative implementation blueprints from the 3 Milestone 1 Explorers:
- Architecture & Decomposition: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1\report.md
- Metrics Extraction, Memory Safety & Determinism: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_2\report.md
- Report Format, CLI Interface & Validation Tests: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_3\report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL CONSTRAINTS:
1. Source Workbook (C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx) MUST remain completely untouched. Read-only inspection only. Pre- and post-execution SHA-256 hash and st_mtime must be asserted identical; exit with code 3 if modified.
2. Strict Neo4j Isolation Guardrail: Under NO circumstances connect to Neo4j, call Neo4j Aura, create Neo4j constraints, indexes, nodes, or edges. Work stops after files are verified on disk.
3. 100% Determinism: Running audit_workbook.py twice must produce byte-identical markdown outputs. Static SHA-256 header (no datetime.now()), deterministic sorting, UTF-8 with LF (\n).
4. Exclusive Write Ownership: You own `audit_workbook.py` and `neo4j/reports/workbook_audit.md` (and tests in `tests/test_audit_workbook.py`). DO NOT touch `tests/test_e2e_harness.py` or `TEST_READY.md`.

Your Mission:
1. Implement `audit_workbook.py` at the workspace root (`c:\Users\iamdn\OneDrive\Desktop\Parts&Service\audit_workbook.py`) supporting:
   - CLI options: `--input`, `--output`, `--verify-source`, `--quiet`, `--version`
   - Exit code contract: 0 = success, 1 = bad args, 2 = missing/corrupt source, 3 = source modified/hash mismatch
   - Memory-safe openpyxl streaming (`read_only=True, data_only=True`)
   - Pre- and post-read SHA-256 and timestamp check
   - Metric extraction across all 21 sheets: row count, col count, active data rows, headers, non-empty/empty counts, fill rates, duplicate rows, duplicate IDs, suspicious/URL/e-commerce noise fields, and 5-class column classification
   - Deterministic markdown generation
2. Execute `python audit_workbook.py` to generate `neo4j/reports/workbook_audit.md`.
3. Verify:
   - Run verification tests
   - Verify source workbook hash unchanged
   - Verify double-run determinism (byte-identical output)
4. Write your implementation report to:
   `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\worker_m1\report.md`
   and write a standard 5-component handoff in:
   `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\worker_m1\handoff.md`
Send a completion message back to the orchestrator when finished.
