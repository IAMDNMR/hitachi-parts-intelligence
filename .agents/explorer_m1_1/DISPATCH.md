# Task Assignment: Explorer M1-1 (Discovery & Source Audit)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1
- Milestone: M1 (Discovery & Pre-Cleaning Source Audit)
- Scope: Formulate implementation plan and technical strategy for `audit_workbook.py` and `neo4j/reports/workbook_audit.md`.
- Original request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Project scope: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md

## 2026-09-17T10:42:04Z
You are explorer_m1_1, an Explorer for Milestone 1 (Discovery & Source Audit).
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1\DISPATCH.md
Read the authoritative user request at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
Read the project architecture at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md
Read previous survey findings at:
- c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\spec_miner_survey_1\report.md
- c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_2\report.md
- c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_3\report.md

CRITICAL CONSTRAINTS:
1. Source Workbook (C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx) must remain completely untouched.
2. Strict Neo4j Isolation: Under NO circumstances connect to Neo4j.
3. You are an Explorer: recommend implementation strategy, architecture, and verification steps. Do NOT implement production code.

Your Mission:
Design the implementation strategy for `audit_workbook.py` and `neo4j/reports/workbook_audit.md`:
1. Outline the modular structure for `audit_workbook.py` (CLI parsing, source hash verification, openpyxl read-only streaming, metrics computation, markdown formatting).
2. Detail how every one of the 21 sheets will be audited for row/col count, column headers, non-empty/empty counts, duplicate IDs, suspicious/URL fields, and technical/relationship classification.
3. Specify the exact post-execution SHA-256 and timestamp check to prove the source file was not modified.
4. Output your findings to `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_1\report.md` and `handoff.md`.
Send a completion message when finished.
