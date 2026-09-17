# Task Assignment: Milestone 1 Challenger 1 (challenger_m1_1)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\challenger_m1_1
- Role: Adversarial Verifier and Stress Tester for Milestone 1
- Target Artifacts: `audit_workbook.py`, `neo4j/reports/workbook_audit.md`
- Mission: Empirically stress-test `audit_workbook.py`:
  - CLI edge cases (non-existent file, invalid flags, directory path as input)
  - Determinism stress test (run twice, hash compare)
  - Source file immutability verification (verify zero bytes touched)
  - Strict Neo4j isolation verification (zero socket connections, zero drivers)
- Original Request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Project Scope: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md

## 2026-09-17T10:54:20Z
You are challenger_m1_1, Milestone 1 Adversarial Verifier 1.
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\challenger_m1_1
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\challenger_m1_1\DISPATCH.md
Read the authoritative user request at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
Read the project scope at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md

CRITICAL CONSTRAINTS:
1. Source Workbook (C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx) must remain completely untouched.
2. Strict Neo4j Isolation: Under NO circumstances connect to Neo4j.

Your Mission:
Empirically stress-test `audit_workbook.py`:
1. Test CLI boundary conditions:
   - Missing arguments / invalid flag handling (assert exit code 1)
   - Non-existent input file (assert exit code 2)
2. Test double-run determinism:
   - Run `audit_workbook.py -o test_run1.md` and `audit_workbook.py -o test_run2.md`
   - Assert SHA-256(test_run1.md) == SHA-256(test_run2.md) bit-for-bit
3. Test source workbook immutability:
   - Verify SHA-256 and modification time of source workbook before and after execution
4. Test strict Neo4j isolation:
   - Verify zero socket connections to port 7687, zero `neo4j` module imports
5. State your verdict: APPROVE or REQUEST_CHANGES.
Output to `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\challenger_m1_1\report.md` and `handoff.md`. Send completion message when done.
