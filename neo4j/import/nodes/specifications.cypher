// Specifications — 1635 rows expected.
// value_stated preserves the "was this explicitly NOT PUBLICLY STATED" fact
// separately from the (nulled) value itself — see FINAL_GRAPH_SCHEMA.md §6.
LOAD CSV WITH HEADERS FROM 'file:///specifications.csv' AS row
MERGE (s:Specification {spec_id: row.`Spec ID`})
SET s.machine_id           = row.`Machine ID`,
    s.specification_group  = row.`Specification Group`,
    s.specification_name   = row.`Specification Name`,
    s.specification_value  = row.`Specification Value`,
    s.unit                 = row.Unit,
    s.normalised_value     = row.`Normalised Value`,
    s.value_stated         = toBoolean(row.value_stated),
    s.data_class           = row.`Data Class`,
    s.source_id            = row.`Source ID`,
    s.source_date          = row.`Source Date`;
