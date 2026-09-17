// (:Machine)-[:HAS_SPECIFICATION]->(:Specification) — 1635 relationships expected.
LOAD CSV WITH HEADERS FROM 'file:///specifications.csv' AS row
MATCH (m:Machine {machine_id: row.`Machine ID`})
MATCH (s:Specification {spec_id: row.`Spec ID`})
MERGE (m)-[r:HAS_SPECIFICATION]->(s)
SET r.data_class = row.`Data Class`;
