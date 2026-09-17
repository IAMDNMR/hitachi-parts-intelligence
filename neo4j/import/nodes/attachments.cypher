// Attachments — 17 rows expected.
// Compatible Machine Model / Compatible Machine Category are kept as raw text
// properties here (not resolved into edges yet — see relationships/
// machine_attachment.cypher for the model-level edges that ARE resolvable,
// and IMPORT_DESIGN_REPORT.md §13 for why category-level text is not).
LOAD CSV WITH HEADERS FROM 'file:///attachments.csv' AS row
MERGE (a:Attachment {attachment_id: row.`Attachment ID`})
SET a.attachment_name       = row.`Attachment Name`,
    a.attachment_type       = row.`Attachment Type`,
    a.attachment_category   = row.`Attachment Category`,
    a.compatible_machine_model    = row.`Compatible Machine Model`,
    a.compatible_machine_category = row.`Compatible Machine Category`,
    a.mounting_coupling_type = row.`Mounting / Coupling Type`,
    a.hydraulic_requirement  = row.`Hydraulic Requirement`,
    a.weight                 = row.Weight,
    a.dimensions             = row.Dimensions,
    a.capacity               = row.Capacity,
    a.purpose_application    = row.`Purpose / Application`,
    a.detachable_fixed       = row.`Detachable / Fixed`,
    a.data_class             = row.`Data Class`,
    a.source_id              = row.`Source ID`,
    a.confidence             = row.Confidence,
    a.source_date            = row.`Source Date`;
