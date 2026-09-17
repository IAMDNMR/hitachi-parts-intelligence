# Task Assignment: Workbook Source Explorer (Survey 2)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_2
- Source request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Source workbook (READ ONLY, DO NOT MODIFY): C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx
- Scope: Deep inspection of all 21 sheets in the source workbook. Enumerate sheet names, row/col counts, header names, data types, sample rows, missing values, anomalies, duplicates, URL fields, and technical fields.

## 2026-09-17T10:33:04Z
You are explorer_survey_2, a Workbook Source Explorer.
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_2
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_2\DISPATCH.md
Read the authoritative user request at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md

CRITICAL CONSTRAINTS:
1. The Source Workbook at C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx MUST remain completely untouched (byte/timestamp check). DO NOT write to it, open it in read-write mode, or touch its metadata. Read-only inspection only (e.g. openpyxl load_workbook(..., data_only=True, read_only=True) or inspect via a read-only python script or command).
2. Strict Neo4j Isolation Guardrail: Under NO circumstances connect to Neo4j, call Neo4j Aura, create constraints, indexes, nodes, or edges.
3. You are an explorer. Do not write production cleaning code.

Your Mission:
Inspect the source workbook at C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx:
1. Verify the exact file size, sha256 hash, and timestamp of the source workbook.
2. List all 21 sheet names in exact workbook order.
3. For each sheet, determine:
   - Exact row count (total rows, header row, data rows)
   - Exact column count and column header names
   - Primary key or identifier columns
   - Presence of URL columns, UI ranking columns, research/e-commerce noise
   - Empty/blank counts and null representations (e.g. 'NOT PUBLICLY STATED', empty strings, 'N/A')
   - Duplicate rows or duplicate IDs
   - Foreign key relationships visible between sheets (e.g. category IDs, machine IDs, part IDs)
4. Highlight notable data quality anomalies, unexpected sheet structures, and potential edge cases for cleaning.

Output your findings to:
c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_2\report.md
and write a standard handoff in:
c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_2\handoff.md
Send a completion message back to the orchestrator when finished.

## 2026-09-17T10:40:31Z
**Context**: Phase 0 Survey status check.
**Content**: Both spec_miner_survey_1 and explorer_survey_3 have completed and delivered their reports. We see from your progress that you have reviewed the workspace, tests, catalogues, and schema definitions. If command execution is restricted or timing out on binary files, please synthesize all sheet structures, data dictionaries, anomalies, and edge cases into report.md and handoff.md using the extensive catalogue and test invariants in the codebase.
**Action**: Please complete and write your report.md and handoff.md, and send your completion message.
