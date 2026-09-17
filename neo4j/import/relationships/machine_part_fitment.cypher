// (:Machine)-[:HAS_PART_FITMENT]->(:Part) — 944 relationships expected.
// evidence carries the controlled vocabulary (EXACT_MODEL/MODEL_RANGE/
// CATEGORY/NOT_STATED) computed in the cleaning phase; evidence_original
// preserves the source's own free text. fitment_type (Maintenance/
// Replacement/Accessory/Standard/Wear) is a SEPARATE axis — the nature of the
// part, not the fitment confidence — and both are kept, never conflated
// (FINAL_GRAPH_SCHEMA.md §5).
LOAD CSV WITH HEADERS FROM 'file:///machine_part_fitment.csv' AS row
WITH row WHERE row.`Machine ID` <> 'NOT IN CURRENT CATALOGUE'
MATCH (m:Machine {machine_id: row.`Machine ID`})
MATCH (p:Part {part_id: row.`Part ID`})
MERGE (m)-[r:HAS_PART_FITMENT {fitment_id: row.`Fitment ID`}]->(p)
SET r.evidence           = row.evidence,
    r.evidence_original  = row.evidence_original,
    r.fitment_type       = row.`Fitment Type`,
    r.assembly           = row.Assembly,
    r.installation_context = row.`Installation Context`,
    r.position_location  = row.`Position / Location`,
    r.data_class         = row.`Data Class`,
    r.source_id          = row.`Source ID`,
    r.confidence         = row.Confidence;
// The one row whose Machine ID is the source's own scope-descriptor sentinel
// ("NOT IN CURRENT CATALOGUE", Fitment ID FIT-0032) is excluded — it is not a
// broken reference, it is the source honestly stating this fitment applies to
// a part/model combination outside the current catalogue. See
// MODEL_CODE_RECONCILIATION_REPORT.md-adjacent finding in
// neo4j/reports/data_quality_report.md's "Scope-descriptor values" section.
