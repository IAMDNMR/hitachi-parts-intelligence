# HCME Europe — Operational Data & KPI Foundation

Status: **PARTIAL — backend complete and verified; frontend not started.** See
Section 24 for exactly what remains. All numbers in this document were
queried live against the running AuraDB graph on 2026-09-23, in the same
session that wrote this report — none are estimated or carried over from an
earlier session.

## 1. Objective

Build a synthetic-but-honestly-labeled operational/commercial context layer
around the real HCME Europe Part + Dealer graph, so five KPI scenarios
(order traceability, cross-catalog matching, order-status query, master-data
consistency, customs flagging) can be demonstrated end-to-end on real Neo4j
data — without ever fabricating real HCME pricing, inventory, order, or
shipment facts, and without rewriting Phase 6 (Allocation + Order) or any
provider contract.

## 2. Existing State (verified at session start)

Live AuraDB label counts before this session's writes:

| Label | Count |
|---|---|
| Part | 68 (60 real CSV-sourced + 8 `CONC6-DBG*` — pre-existing Phase 6 concurrency-test pollution, not created by this session, left untouched) |
| Machine | 77 |
| Allocation | 60 (all Phase 6 test-workflow data, `provenance` not tagged synthetic — pre-existing, untouched) |
| Order | 232 (all `provenance: 'INTERNAL_TEST_WORKFLOW'`, pre-existing Phase 6 test data, untouched) |
| FulfilmentRequest / FulfilmentOption | 148 / 150 |
| InventoryCache / InventoryLedger | 148 / 45 |
| **DealerBranch** | **0** — the 182-row real dataset prepared in the prior session (`docs/data/neo4j/data/dealers.csv`) had **not yet been imported**, confirmed by a live label query, not assumed. |
| Depot, Supplier, CatalogEntry, InventorySnapshot, Shipment, CustomsContext | did not exist |

`backend/app/modules/order/service.py` confirmed the real order state model:
`CREATED -> ACCEPTED -> CANCELLED` (documented in its own docstring, citing
`docs/business-process/ORDER_PROCESS.md §4`), plus an internal pre-`CREATED`
`DRAFT` step that is never a final status. No `ACCEPTED`/`SHIPPED`/`DELIVERED`
transition exists in Phase 6 code today — `SHIPPED`/`DELIVERED` in this
session's synthetic data live on the new `(:Shipment).status` field, not on
`Order.status`, so no new Order state was invented.

## 3. Real HCME Europe Data Available

- 60 real, provenanced `Part` nodes (SRC-039 and others; excludes the 8
  pre-existing `CONC6-DBG*` test nodes).
