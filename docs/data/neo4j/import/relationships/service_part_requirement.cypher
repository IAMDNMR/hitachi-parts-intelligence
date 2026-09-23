// (:Service)-[:REQUIRES_PART]->(:Part) — 11 relationships expected.
// Machine-level detail (per-machine requirement rows) — the primary source
// of truth for this relationship type, per FINAL_GRAPH_SCHEMA.md §7/§11.
// Sheet 13's coarser service-level REQUIRES rows are NOT imported here — see
// relationships/channel_relationships.cypher's header note and
// IMPORT_DESIGN_REPORT.md §10 for why both aren't loaded together.
LOAD CSV WITH HEADERS FROM 'file:///service_part_requirements.csv' AS row
MATCH (s:Service {service_id: row.`Service ID`})
MATCH (p:Part {part_id: row.`Part ID`})
MERGE (s)-[r:REQUIRES_PART {requirement_id: row.`Requirement ID`}]->(p)
SET r.quantity            = row.Quantity,
    r.mandatory_optional  = row.`Mandatory / Optional`,
    r.consumable_wear_replacement = row.`Consumable / Wear / Replacement`,
    r.data_class          = row.`Data Class`,
    r.source_id           = row.`Source ID`,
    r.confidence          = row.Confidence;
