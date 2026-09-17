# Task Assignment: E2E Test Suite Writer (M-TEST)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\test_writer_m_test
- Scope: Implement `tests/test_e2e_harness.py` implementing comprehensive 4-tier requirement-driven opaque-box tests per `TEST_INFRA.md` and publish `TEST_READY.md`.
- Original request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Project scope: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md
- Test infra: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\TEST_INFRA.md

## 2026-09-17T10:42:04Z
You are test_writer_m_test, an E2E Test Writer.
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\test_writer_m_test
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\test_writer_m_test\DISPATCH.md
Read the authoritative user request at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
Read the project architecture at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md
Read the test infrastructure design at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\TEST_INFRA.md

CRITICAL CONSTRAINTS:
1. Source Workbook (C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx) must remain completely untouched.
2. Strict Neo4j Isolation: Under NO circumstances connect to Neo4j, call Neo4j Aura, or load DB drivers. Work stops on disk.
3. You are a Test Writer. You write tests, test harnesses, and test documentation. Do NOT implement or modify data extraction code (such as audit_workbook.py or export_clean_data.py).

Your Mission:
1. Implement the comprehensive opaque-box E2E test suite in `tests/test_e2e_harness.py`.
   The runner must support:
   - Command line: `python tests/test_e2e_harness.py [--tier 1|2|3|4|all] [--verbose]`
   - Exit code 0 if all requested tests pass, non-zero if any test fails.
   - Tier 1: Feature Coverage (checks existence, schemas, headers, non-empty content for all 16 target Excel sheets, 14 CSVs, and audit reports).
   - Tier 2: Boundary & Corner Cases (checks null handling as empty string, zero URLs in core CSVs, no manufactured part numbers, controlled fitment vocabulary, record_class segregation).
   - Tier 3: Referential Integrity & Cross-Feature combinations (checks FK graph across all 14 CSVs, zero dangling edges in CORE relationships, machine/part fitment integrity).
   - Tier 4: Real-World Workload Scenarios (checks pre-cleaning audit metrics coverage across all 21 sheets, double-run determinism verification, openpyxl readability, and strict Neo4j isolation check).
2. When the test suite harness is written, verified, and complete, publish `TEST_READY.md` at project root (`c:\Users\iamdn\OneDrive\Desktop\Parts&Service\TEST_READY.md`) following the format in TEST_INFRA.md and PROJECT.md.
3. Write your report to:
   c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\test_writer_m_test\report.md
   and write a standard handoff in:
   c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\test_writer_m_test\handoff.md
Send a completion message back to the orchestrator when finished.
