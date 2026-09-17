// (:Attachment)-[:FITS]->(:Machine) — model-level, resolved via real evidence.
//
// attachments.csv's "Compatible Machine Model" holds comma/semicolon-separated
// model-code TEXT (e.g. "EX1200-7, EX2000-7, ..."), not a Machine ID. Resolving
// that text to real Machine nodes needs the model-code -> machine_id mapping
// already produced (and reviewed) in MODEL_CODE_INVENTORY.csv from the
// reconciliation phase — reused here rather than re-derived, so this can never
// silently diverge from the approved reconciliation.
//
// Only 7 of the 17 attachments have Compatible Machine Model populated; the
// other 10 are category-level only (see IMPORT_DESIGN_REPORT.md §13 — category
// text is NOT resolved to Category edges in this phase, kept as a property).
//
// Step 1: stage the model-code -> machine_id lookup as temporary helper nodes.
LOAD CSV WITH HEADERS FROM 'file:///MODEL_CODE_INVENTORY.csv' AS row
MERGE (l:_ModelCodeLookup {code: row.parsed_model_code, machine_id: row.machine_id});

// Step 2: resolve each attachment's Compatible Machine Model text against the
// lookup and create the FITS edge for every match.
LOAD CSV WITH HEADERS FROM 'file:///attachments.csv' AS row
WITH row WHERE row.`Compatible Machine Model` IS NOT NULL AND row.`Compatible Machine Model` <> ''
MATCH (a:Attachment {attachment_id: row.`Attachment ID`})
UNWIND [x IN split(replace(row.`Compatible Machine Model`, ';', ','), ',') | trim(x)] AS raw_code
MATCH (l:_ModelCodeLookup {code: raw_code})
MATCH (m:Machine {machine_id: l.machine_id})
MERGE (a)-[r:FITS]->(m)
SET r.evidence   = 'MODEL',
    r.confidence = row.Confidence,
    r.source_id  = row.`Source ID`;

// Step 3: remove the temporary helper nodes — they are staging only, not part
// of the approved node model (FINAL_GRAPH_SCHEMA.md lists no such label).
MATCH (l:_ModelCodeLookup) DETACH DELETE l;

// Note: raw_code fragments that don't match any code in MODEL_CODE_INVENTORY
// (e.g. free-text qualifiers like "ZX10 to ZX85 (as stated)" on ATT-005, or
// "and their Electric Drive variants" trailing text on ATT-002) are silently
// skipped by the MATCH — not resolved, not invented. See IMPORT_DESIGN_REPORT.md
// §13 for the exact list of unresolved fragments found during the dry run.
