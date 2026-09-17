// (:Machine)-[:HAS_APPLICATION]->(:Application) — 328 relationships expected.
// data_class is always "DERIVED (category-level official statement applied to
// each machine in that category)" for every row in this sheet — the source's
// own README states applications are published per-category, not per-model,
// so this relationship type is honestly 100% derived. Never presented as if
// it were a per-machine exact statement.
LOAD CSV WITH HEADERS FROM 'file:///applications.csv' AS row
MATCH (m:Machine {machine_id: row.`Machine ID`})
MATCH (a:Application {name: row.Application})
MERGE (m)-[r:HAS_APPLICATION]->(a)
SET r.data_class  = row.`Data Class`,
    r.confidence  = row.Confidence,
    r.source_id   = row.`Source ID`;
