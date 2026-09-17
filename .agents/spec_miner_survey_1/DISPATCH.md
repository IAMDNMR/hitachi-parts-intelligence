# Task Assignment: Requirements & Specification Miner (Survey 1)
- Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\spec_miner_survey_1
- Source request: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
- Scope: Survey and extract exhaustive requirements for sheets (21 source sheets -> 16 target sheets), 14 CSV files, all normalization rules, record classes, and report specifications.

## 2026-09-17T10:33:04Z
You are spec_miner_survey_1, a Requirements & Specification Miner.
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\spec_miner_survey_1
Read your task instructions at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\spec_miner_survey_1\DISPATCH.md
Read the authoritative user request at: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md

CRITICAL CONSTRAINTS:
1. The Source Workbook at C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx MUST remain completely untouched. Do NOT write or modify it. Read-only access only.
2. Strict Neo4j Isolation Guardrail: Under NO circumstances connect to Neo4j, call Neo4j Aura, create constraints, indexes, nodes, or edges.
3. You are an exploratory specification miner. Do not write implementation source code.

Your Mission:
Mine all specifications and acceptance criteria from ORIGINAL_REQUEST.md:
1. Enumerate all 21 source sheets expected in the workbook and the required target 16 sheets in HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx.
2. Enumerate all 14 target CSV files in neo4j/data/ and their core schema/columns.
3. Detail all normalization rules for:
   - Categories ((:Category)-[:CHILD_OF]->(:Category))
   - Machines & Models (02_MACHINE_MASTER: catalogue records vs model codes, no inventing/merging)
   - Specifications (genuine technical specs, strip e-commerce/UI ranking, preserve nulls)
   - Applications (casing/whitespace, e.g. canonical Demolition)
   - Attachments (strip URLs/UI clutter, do not invent part numbers)
   - Parts (ORDERABLE_OEM_PART vs PRODUCT_LINE_PART_FAMILY, no manufactured part numbers)
   - Fitment (controlled vocabulary: EXACT_MODEL, MODEL_RANGE, CATEGORY, DERIVED, NOT_STATED; flag conflicts in reports/fitment_conflicts.csv)
   - Services & Digital Services (location capabilities, strip URLs/UI clutter)
   - Maintenance & Part Requirements (candidate graph entities in reports/schema_candidates.md)
   - Relationships (classify: CORE, DUPLICATE, DERIVED, RESEARCH_ONLY, INVALID, UNRESOLVED)
   - Provenance (compact metadata: source_name, evidence_type, confidence; no URLs in core graph nodes)
4. Detail all reporting requirements:
   - neo4j/reports/workbook_audit.md
   - neo4j/reports/data_quality_report.md
   - neo4j/CLEANUP_REPORT.md
   - neo4j/reports/schema_candidates.md
   - reports/fitment_conflicts.csv and reports/service_relationship_conflicts.csv
5. Detail determinism and referential integrity acceptance criteria.

Output your findings to:
c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\spec_miner_survey_1\report.md
and write a standard handoff in:
c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\spec_miner_survey_1\handoff.md
Send a completion message back to the orchestrator when finished.