- 77 real `Machine` nodes, 1,041 real `HAS_PART_FITMENT` relationships.
- **182 real `DealerBranch` nodes — imported this session** (previously
  prepared, never executed). Idempotent MERGE keyed on `dealer_id`,
  source SRC-049 (HCME's public dealer-locator JSON feed).
- **One real `Depot` node — added this session**: Hitachi European Parts
  Centre, Oosterhout, NL. New provenance registered as **SRC-050** in
  `docs/data/neo4j/data/provenance.csv`: HCME's own "Onsite" news article
  (`https://www.hitachicm.com/eu/en/onsite/article/a-future-proof-parts-warehouse/`,
  published 2024-07-09, verified live via browser fetch on 2026-09-23).
  Real published facts captured: 28,000 m² building, 110,000 storage
  locations (up from 73,000 pre-upgrade), ~80,000 distinct parts stocked in
  2024 (up from 68,800 in 2015), logistics partner Neovia, and the
  dispatch-within-24-hours claim. **These are historical, article-published
  facility statistics, not a live inventory feed** — no per-part or current
  stock count is asserted from this node, and the node explicitly says so in
  its own `note` property.

## 4. Real HCME Europe Data Not Public (confirmed, not re-litigated)

Per the two prior research docs (`HCME_PRICING_ORDER_INTEGRATION_RESEARCH.md`,
`HCME_EUROPE_PARTS_AND_DEALER_DATA_RESEARCH.md`), still holds: no public
HCME pricing, no live inventory/stock-by-part API, no order-submission API,
no supplier data, no live shipment/tracking data, no per-part customs data.
This session found one new real fact (Section 3, the Depot's published
statistics) but nothing that changes those conclusions — no live feed of any
kind was found or is claimed.

## 5. Commercial Data Findings

No new commercial (price-list, catalogue-price) research was performed —
not genuinely necessary for the KPI scenarios, and prior research already
confirmed no public HCME Europe pricing exists. Not re-litigated.

## 6. Pricing Findings

Unchanged from prior research: **UNKNOWN / NOT_AVAILABLE**. `PricingProvider`
and `TestPricingProvider` (`backend/app/integrations/contracts/pricing.py`,
`backend/app/integrations/mocks/pricing_mock.py`) were inspected, not
modified. No `(:Price)` node was introduced — none of the five KPI scenarios
required one; every synthetic Order in this session carries
`unitPrice: null`, `pricingStatus: 'NOT_AVAILABLE'`, honestly reflecting
that no pricing source exists, exactly like the real Phase 6 order path when
`TestPricingProvider` returns `NOT_AVAILABLE`.

## 7. Inventory Findings

Existing Phase 4 Availability flow (`backend/app/modules/availability/`) and
Phase 6 `InventoryCache`/`InventoryLedger` were inspected, not modified. A
deliberately **separate** synthetic-only label, `(:InventorySnapshot)`, was
introduced instead of writing demo data into `InventoryCache`/
`InventoryLedger` — those labels are read by real Phase 6/4 code paths, and
writing synthetic stock into them would risk it being treated as live data.
3 `InventorySnapshot` records were seeded (one each at the real Depot, a
real Dealer, and a synthetic Supplier), all `synthetic: true`,
`data_source: 'SYNTHETIC_DEMO'`.

## 8. Fulfilment Findings

Existing Phase 5 Fulfilment workflow (`backend/app/modules/fulfilment/`) was
inspected, not modified. Three synthetic demo chains reuse the **existing**
`FulfilmentRequest`/`FulfilmentOption` labels and field names (mirroring the
exact `CREATE` shape found in `availability/service.py` and
`fulfilment/service.py`) rather than inventing parallel entities, each
tagged `synthetic: true`. Confirmed via code search that no existing route
runs an unfiltered `MATCH (n:FulfilmentRequest)`-style listing query, so
these demo nodes cannot leak into any real Phase 5 UI/endpoint — every real
query is scoped by a specific id already known to the caller.

## 9. Order Findings

Phase 6 `backend/app/modules/order/service.py` was inspected, not modified,
and no Phase 6 service function was called by the seed script (it performs
direct, inert Cypher writes — it never touches the live allocation ledger,
inventory cache, or idempotency store). Three synthetic demo `Order` nodes
reuse the real `Order` label and the real `CREATED`/`ACCEPTED`/`CANCELLED`
state vocabulary (`order-demo-001` ACCEPTED, `order-demo-002` ACCEPTED,
`order-demo-003` CANCELLED). Their ids (`order-demo-*`) can never collide
with real ids (`order-<uuid4>`). All carry
`provenance: 'SYNTHETIC_DEMO_KPI_WORKFLOW'`, `synthetic: true`,
`data_source: 'SYNTHETIC_DEMO'` — distinct from the 232 pre-existing
`provenance: 'INTERNAL_TEST_WORKFLOW'` orders, which were left untouched.

## 10. Shipment Findings

No Phase 7 (production shipment/tracking) exists and none was built here.
Two synthetic `(:Shipment)` nodes were created purely for KPI/graph
demonstration, with the exact fields the spec requested (shipment_id,
status, carrier, tracking_number, origin, destination, eta, shipped_at,
delivered_at, synthetic, data_source), linked `(:Order)-[:HAS_SHIPMENT]->
(:Shipment)-[:SHIPPED_TO]->(:DealerBranch)`. No real carrier/tracking data
was found or claimed — both are demo values (`Demo Carrier Logistics`,
`DEMO-TRACK-000x`).

## 11. Service Findings

`backend/app/db/neo4j/schema.py` and the existing `Service`/
`HAS_SERVICE`/`service_part_requirements.csv` model were inspected. No
changes were made here — the existing real Machine→Service and
Machine→Part(fitment) relationships already support the Parts Intelligence
"Impact" tab (`related_services`, see `service.py::get_graph_insights`), and
no unsupported new Service relationship was needed for any of the five KPI
scenarios in this session's scope.

## 12. Supplier Findings

Confirmed (again, not re-litigated) no real HCME-published supplier data
exists. Two synthetic `(:Supplier)` nodes were created
(`SUP-DEMO-001`, `SUP-DEMO-002`), both `synthetic: true`,
`data_source: 'SYNTHETIC_DEMO'`, `record_class: 'DEMO_SUPPLIER'`, used only
as an alternative `SOURCED_FROM` target to the real Depot for one demo
order.

## 13. Cross-Catalog Findings

No new real cross-reference/supersession evidence was found beyond what
prior research already covered (none). Three synthetic `(:CatalogEntry)`
nodes were created against real Parts (`PT-001`, `PT-002`), each
`synthetic: true`, linked via `CROSS_REFERENCES` or `ALTERNATIVE_FOR`
relationships that also carry `synthetic: true`. No `SUPERSEDES`
relationship instance was created (none was needed for the demo — the
relationship type is referenced defensively in the read query for forward
compatibility, which produces a harmless "relationship type does not exist
yet" notification from Neo4j, not an error).

## 14. Customs Findings

No real HCME shipment customs data exists or was searched for again (out of
scope — no HCME source would plausibly publish it). One synthetic
`(:CustomsContext)` node was created for the one cross-border demo shipment
(Oosterhout, NL → AC Plant Sales, GB), `requires_declaration: true`,
`customs_status: 'PENDING_DECLARATION'`, with an explicit `flag_reason`. The
intra-EU demo shipment (NL → NL) has no `CustomsContext` node at all —
verified by test (`test_customs_flags_kpi5`) — because it should not be
flagged.

## 15. Synthetic Data Boundary

Enforced two ways:
1. **Structural** — every synthetic-only concept got its own new label
   (`Supplier`, `CatalogEntry`, `InventorySnapshot`, `Shipment`,
   `CustomsContext`) rather than being written into a real/Phase-6 label.
   The one exception is intentional and safe: `Order`/`Allocation`/
   `FulfilmentRequest`/`FulfilmentOption` are reused (per the spec's
   explicit instruction to extend, not duplicate, the existing order
   model), distinguished purely by `synthetic: true` + a `-demo-` id infix
   that cannot collide with real ids, and verified to be unreachable by any
   existing unfiltered query (Section 8).
2. **Field-level** — every synthetic node/relationship carries both
   `synthetic: true` and `data_source: 'SYNTHETIC_DEMO'`. This was verified
   with a live query, not assumed (Section 22).

## 16. Neo4j Changes

- `backend/app/db/neo4j/schema.py`: added uniqueness constraints for
  `Depot.depot_id`, `Supplier.supplier_id`, `CatalogEntry.catalog_entry_id`,
  `InventorySnapshot.snapshot_id`, `Shipment.shipment_id`,
  `CustomsContext.customs_context_id`, `DealerBranch.dealer_id` (the last
  one had no constraint anywhere previously). Applied automatically on
  every app startup like the rest of the file (`IF NOT EXISTS`, non-fatal).
- `docs/data/neo4j/scripts/import_dealers.py` (new, checked in): imported
  the 182 real `DealerBranch` rows via the Python driver (MERGE on
  `dealer_id`, idempotent).
- `docs/data/neo4j/scripts/seed_operational_demo_data.py` (new, permanent,
  idempotent): writes the one real Depot node and all synthetic entities
  described above. Verified idempotent by running it twice and by an
  automated test (`test_seed_is_idempotent`).
- `docs/data/neo4j/data/provenance.csv`: added `SRC-050`.

## 17. Parts Intelligence Changes

New module `backend/app/modules/intelligence/context.py` — five read-only
functions (`get_order_context`, `get_order_status`, `get_supply_chain`,
`get_cross_catalog`, `get_customs_flags`, `get_graph_stats`) following the
exact pattern of `service.py::get_graph_insights` (session in, Cypher
traversal, plain dict/dataclass out, `NotFoundError` on missing id). The LLM
provider is never imported or called anywhere in this module — the same
"LLM understands intent only" boundary `service.py` already enforces.
Master-data-consistency verdicts (`MATCH`/`MINOR_DIFFERENCE`/
`SIGNIFICANT_DIFFERENCE`/`UNKNOWN`) are computed by a small deterministic
function (`_classify_difference`), never by the LLM.

## 18. API Changes

Added to `backend/app/api/v1/intelligence.py` (no naming collisions with
the existing `/search` and `/parts/{part_id}/insights` routes):

- `GET /api/v1/intelligence/parts/{part_id}/order-context`
- `GET /api/v1/intelligence/orders/{order_id}/status`
- `GET /api/v1/intelligence/parts/{part_id}/supply-chain`
- `GET /api/v1/intelligence/parts/{part_id}/cross-catalog`
- `GET /api/v1/intelligence/parts/{part_id}/customs`
- `GET /api/v1/intelligence/graph-stats`

All six were smoke-tested end-to-end this session via `TestClient` against
the real app (not mocked) — see Section 22 for the actual response excerpts.

## 19. Frontend Changes

**None. Not started this session** — see Section 24. `GraphInsights.tsx`
and `PartsStore.css` were not touched (the pre-existing frontend jsx→tsx
migration noise was also correctly left alone, per instruction, and is
unrelated to this gap). `npm run test` was run as a baseline/regression
check only (no frontend code was changed): **82 tests, 82 passed, 0
failed** — matches the stated baseline exactly, confirming no regression
from the backend-only changes in this session.

## 20. KPI Scenario Coverage

| KPI | Backend graph structure | Backend API | Deterministic/no-LLM-fabrication verified | Frontend |
|---|---|---|---|---|
| 1. Order traceability | Done (Part→Order→Allocation→FulfilmentRequest→Shipment→DealerBranch) | `/parts/{id}/order-context` | Yes (test) | Not started |
| 2. Cross-catalog matching | Done (synthetic, labeled) | `/parts/{id}/cross-catalog` | Yes (test) | Not started |
| 3. Order status query | Done | `/orders/{id}/status` | Yes (test) | Not started |
| 4. Master-data consistency | Done (MATCH/MINOR/SIGNIFICANT verdicts demonstrated) | `/parts/{id}/cross-catalog` | Yes (test) | Not started |
| 5. Customs flag | Done (cross-border flagged, intra-EU correctly unflagged) | `/parts/{id}/customs` | Yes (test) | Not started |

All five KPIs are backend-complete and independently verified (automated
tests + live API smoke test). None have a UI yet.

## 21. Provenance

Reused the exact existing scheme, no parallel system invented:
- Real records: `source_id` / `confidence` / `data_class` / `source_date` /
  `record_class` (Depot uses `SRC-050`; DealerBranch rows use `SRC-049`,
  already defined).
- Synthetic records: `synthetic: true` + `data_source: 'SYNTHETIC_DEMO'` on
  every node and every relationship this session created among them.

## 22. Validation

Ran directly against the live graph and via `TestClient` in this session
(not estimated):

```
GET /api/v1/intelligence/graph-stats  ->
{
  "real": {"Part": 68, "Machine": 77, "DealerBranch": 182, "Depot": 1,
            "HAS_PART_FITMENT_relationships": 1041},
  "synthetic": {"Supplier": 2, "CatalogEntry": 3, "InventorySnapshot": 3,
                "Order": 3, "Shipment": 2, "CustomsContext": 1},
  "integrity_checks": {
    "synthetic_records_missing_synthetic_flag": 0,
    "real_part_nodes_with_synthetic_property_set": 0,
    "real_dealer_nodes_with_synthetic_property_set": 0
  }
}
```

`GET /api/v1/intelligence/orders/order-demo-001/status`,
`/parts/PT-001/order-context`, `/parts/PT-001/cross-catalog`,
`/parts/PT-002/customs` all returned 200 with correctly synthetic-flagged
payloads (full excerpts captured during this session).

Seed script run twice; all six new-label counts and the 3 demo-Order count
were identical before/after the second run (idempotency confirmed, also
covered by `test_seed_is_idempotent`).

## 23. Known Limitations

- **Frontend is entirely undone.** No `GraphInsights.tsx` tab/extension, no
  "SYNTHETIC DEMO DATA" UI indicator, no frontend build/test/typecheck run.
  This is the largest gap against the spec.
- **KPI demo breadth is minimal, not exhaustive.** 3 demo orders, 3
  CatalogEntry comparisons, 1 customs flag — enough to prove each traversal
  pattern works end-to-end, not a large synthetic dataset.
- **Pre-existing data-quality issues, not caused by or fixed in this
  session** (left alone per the brief): 8 `CONC6-DBG*` Part nodes are
  Phase-6 concurrency-test pollution already in the live graph; 23 Part
  nodes (`PT-021`..`PT-043`) have `part_number: null` in the live graph
  (a pre-existing gap, discovered while validating duplicates, not
  introduced here); PT-054–PT-060's SRC-042 provenance mismatch (flagged in
  the prior research doc) was not touched and none of those 7 rows were
  used in any new demo data.
- `docs/data/neo4j/scripts/import_dealers.py` (now checked in) imported the
  182 dealers via the Python driver, since Aura does not support
  `LOAD CSV FROM 'file:///...'` the way `dealers.cypher` is written — same
  situation as the existing `aura_import.py` for the rest of the dataset.
- No `(:Price)` node, no real cross-catalog evidence, no real customs
  evidence — all confirmed absent, consistent with prior research; nothing
  new attempted to find them beyond the one Depot-statistics fact in
  Section 3.

## 24. Next Recommended Phase

In priority order:
1. **Frontend**: extend `GraphInsights.tsx` with the "SYNTHETIC DEMO DATA"
   indicator convention and wire the five new endpoints — likely as
   extensions of the existing Source & Availability / Alternatives /
   Supply-Source-Risk tabs rather than net-new tabs, per the spec's own
   preference; then run `npm run check` (typecheck + test + build) for a
   real before/after count against the confirmed 82/82 baseline (Section 19).
2. Commit the dealer-import step into `docs/data/neo4j/scripts/` as a
   proper, checked-in idempotent script (mirroring
   `seed_operational_demo_data.py`'s structure) so it isn't just a
   scratchpad one-off.
3. Broaden the synthetic KPI dataset (more demo orders/catalog entries)
   only if a specific new demo scenario is requested — the current set is
   intentionally minimal-but-real, not a placeholder to pad silently.
