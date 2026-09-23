// (:Machine)-[:HAS_SERVICE]->(:Service) — 1694 relationships expected.
// applicability carries ALL_MACHINES_STATED/CATEGORY/NOT_STATED. NOT_STATED
// rows (63) are still imported — a query consuming this edge must check
// applicability before treating the service as confirmed available
// (FINAL_GRAPH_SCHEMA.md §6) — they are not excluded here because excluding
// them would silently discard real rows the source does publish, just with a
// "not stated" applicability value.
LOAD CSV WITH HEADERS FROM 'file:///machine_service.csv' AS row
MATCH (m:Machine {machine_id: row.`Machine ID`})
MATCH (s:Service {service_id: row.`Service ID`})
MERGE (m)-[r:HAS_SERVICE]->(s)
SET r.applicability          = row.applicability,
    r.applicability_original = row.applicability_original,
    r.service_type           = row.`Service Type`,
    r.service_location       = row.`Service Location`,
    r.trigger                = row.Trigger,
    r.interval_officially_stated = row.`Interval (officially stated)`,
    r.data_class             = row.`Data Class`,
    r.source_id              = row.`Source ID`,
    r.confidence             = row.Confidence;
