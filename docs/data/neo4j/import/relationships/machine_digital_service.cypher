// (:Machine)-[:HAS_DIGITAL_SERVICE]->(:DigitalService) — 616 relationships
// expected. Every one of the 616 source rows becomes one relationship
// instance between 77 Machines and 8 DigitalService nodes.
LOAD CSV WITH HEADERS FROM 'file:///digital_services.csv' AS row
MATCH (m:Machine {machine_id: row.`Machine ID`})
MATCH (d:DigitalService {digital_service_id: row.`Digital Service ID`})
MERGE (m)-[r:HAS_DIGITAL_SERVICE]->(d)
SET r.applicability = row.Applicability,
    r.data_class     = row.`Data Class`,
    r.source_id      = row.`Source ID`;
