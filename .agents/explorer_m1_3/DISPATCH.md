# Task Assignment: Explorer M1-3 (Audit Report Format & CLI Interface)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_3
- Milestone: M1 (Discovery & Pre-Cleaning Source Audit)
- Scope: Formulate exact Markdown output formatting for `neo4j/reports/workbook_audit.md`, CLI argument parsing, return codes, and error handling.
- Original request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Project scope: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\PROJECT.md

## 2026-09-17T10:42:04Z
You are explorer_m1_3, an Explorer for Milestone 1 (Discovery & Source Audit).
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_3
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_3\DISPATCH.md
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
Design the report format and validation criteria for `audit_workbook.py`:
1. Provide the exact Markdown template and table structures for `neo4j/reports/workbook_audit.md` covering all 21 sheets.
2. Define the CLI options, help messages, argument parser, and exit code contract (0=success, 1=bad args, 2=missing source, 3=source modified/hash mismatch).
3. Specify verification commands and acceptance tests for the worker and reviewer.
4. Output your findings to `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_3\report.md` and `handoff.md`.
Send a completion message when finished.
