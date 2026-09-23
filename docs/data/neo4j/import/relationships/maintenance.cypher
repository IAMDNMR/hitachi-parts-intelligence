// Maintenance — REVISED after final pre-import review (see
// neo4j/FINAL_PRE_IMPORT_REVIEW.md item 1). The previous design used a
// self-relationship (:Part)-[:HAS_MAINTENANCE_GUIDELINE]->(:Part), which
// review correctly identified as semantically awkward. This version instead
// attaches maintenance data as parallel LIST properties directly on Part —
// no new node, no self-relationship, and (unlike a flat scalar SET) it
// correctly supports the one part (PT-032) that has two guidelines without
// either overwriting one or forcing an artificial second entity.
//
// Confirmed not attachable to Machine (every row's Machine ID is the source's
// own scope-descriptor sentinel "ALL - see Applies To") or to Service (no
// Service ID column exists in this sheet, and only 1 of 10 rows — MS-010 —
// has strong-enough textual evidence to link to a specific Service; doing
// that for 1 row and not the other 9 would be an inconsistent special case,
// not a schema pattern — left as a documented limitation, not implemented).
//
// 9 of 10 rows resolve to at least one real Part via "Required Part" text
// (split on ';', trailing parenthetical qualifiers stripped). MS-005 ("Daily
// inspection", no consumable) has none and is intentionally not represented.
LOAD CSV WITH HEADERS FROM 'file:///maintenance.csv' AS row
WITH row WHERE row.`Required Part` IS NOT NULL AND row.`Required Part` <> ''
UNWIND [x IN split(row.`Required Part`, ';') | trim(split(trim(x), '(')[0])] AS part_name_fragment
MATCH (p:Part) WHERE toLower(p.part_name) CONTAINS toLower(part_name_fragment)
SET p.maintenance_ids              = coalesce(p.maintenance_ids, [])              + row.`Maintenance ID`,
    p.maintenance_activities       = coalesce(p.maintenance_activities, [])       + row.`Maintenance Activity`,
    p.maintenance_intervals        = coalesce(p.maintenance_intervals, [])        + row.Interval,
    p.maintenance_interval_units   = coalesce(p.maintenance_interval_units, [])   + row.`Interval Unit`,
    p.maintenance_applies_to       = coalesce(p.maintenance_applies_to, [])       + row.`Applies To (as stated)`,
    p.maintenance_components       = coalesce(p.maintenance_components, [])      + row.Component,
    p.maintenance_data_classes     = coalesce(p.maintenance_data_classes, [])    + row.`Data Class`,
    p.maintenance_source_ids       = coalesce(p.maintenance_source_ids, [])      + row.`Source ID`,
    p.maintenance_confidences      = coalesce(p.maintenance_confidences, [])     + row.Confidence;
// All 9 arrays stay index-aligned per part (position i across every array
// describes the same one guideline) — e.g. PT-032 ends up with 2-element
// arrays (MS-002 at index 0, MS-003 at index 1), nothing overwritten.
//
// NOT RUN TWICE WITHOUT RESETTING: unlike every other file in this design,
// list-append via `coalesce(...) + value` is NOT idempotent — re-running this
// file would duplicate entries. If a re-run is ever needed, first
// `MATCH (p:Part) REMOVE p.maintenance_ids, p.maintenance_activities, ...`
// (all 9 properties) before reloading. This limitation is called out
// explicitly rather than silently shipped — see
// neo4j/FINAL_PRE_IMPORT_REVIEW.md item 1 and IMPORT_DESIGN_REPORT.md §7.
