// =============================================================================
// Neo4j indexes — HCME After-Sales graph
// NOT EXECUTED. Design artifact only.
// Every uniqueness constraint above already creates a backing index on that
// property — these are the ADDITIONAL indexes needed for lookup patterns the
// constraints don't cover. No index is created "just in case"; each one below
// is tied to a named query pattern from FINAL_GRAPH_SCHEMA.md §17 or the
// Parts Store / Service journeys.
// =============================================================================

// Part lookup by the real published part number (Parts Store: "search this
// part number"). Only meaningful for ORDERABLE_OEM_PART rows, but the index
// covers the property regardless — family rows simply have a null value.
CREATE INDEX part_number_lookup IF NOT EXISTS
FOR (n:Part) ON (n.part_number);

// Part name search (Parts Store: free-text search by name).
CREATE INDEX part_name_lookup IF NOT EXISTS
FOR (n:Part) ON (n.part_name);

// Machine lookup by model text (Service/Parts Store: "find my machine" by
// typing its model code — must be a non-unique index since EX2000-7 maps to
// two Machine nodes, by design; see IMPORT_KEY_MAP.md).
CREATE INDEX machine_model_lookup IF NOT EXISTS
FOR (n:Machine) ON (n.model);

// Machine lookup by category text (Service/Parts Store category filters).
CREATE INDEX machine_category_lookup IF NOT EXISTS
FOR (n:Machine) ON (n.machine_category);

// Service lookup by name (Service journey: service capability search).
CREATE INDEX service_name_lookup IF NOT EXISTS
FOR (n:Service) ON (n.service_name);

// Attachment lookup by name (Parts Store: attachment browsing).
CREATE INDEX attachment_name_lookup IF NOT EXISTS
FOR (n:Attachment) ON (n.attachment_name);

// Category lookup by name (both journeys: category-level navigation).
CREATE INDEX category_name_lookup IF NOT EXISTS
FOR (n:Category) ON (n.category_name);

// Not created: an index on every property "just in case" (Step 4 explicitly
// warns against this). No index on Specification.specification_value (free
// text, not a lookup key), no index on any Source ID / Confidence / Data
// Class property (provenance is read alongside a fact already found by its
// own key, never used to search FOR that fact).
