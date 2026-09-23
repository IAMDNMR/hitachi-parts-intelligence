# Supplier data model - ready for real SAP purchasing data

Nothing here is loaded today. The graph already holds the SAP supplier master (1,720 suppliers: number, name, city, country) and
73 **synthetic demo** `SUPPLIED_BY` links. Real data must NOT be mixed into the demo layer: real links carry `synthetic=false`
(or no synthetic flag), demo links carry `synthetic=true, data_source='SYNTHETIC_DEMO'`. Disruption/supplier-risk code already reads
that flag and reports `REAL` vs `SYNTHETIC_DEMO` per link.

## Input needed from SAP (purchasing / source list / info records)
| Field | Used for |
|---|---|
| supplier number (LIFNR) | match `Supplier.supplier_number` (already loaded) |
| material number | match `Part.part_number` |
| source-list validity dates, fixed-source flag, quota % | `share_pct`, `role` (SOLE / PRIMARY / SECONDARY), validity |
| purchasing info record: lead time, MOQ | supplier lead time (feeds RFQ `lead_time`) |
| plant / storage location | which depot |
| (optional) assembly / BOM component -> supplier | supplier -> assembly |

## Relationships to populate
| Relationship | Properties | Enables |
|---|---|---|
| `(Part)-[:SUPPLIED_BY {share_pct, role, valid_from, valid_to, lead_time_days, source:'SAP_SOURCE_LIST', synthetic:false}]->(Supplier)` | see left | supplier -> part, sole/dual source, supplier dependency, supplier-unavailable scenario |
| `(Supplier)-[:SUPPLIES_ASSEMBLY {source, synthetic:false}]->(Assembly)` (only if SAP/engineering BOM provides it) | | supplier -> assembly |
| `(Supplier)-[:LOCATED_IN]->(City)` | already loaded | geographic exposure once part links are real |

## Derived (no extra data)
Supplier dependency = for each part, the set of `SUPPLIED_BY` suppliers and their shares; a supplier's exposure = parts (and via the BOM,
assemblies and machine models) that lose their only usable source. KPI `Supplier-to-part coverage` moves from 0% as links load.
