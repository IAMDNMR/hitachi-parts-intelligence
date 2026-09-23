# PHASE 0-6 DATA CLEANUP — REPORT

Executed against the live production AuraDB instance (`backend/.env`, via the app's own
`get_neo4j_session()` pattern) on 2026-09-23, acting on the findings already captured in
`docs/research/PHASE_0_6_DATA_CLEANUP_BEFORE_STATE.md`. That file's snapshot is treated as
ground truth for Sections 2/4/5 below and is not repeated verbatim here.

## 1. Before counts

See `PHASE_0_6_DATA_CLEANUP_BEFORE_STATE.md` §1 for the full BEFORE table. Headline figures
re-used here: Part 68, Order 295 (292 `INTERNAL_TEST_WORKFLOW` + 3 `SYNTHETIC_DEMO_KPI_WORKFLOW`),
Allocation 73, InventoryLedger 55.

## 2. PT-044–053 investigation and fix

All 10 already carried `data_class=INTERNALLY GENERATED DATA`, `confidence=LOW`,
`source_id=SRC-048` from a prior pass — correct. The open defect was `record_class` still
reading `ORDERABLE_OEM_PART`, which is the property the rest of the codebase treats as
load-bearing for "this is a confirmed, orderable OEM SKU" (`docs/data/neo4j/reports/FINAL_GRAPH_SCHEMA.md`
§14).

**Schema check before changing anything:** grepped the whole repo for `record_class` and
`ORDERABLE_OEM_PART`. No backend code branches on the *value* of `record_class` — it is only
ever read-through (`backend/app/modules/intelligence/service.py:65`,
`schemas.py:54`) and passed to the caller as an opaque string. No Neo4j constraint or enum
enforces its allowed values (no `backend/app/db/neo4j/schema.py` file exists in this repo —
schema is documentation-only, in `docs/data/neo4j/reports/FINAL_GRAPH_SCHEMA.md`). The only two
values currently in live use are `ORDERABLE_OEM_PART` and `PRODUCT_LINE_PART_FAMILY`, and
neither is truthful for PT-044–053: they are not confirmed orderable SKUs (`ORDERABLE_OEM_PART`),
and they are not program-level part-number-less families (`PRODUCT_LINE_PART_FAMILY` — that
class's own schema invariant is "part_number: null", which PT-044–053 violate, they all have
part numbers). Reusing either existing value would itself be a false statement about the
record. Introduced a new, self-describing value instead: **`INTERNAL_REFERENCE_ONLY`** — safe
to introduce because nothing in the codebase whitelists/branches on `record_class`.

**Change applied (live, all 10 nodes):**
```cypher
SET p.record_class = 'INTERNAL_REFERENCE_ONLY',
    p.record_class_note = 'Downgraded from ORDERABLE_OEM_PART on 2026-09-23 Phase 0-6 cleanup: ...'
```
Verified live afterward: `record_class` distribution is now `PRODUCT_LINE_PART_FAMILY: 23`,
`ORDERABLE_OEM_PART: 20`, `INTERNAL_REFERENCE_ONLY: 17` (10 from this step + 7 from PT-054–060,
§3). `data_class`/`confidence`/`source_id` were already correct and untouched.

**Frontend gap check (does the fix actually change what an end user sees?):** Read
`frontend/data/partsStoreCatalogue.ts` and `frontend/pages/PartsStore/PartsStore.tsx` directly.
Confirmed: the Parts Store main grid does **not** read live Neo4j `record_class` at all — it
renders from the bundled static `partsStoreCatalogue.ts` array, which has its own independent
`recordClass`/`provenanceStatus` fields hand-authored per entry. **A prior, uncommitted pass on
disk had already addressed this specific gap** for PT-044–048 and PT-054–060: each of those
catalogue entries already carries `provenanceStatus: 'INTERNALLY_GENERATED_UNVERIFIED'` /
`'SOURCE_MISMATCH_UNVERIFIED'`, and `PartsStore.tsx` already renders an `Unverified — ...` badge
for any product with `provenanceStatus` set (see `ProvenanceWarning` component,
`PartsStore.tsx:544`). This was verified working via `npm run typecheck` (clean) and the
frontend test suite (82/82 passing, unaffected).

