// (:Machine)-[:BELONGS_TO]->(:Category) — 77 relationships expected.
// Sourced from machines.csv's own Category ID column (cross-checked against
// relationships.csv's 77 BELONGS_TO rows in FINAL_GRAPH_SCHEMA.md §7 — exact
// match). Requires categories.cypher and machines.cypher to have run first.
LOAD CSV WITH HEADERS FROM 'file:///machines.csv' AS row
MATCH (m:Machine {machine_id: row.`Machine ID`})
MATCH (c:Category {category_id: row.`Category ID`})
MERGE (m)-[r:BELONGS_TO]->(c)
SET r.source_id = row.`Source ID`;

// (:Category)-[:CHILD_OF]->(:Category) — 16 relationships expected (17
// categories minus the 1 root, "Machinery", whose own Parent Category value
// is the literal sentinel "(root)", not a real parent — excluded, not
// resolved to a fake self-loop or fabricated root link).
// Parent Category holds a Category ID (verified directly against the data —
// NOT a category name, which was the wrong assumption on the first pass).
LOAD CSV WITH HEADERS FROM 'file:///categories.csv' AS row
WITH row WHERE row.`Parent Category` IS NOT NULL AND row.`Parent Category` <> '' AND row.`Parent Category` <> '(root)'
MATCH (child:Category {category_id: row.`Category ID`})
MATCH (parent:Category {category_id: row.`Parent Category`})
MERGE (child)-[r:CHILD_OF]->(parent)
SET r.source_id = row.`Source ID`;
