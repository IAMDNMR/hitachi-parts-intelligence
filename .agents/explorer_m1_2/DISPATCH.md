# Task Assignment: Explorer M1-2 (Source Immutability & Audit Metrics)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_2
- Milestone: M1 (Discovery & Pre-Cleaning Source Audit)
- Scope: Formulate exact data structures, openpyxl memory-efficient streaming, metric calculations, and determinism controls for `audit_workbook.py`.
- Original request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Project scope: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md

## 2026-09-17T10:42:04Z
You are explorer_m1_2, an Explorer for Milestone 1 (Discovery & Source Audit).
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_2
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_2\DISPATCH.md
Read the authoritative user request at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
Read the project architecture at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md
Read previous survey findings at:
- c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\spec_miner_survey_1\report.md
- c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_2\report.md
- c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_3\report.md

CRITICAL CONSTRAINTS:
1. Source Workbook (C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx) must remain completely untouched.
2. Strict Neo4j Isolation: Under NO circumstances connect to Neo4j.
3. You are an Explorer: do NOT implement production code.

Your Mission:
Design the data structures, metric extraction logic, and determinism controls for `audit_workbook.py`:
1. Detail exact metric collection algorithms: primary key uniqueness detection, empty vs non-empty cell counting, fill rates, URL pattern matching regex, and sentinel value detection.
2. Detail openpyxl memory safety (`read_only=True, data_only=True`), handling potential merged cells, None types, and date objects safely.
3. Detail how to achieve 100% determinism (static report header with input SHA-256, sorted tables, deterministic dictionary key iteration, LF newlines).
4. Output your findings to `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_2\report.md` and `handoff.md`.
Send a completion message when finished.
