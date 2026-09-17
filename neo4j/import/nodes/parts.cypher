// Parts — 43 rows expected: 20 ORDERABLE_OEM_PART + 23 PRODUCT_LINE_PART_FAMILY.
// record_class is the load-bearing property (FINAL_GRAPH_SCHEMA.md §14) — a
// family record's part_number is null here exactly as it is in the source;
// nothing manufactures a SKU for it.
LOAD CSV WITH HEADERS FROM 'file:///parts.csv' AS row
MERGE (p:Part {part_id: row.`Part ID`})
SET p.part_number          = row.`Part Number`,
    p.part_name            = row.`Part Name`,
    p.part_category        = row.`Part Category`,
    p.part_subcategory     = row.`Part Subcategory`,
    p.component_assembly   = row.`Component / Assembly`,
    p.genuine_hitachi_part = row.`Genuine Hitachi Part`,
    p.consumable           = row.Consumable,
    p.wear_part            = row.`Wear Part`,
    p.replacement_part     = row.`Replacement Part`,
    p.service_part         = row.`Service Part`,
    p.attachment_part      = row.`Attachment Part`,
    p.description          = row.Description,
    p.supersedes_part_number = row.`Supersedes Part Number`,
    p.superseded_by        = row.`Superseded By`,
    p.record_class         = row.record_class,
    p.data_class           = row.`Data Class`,
    p.source_id            = row.`Source ID`,
    p.confidence           = row.Confidence,
    p.source_date          = row.`Source Date`;