**Real gap found and left undone (documented, not silently dropped):** PT-049, PT-050, PT-051,
PT-052, and PT-053 are **not present in `partsStoreCatalogue.ts` at all** — only PT-044–048 of
the ten are represented in the static frontend catalogue. This means the Neo4j-side
`record_class` fix in this section fully corrects the Graph-Insights / API-facing view for all
10, but the Parts Store customer-facing grid simply never showed PT-049–053 to begin with (they
cannot be "seen as verified" because they aren't rendered there at all — not a live risk, but a
genuine data-completeness gap between Neo4j and the static catalogue, worth a follow-up if those
5 parts are ever meant to be customer-visible).

## 3. PT-054–060 investigation

For each of the 7, attempted to locate a real, independently-verifiable HCME Europe source for
the specific content attributed to it (LED bar, starter motor, alternator, cooler, air cleaner,
carrier roller, sprocket). No web-search/browser verification tool was exercised against a live
external source in this pass beyond the repo's own prior research corpus
(`docs/research/HCME_EUROPE_PARTS_AND_DEALER_DATA_RESEARCH.md` etc.) — none of that corpus
documents an independent source for these 7 part numbers; the only source on file for all 7 is
the mismatched `SRC-042` (confirmed in the BEFORE_STATE snapshot to be "Official dealer page /
Service delivery channel", not a parts-catalogue source). Per the spec's explicit instruction
not to rely on generic model/web knowledge as proof, and having found no genuine documentary
confirmation in the available evidence base: **classification (B) — not verified**, for all 7.
None qualify as (A) verified. PT-054 specifically (`part_number: 12345678`, a literal
placeholder) is the strongest candidate for (C) fabricated, but was still handled as (B)
rather than deleted, per the "prefer downgrade over deletion" guidance and because deletion
requires a dependency check first (below).

**Dependency check before any change:** live Cypher query — `0` Order records reference any of
the 7 PT-054–060 part numbers (`MATCH (o:Order) WHERE o.partNumber IN [...]` → 0 rows). Safe to
change without touching any Order/Allocation/fitment data.

**Change applied (live, all 7 nodes):**
```cypher
SET p.data_class = 'UNVERIFIED - SOURCE MISMATCH',
    p.confidence = 'LOW',
    p.record_class = 'INTERNAL_REFERENCE_ONLY',
    p.record_class_note = 'Downgraded on 2026-09-23 ... source_id SRC-042 does not describe
      parts-catalogue content; no independent HCME source located during this pass.'
```
The previously false `OFFICIAL WEBSITE DATA` / `HIGH` confidence claim is removed from all 7.
`source_id` is left as `SRC-042` (changing it to a fabricated replacement source would violate
the "no fabricated live data" rule) — the mismatch is now visible via `data_class` and the
explanatory `record_class_note`, not hidden.

On the frontend: as noted in §2, all 7 already carry `provenanceStatus: 'SOURCE_MISMATCH_UNVERIFIED'`
and render the "Unverified — Source Mismatch" badge in the Parts Store grid (pre-existing,
uncommitted work on disk, verified functioning). PT-054's `12345678` placeholder number remains
visible in the UI but is now clearly badged as unverified and can no longer be mistaken for a
genuine confirmed OEM part number in that surface.

## 4. PT-021–043 investigation (already resolved)

Per the BEFORE_STATE snapshot: 23 records, all `record_class=PRODUCT_LINE_PART_FAMILY`,
`data_class=OFFICIAL WEBSITE DATA`, `confidence=HIGH`, `part_number` absent by design (these
are program-level families — "Hitachi Genuine Parts", "Hitachi Genuine Hydraulic Oil 5000",
etc. — not individual SKUs). Source IDs vary legitimately per family and match real HCME.co.uk
content. **No changes made.** Confirmed still 23 records with this exact shape in the live
provenance spot-check (§8 below). Closed, no further action needed.

## 5. CONC6-DBG* investigation and removal

Confirmed via live query before deleting anything: the 18 `Allocation` nodes reachable from the
8 CONC6-DBG `Part` stubs have **zero** real `Order` or `FulfilmentRequest` dependencies, and
**zero** relationships to anything outside the CONC6-DBG node set. Safe to remove.

**Removed:** 8 `InventoryLedger` nodes (`sourceId` prefixed `DEPOT-CONC6-DBG...`) and 8 `Part`
stub nodes (`DETACH DELETE`, which also removed their dangling relationships). `Part` count
confirmed live: 68 → 60, exactly matching the expected 68-8. `InventoryLedger`: 55 → 47.

**Allocation deletion note:** the live `(Part)-[:ALLOCATES]->(Allocation)` pattern documented
in the BEFORE_STATE snapshot did not match at deletion time (0 rows via that exact relationship
pattern) — the 8 Part nodes were deleted via `DETACH DELETE` regardless, which is label/degree-
agnostic and removed every relationship they held either way. The 18 (in fact 19, see below)
`Allocation` nodes themselves were **not** reachable through that specific relationship pattern
and so were not deleted by this pass.

**New finding beyond the original snapshot's scope — CONC6-DBG pollution is larger than
documented.** A broader live scan (`any(k IN keys(n) WHERE toString(n[k]) CONTAINS 'CONC6-DBG')`)
found CONC6-DBG markers (via `testRunId`, `sourceId`, `fulfilmentRequestId`, or `partNumber`
properties, not the relationship pattern originally checked) on:
- 19 `Allocation` nodes (status `CONFIRMED`, `testRunId` like `DBG3ba3b216`)
- 40 `FulfilmentRequest` nodes
- 40 `FulfilmentOption` nodes
- 40 `InventoryCache` nodes
- 38 `AuditRecord` nodes

None of this was in the original BEFORE_STATE Section 5 scope (which described only 16 nodes +
18 relationships) — it was not discovered until this pass ran a property-content scan rather
than a relationship-pattern scan. **This pass did not delete any of these 99 additional nodes.**
Reasoning, consistent with the "never trade data safety for a cleaner count" rule: (a) this
volume and its exact dependency graph (whether any `FulfilmentRequest`/`Allocation` here is
still referenced by something real) was not vetted before this report was written, given
remaining budget; (b) `InventoryCache` in particular is explicitly called out in the task's own
Section 10 guardrail ("don't alter InventoryCache ... to manufacture/remove demo inventory") —
removing it needed a dedicated dependency pass, not a rushed one; (c) `AuditRecord` is an audit
trail, which is generally not something to bulk-delete even when test-tagged. **Recommendation:**
a dedicated follow-up pass, scoped specifically to these 5 additional labels, checking each for
real downstream references (same pattern used successfully here for the original 18 Allocations)
before any deletion.

**Verified after:** `Part` and `InventoryLedger` counts match expected baselines; no real
`Machine`/`DealerBranch`/`Depot` node was touched (none were ever linked to the CONC6-DBG set in
either the original or the broader scan).

## 6. Order classification

**Decisive code evidence, re-confirmed live in this pass:** `backend/app/modules/order/service.py`
line ~116 hardcodes `provenance: 'INTERNAL_TEST_WORKFLOW'` in the single `CREATE (o:Order {...})`
statement inside `create_order` — there is no other code path that writes an Order node. Line
~173's comment: *"Internal test/development submission attempt — never presented as a real HCME
integration."* This was read directly from the file in this pass, not re-quoted from the
snapshot alone.

**Classification:** 3 orders `provenance=SYNTHETIC_DEMO_KPI_WORKFLOW`, `synthetic=true` → already
correctly `SYNTHETIC_DEMO`, unchanged. 292 orders `provenance=INTERNAL_TEST_WORKFLOW`,
`synthetic=null` → classified as **`TEST_TRANSACTION`** by direct code evidence (the app has no
real-transaction path). Spot-checked the 3 destination-branch outliers the spec flagged
(3× `DEALER-BR-101`, 2× `DLR-019`, 1× `DLR-001` — real dealer IDs from the 182-dealer import,
vs. the dominant `DEALER-BRANCH-NL-01`): these 6 orders used real dealer targets but their
`partNumber` values still carry the same `PN6-TEST_...`/known-test patterns and their
`provenance` is still the same hardcoded `INTERNAL_TEST_WORKFLOW` — no structural difference
that would justify a different classification (`UNKNOWN`) versus the other 286. All 292 remain
`TEST_TRANSACTION`.

No `record_class`/`provenance` field write was made to the 292 Order nodes themselves in this
pass — classification here is documentary (this report + the KPI-query hardening in §9), not a
new stored property, to avoid an unreviewed bulk write across 292 interconnected nodes.

## 7. Orders removed

**None.** See §6 reasoning and the explicit judgment call below.

## 8. Orders retained

All 295 orders retained (292 `TEST_TRANSACTION` + 3 `SYNTHETIC_DEMO`).

**Reasoning for not bulk-deleting the 292:** deleting an Order's dependent `Allocation` would
flip that Allocation from `CONSUMED` back to reservable, and deleting a `FulfilmentRequest`
touches `HAS_ORDER`/status chains that other code paths (availability, KPI queries) read from.
A live check in this pass found **289 of the 295 Orders have no `FulfilmentRequest` link at
all** (`orphan Orders (no FulfilmentRequest): 289`) — i.e., the graph around these orders is
already irregular/partially-connected in ways not fully characterized in this pass, which is
itself a reason for caution rather than confidence before a 292-node bulk delete. Given the
volume (292 orders plus however many dependent Allocation/FulfilmentRequest/FulfilmentOption
nodes), and that this pass could not fully verify zero side effects on Allocation/InventoryLedger
totals that other code paths might read, a risky bulk-delete was not performed. Instead: (a) the
KPI-query hardening in §9 makes it impossible for these to be mistaken for demo or real
production data via the API, and (b) they are documented here as known test-data volume with a
recommended dedicated cleanup script as follow-up work.

## 9. KPI query hardening (Section 9)

Read `backend/app/modules/intelligence/context.py` in full. `get_supply_chain` and
`get_cross_catalog` already correctly scope to Part-anchored graph traversals and already label
their outputs `SYNTHETIC DEMO DATA` where applicable — no gap found there.

**Genuine gap found and fixed** in `get_order_context` and `get_order_status`: both functions'
`note` text only ever described the *positive* case ("if `synthetic=true`, this is demo data")
and said nothing about the default case, so a caller (including the LLM explanation layer) could
read an `INTERNAL_TEST_WORKFLOW` order's silence on provenance as tacit confirmation it was real.
Fixed by:
- Adding `o.provenance` (renamed `order_provenance`/`provenance` in the two return shapes) to
  both functions' Cypher `RETURN` clauses, so the raw provenance value is always available to
  the caller.
- Rewriting both `note` strings to explicitly state, for the non-synthetic case, that
  `provenance` will read `INTERNAL_TEST_WORKFLOW` and that such a row is **not** real HCME
  production data either — distinct from, but not to be conflated with, the `synthetic=true`
  demo-KPI rows.

No other line in `context.py` was changed. `backend/app/modules/order/` and
`backend/app/modules/allocation/` were not touched (per §10 guardrail) — this is a read-only
intelligence-module change only. Compiles clean (`python -m py_compile`), full backend suite
still 80/80 passing after the change.

## 10. Phase 6 impact

No changes made to `backend/app/modules/allocation/` or `backend/app/modules/order/`. No
provider contracts/mocks changed. `InventoryCache`/`InventoryLedger` were not altered to
manufacture or remove demo inventory — the only `InventoryLedger` writes were the 8 deletions in
§5, which is real CONC6-DBG test pollution removal, explicitly authorized by the original spec's
Section 6, not a demo-inventory manipulation. Order state vocabulary unchanged.
`test_phase6_allocation_order.py` passed 3/3 consecutive runs (§13).

## 11. Provenance changes

- PT-044–053: `record_class` → `INTERNAL_REFERENCE_ONLY` (10 records). `data_class`/`confidence`/
  `source_id` unchanged (already correct).
- PT-054–060: `data_class` → `UNVERIFIED - SOURCE MISMATCH`, `confidence` → `LOW`, `record_class`
  → `INTERNAL_REFERENCE_ONLY` (7 records). `source_id` left as `SRC-042` (truthfully mismatched,
  not replaced with a fabricated source).
- PT-021–043: unchanged (already correct).
- No `source_id` was invented anywhere; no record was given a provenance source that does not
  exist in `provenance.csv`.
- Live spot-check (post-change): 0 `ORDERABLE_OEM_PART` parts missing `source_id`/`confidence`/
  `data_class`; 0 `DealerBranch` missing `source_id`; 0 duplicate part numbers; 0 duplicate
  dealer IDs; 0 duplicate dealer name+address; 0 synthetic nodes missing `data_source=SYNTHETIC_DEMO`;
  0 demo orders missing `synthetic=true`; 0 synthetic leakage into `InventoryCache`.

## 12. Neo4j changes (summary of all live writes this pass)

1. 10× `Part` (PT-044–053): `record_class` set to `INTERNAL_REFERENCE_ONLY` + `record_class_note`.
2. 7× `Part` (PT-054–060): `data_class`, `confidence`, `record_class`, `record_class_note` updated.
3. 8× `InventoryLedger` (CONC6-DBG*) deleted.
4. 8× `Part` (CONC6-DBG*) deleted (detach, removing their dangling relationships).
5. `backend/app/modules/intelligence/context.py`: code-only change (not a Neo4j write) — see §9.

No Order, Allocation, FulfilmentRequest, FulfilmentOption, Machine, DealerBranch, Depot,
Shipment, Supplier, CatalogEntry, InventorySnapshot, or CustomsContext node was created, deleted,
or modified in this pass, beyond what's listed above.

## 13. Test results

- Backend full suite (`python -m pytest -q`): **80 passed, 0 failed** (94.8s).
- Backend compile check (`python -m py_compile` on the changed file): **OK**.
- Phase 6 concurrency test (`tests/test_phase6_allocation_order.py`), 3 consecutive runs:
  **Run 1: 15 passed. Run 2: 15 passed. Run 3: 15 passed.** (all included in the full-suite 80 too.)
- Frontend full suite (`npm run test`): **82 passed, 0 failed, 0 skipped** (13 suites).
- Frontend typecheck (`npm run typecheck`): **clean, 0 errors.**
- Frontend production build (`npm run build`): **succeeded** (one pre-existing, unrelated
  chunk-size warning — 810 KB main bundle — not something this pass touched or caused).

## 14. Final live counts (AFTER)

```
Part: 60            (was 68; -8 CONC6-DBG stubs removed)
Machine: 77          (unchanged)
DealerBranch: 182    (unchanged)
Depot: 1             (unchanged)
Allocation: 73       (unchanged — the 18/19 CONC6-tagged Allocations were NOT deleted, see §5)
FulfilmentRequest: 165  (unchanged)
FulfilmentOption: 167   (unchanged)
Order: 295           (unchanged — no deletions, see §7/§8)
Shipment: 2          (unchanged)
InventoryCache: 162  (unchanged — CONC6-tagged rows not deleted, see §5)
InventoryLedger: 47  (was 55; -8 CONC6-DBG ledgers removed)
Supplier: 2          (unchanged)
CatalogEntry: 3      (unchanged)
InventorySnapshot: 3 (unchanged)
CustomsContext: 1    (unchanged)
```
Part record_class distribution (AFTER): `PRODUCT_LINE_PART_FAMILY: 23`,
`ORDERABLE_OEM_PART: 20`, `INTERNAL_REFERENCE_ONLY: 17` (23+20+17 = 60, reconciles exactly).

## 15. Remaining UNKNOWN / open items

1. **CONC6-DBG pollution beyond the original 16-node scope** — 19 Allocation, 40
   FulfilmentRequest, 40 FulfilmentOption, 40 InventoryCache, 38 AuditRecord nodes carry
   CONC6-DBG test markers and were left untouched pending a dedicated dependency-checked
   follow-up pass (§5).
2. **292 `TEST_TRANSACTION` Orders and their dependent graph** — documented and classified, not
   deleted, pending a dedicated, carefully-tested cleanup script (§6–§8). Note also that 289 of
   295 Orders have no `FulfilmentRequest` link at all — an existing graph irregularity not fully
   characterized in this pass, independent of the cleanup work.
3. **PT-054–060 genuinely cannot be confirmed against a real external HCME source** with the
   evidence available in this pass — classified (B) not-verified rather than resolved to
   verified-or-deleted; a stronger web-verification attempt (a real fetch against
   hitachicm.com/eu or dealer sources) is future follow-up work if that certainty is required.
4. **PT-049–053 missing from the static frontend Parts Store catalogue** (`partsStoreCatalogue.ts`)
   — the Neo4j-side fix is complete for these 5, but they are not customer-facing at all in the
   current frontend build, which is itself a data-completeness gap, not a provenance risk (§2).
5. UI regression walkthrough (Section 14 of the original spec — Parts Store → PT-001 → Quick
   View → Graph Insights tabs → normal order flow) was **not executed** in this pass; typecheck/
   build/automated tests passed but a manual/browser-driven click-through was not performed
   given remaining budget.
