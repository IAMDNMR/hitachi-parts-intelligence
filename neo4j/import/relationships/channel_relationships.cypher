// Small, explicit, non-deferred edges from 13_AFTER_SALES_RELATIONSHIPS that
// don't have their own dedicated detail sheet. All read directly from
// relationships.csv, filtered by Relationship type. relationship_class on
// every row preserves CORE vs DERIVED — see IMPORT_DESIGN_REPORT.md §9.
//
// Explicitly NOT included here (approved decision #3 — deferred):
// RECEIVES, USES, FITS (sheet-13 version), PROVIDES_CATALOGUE_FOR.

// (:Service)-[:DELIVERED_BY]->(:Channel) — 23 relationships expected.
// provider_detail carries the per-service "To Name" text (e.g. "Yes (Reman
// centre)" for SVC-016, "Yes (BNP Paribas Leasing Solutions; DLL)" for
// SVC-022) — this is a per-(Service,Channel) fact, not a Channel-level one,
// which is why it lives here rather than on the Channel node. See
// neo4j/FINAL_PRE_IMPORT_REVIEW.md item 2.
LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' AS row
WITH row WHERE row.Relationship = 'DELIVERED_BY'
MATCH (s:Service {service_id: row.`From ID`})
MATCH (c:Channel {channel_id: row.`To ID`})
MERGE (s)-[r:DELIVERED_BY]->(c)
SET r.relationship_class = row.relationship_class,
    r.provider_detail    = row.`To Name`,
    r.data_class         = row.`Data Class`,
    r.source_id          = row.`Source ID`;

// (:DigitalService)-[:NOTIFIES]->(:Channel) — 2 relationships expected.
LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' AS row
WITH row WHERE row.Relationship = 'NOTIFIES'
MATCH (d:DigitalService {digital_service_id: row.`From ID`})
MATCH (c:Channel {channel_id: row.`To ID`})
MERGE (d)-[r:NOTIFIES]->(c)
SET r.relationship_class = row.relationship_class,
    r.data_class         = row.`Data Class`,
    r.source_id          = row.`Source ID`;

// (:DigitalService)-[:SUPPORTS]->(:Service) — 2 relationships expected.
LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' AS row
WITH row WHERE row.Relationship = 'SUPPORTS'
MATCH (d:DigitalService {digital_service_id: row.`From ID`})
MATCH (s:Service {service_id: row.`To ID`})
MERGE (d)-[r:SUPPORTS]->(s)
SET r.relationship_class = row.relationship_class,
    r.data_class         = row.`Data Class`,
    r.source_id          = row.`Source ID`;

// (:DigitalService)-[:INTEGRATES]->(:DigitalService) — 1 relationship expected.
LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' AS row
WITH row WHERE row.Relationship = 'INTEGRATES'
MATCH (from:DigitalService {digital_service_id: row.`From ID`})
MATCH (to:DigitalService {digital_service_id: row.`To ID`})
MERGE (from)-[r:INTEGRATES]->(to)
SET r.relationship_class = row.relationship_class,
    r.data_class         = row.`Data Class`,
    r.source_id          = row.`Source ID`;

// (:Attachment)-[:AFFECTS_MAINTENANCE_OF]->(:Part) — 1 relationship expected.
LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' AS row
WITH row WHERE row.Relationship = 'AFFECTS_MAINTENANCE_OF'
MATCH (a:Attachment {attachment_id: row.`From ID`})
MATCH (p:Part {part_id: row.`To ID`})
MERGE (a)-[r:AFFECTS_MAINTENANCE_OF]->(p)
SET r.relationship_class = row.relationship_class,
    r.data_class         = row.`Data Class`,
    r.source_id          = row.`Source ID`;
