// DigitalService — 616 rows in the source CSV (one per Machine×DigitalService
// pair), but MERGE on digital_service_id converges to exactly 8 distinct
// nodes (verified count — see FINAL_GRAPH_SCHEMA.md §3, the correction to
// schema_candidates.md's original 616). The Machine relationship is built
// separately in relationships/machine_digital_service.cypher.
LOAD CSV WITH HEADERS FROM 'file:///digital_services.csv' AS row
MERGE (d:DigitalService {digital_service_id: row.`Digital Service ID`})
SET d.service_name        = row.`Service Name`,
    d.capability            = row.Capability,
    d.machine_data          = row.`Machine Data`,
    d.alert_monitoring      = row.`Alert / Monitoring`,
    d.maintenance_support   = row.`Maintenance Support`,
    d.diagnostic_support    = row.`Diagnostic Support`,
    d.parts_support         = row.`Parts Support`,
    d.dealer_support        = row.`Dealer Support`,
    d.description           = row.Description,
    d.data_class            = row.`Data Class`,
    d.source_id             = row.`Source ID`,
    d.source_date           = row.`Source Date`;
