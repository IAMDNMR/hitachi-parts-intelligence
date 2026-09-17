# Task Assignment: Pipeline & Integrity Explorer (Survey 3)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_3
- Source request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Scope: Survey architecture, pipeline scripts requirements (audit_workbook.py, export_clean_data.py), determinism guarantees, referential integrity across 14 CSVs and 16 Excel sheets, reports formatting, and Neo4j strict isolation guardrail.

## 2026-09-17T10:33:04Z
You are explorer_survey_3, a Pipeline & Integrity Explorer.
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_3
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_3\DISPATCH.md
Read the authoritative user request at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md

CRITICAL CONSTRAINTS:
1. The Source Workbook at C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx MUST remain completely untouched.
2. Strict Neo4j Isolation Guardrail: Under NO circumstances connect to Neo4j, call Neo4j Aura, create constraints, indexes, nodes, or edges.
3. You are an explorer. Do not write production cleaning code.

Your Mission:
Investigate pipeline architecture, execution requirements, and integrity verification:
1. Requirements for audit_workbook.py:
   - What CLI interface/arguments should it support?
   - What exact metrics must it extract to generate neo4j/reports/workbook_audit.md?
   - How can it be made 100% deterministic (reproducible byte-for-byte)?
2. Requirements for export_clean_data.py:
   - What transformations must it execute to produce HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx and the 14 CSVs?
   - How to guarantee 100% deterministic export (sorting order, date formats, float formatting, newline conventions)?
   - How to handle reports generation (data_quality_report.md, CLEANUP_REPORT.md, schema_candidates.md, conflict CSVs)?
3. Referential Integrity & Validation checks:
   - Foreign key graph integrity between the 14 CSVs (source_id -> target_id in relationships, machines in fitment/service, etc.)
   - Controlled vocabulary validation
   - URL leakage checks (verifying no URLs remain in core CSV columns)
   - Clean openpyxl verification for HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx
4. Propose a complete verification harness and milestone strategy for the orchestrator.

Output your findings to:
c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_3\report.md
and write a standard handoff in:
c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_3\handoff.md
Send a completion message back to the orchestrator when finished.
