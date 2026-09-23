// Categories — 17 rows expected. Idempotent: safe to re-run.
// Copy neo4j/data/categories.csv into the Aura/Neo4j import directory first.
LOAD CSV WITH HEADERS FROM 'file:///categories.csv' AS row
MERGE (c:Category {category_id: row.`Category ID`})
SET c.parent_category        = row.`Parent Category`,
    c.category_name          = row.`Category Name`,
    c.official_category_name = row.`Official Category Name`,
    c.category_description   = row.`Category Description`,
    c.product_type            = row.`Product Type`,
    c.machine_configuration   = row.`Machine Configuration`,
    c.on_road_off_road        = row.`On-road / Off-road`,
    c.primary_application     = row.`Primary Application`,
    c.source_id               = row.`Source ID`,
    c.source_date             = row.`Source Date`;
