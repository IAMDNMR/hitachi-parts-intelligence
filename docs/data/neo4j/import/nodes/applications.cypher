// Applications — 328 rows in the source CSV, but this MERGEs on the
// canonicalized name, so it converges to exactly 29 distinct Application
// nodes (verified in FINAL_GRAPH_SCHEMA.md §3). The Machine->Application
// relationship (with its per-row evidence) is built separately in
// relationships/machine_application.cypher — this file creates the node only.
LOAD CSV WITH HEADERS FROM 'file:///applications.csv' AS row
MERGE (a:Application {name: row.Application})
SET a.application_type = row.`Application Type`;
