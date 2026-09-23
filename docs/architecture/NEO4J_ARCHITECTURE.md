# Neo4j Architecture

**Role:** relationship/context information only (principle 10), never a second owner of transactional facts (principle 11). Neo4j (Aura) is already integrated and in production use in this repository — confirmed via `frontend/api/_lib/neo4j.js` and the existing `docs/data/neo4j/data/*.csv` domain (Machines, Parts, Categories, Fitment, Services, Maintenance, Digital Services, Relationships, Provenance).

## Critical rule (restated from the brief)

> The Parts Store and the transactional fulfilment workflow must continue to function if Neo4j is unavailable, wherever graph data is not strictly required for that particular decision.

This is not a new principle for this codebase — it is already practiced: `frontend/api/part-enrichment.js` explicitly documents that the Parts Store catalogue must keep working if the Neo4j-backed enrichment call fails, and returns a safe `502` rather than breaking the page. Phase 2 extends this same pattern to the fulfilment workflow.

## 1. Entities and relationships already confirmed in use today

| Entity/Relationship | Status |
|---|---|
| `(:Part)`, `(:Machine)`, `(:Category)` | CONFIRMED — already populated (`docs/data/neo4j/data/parts.csv`, `machines.csv`, `categories.csv`). |
| `(:Machine)-[:HAS_PART_FITMENT]->(:Part)` | CONFIRMED — already queried live (`frontend/api/_lib/enrichment.js`). |
| `(:Service)`, `(:Machine)-[…]->(:Service)`, maintenance/service-part relationships | CONFIRMED to exist in the data foundation (`docs/data/neo4j/data/services.csv`, `machine_service.csv`, `service_part_requirements.csv`); not yet queried by any live API route. |
| `(:PartsInquiry)-[:REQUESTS]->(:RequestedPart)-[:FOR_PART]->(:Part)` | CONFIRMED — written today by `frontend/api/quote-request.js`. **Flagged below as an item to reconcile**, not redesigned in this phase. |

## 2. Candidate entities/relationships evaluated for the fulfilment process

For each candidate: why graph representation is useful, what question it answers, whether authoritative or derived, sync method, and Neo4j-unavailable behaviour.

| Candidate | Why graph? | Question it answers | Authoritative or derived? | Sync | If Neo4j unavailable |
|---|---|---|---|---|---|
| `Machine → Part` (fitment, existing) | Fitment is inherently a many-to-many relationship question ("which parts fit this machine", "which machines take this part") that a graph traversal answers naturally and that is already proven working. | "Is this part compatible with this machine/context?" (Select Part, Phase 1 Stage 1) | Derived from the existing data foundation (itself derived from the frozen source workbook) — not authoritative over the real engineering fact, but the best available confirmed reference. | Existing ETL pipeline (`docs/data/neo4j/scripts`), unchanged by this phase. | Select Part proceeds with fitment marked "unconfirmed" rather than blocking — matches Phase 1 failure case 3 ("fitment is uncertain"), which already defines this as a non-blocking warning, not a hard dependency. |
| `Part → Warehouse/Depot` | Useful for reasoning about *which sources could plausibly hold this part* as a network/topology question, distinct from *whether they currently do* (a live-inventory question, which stays in PostgreSQL/the external inventory source). | "Which sources are structurally connected to this part's supply network?" | Derived/reference data, not authoritative over live stock. | TO-BE — no such relationship exists in the graph today; would need to be populated once depot/source data is confirmed (currently UNKNOWN per Phase 1). | Availability stage still runs — it only loses this topology hint and queries all approved sources directly instead of using it to narrow the list. Not a hard dependency (see `AVAILABILITY_ARCHITECTURE.md`). |
| `Dealer → Warehouse`, `Dealer → Customer`, `Dealer → Service` | Dealer relationships (territory coverage, which dealers serve which customers/regions, dealer-to-dealer-branch structure) are graph-natural and match how Phase 1 treats the Dealer as a first-class, relationship-rich entity (`ACTORS_AND_RESPONSIBILITIES.md` §3). | "Which dealer(s) should handle this destination/customer?", "What is this dealer's service network?" | Would be authoritative for the *relationship* itself (once populated), while the Dealer's core transactional facts (capabilities used in an actual Order/Service Job) still live in PostgreSQL per `POSTGRESQL_DATA_ARCHITECTURE.md`. | TO-BE — no dealer/territory data exists in the graph today; entirely UNKNOWN per Phase 1 `HCME_CONFIRMED_VS_UNKNOWN.md`. | Dealer selection/lookup falls back to whatever PostgreSQL-held dealer reference data exists; not required for the transactional flow to proceed. |
| `Machine → Dealer` | Answers "which dealer(s) are associated with this machine" (e.g., original selling/servicing dealer) — a genuinely relational question. | "Who has a relationship with this machine already?" | Derived/reference. | TO-BE. | Not required; the process can proceed with an explicitly selected destination/dealer instead of an inferred one. |
| `Machine → Service` (existing, service history/eligibility) | Already present in the data foundation; useful for understanding what service types apply to a machine. | "What service types is this machine eligible for?" | Derived, from the existing data foundation. | Existing ETL, unchanged. | Service Job creation does not depend on this — Phase 1's Service Job model (`SERVICE_ARCHITECTURE.md`) does not require graph-sourced eligibility to open a job. |
| Reman Facility as a distinct node type | Phase 0 research confirms a Remanufactured parts tier exists; representing it as a graph entity would let it participate in the same `Part → Source` relationship pattern as other depots. | "Is a reman source structurally available for this part?" | Derived/reference, once populated. | TO-BE — not present today. | Same as `Part → Warehouse/Depot` above: an optional narrowing hint, never a blocker. |
| Territory as a distinct node type | Would let dealer coverage be queried as "which dealer serves this postcode/region" rather than a flat field. | "Which dealer/branch covers this destination?" | Would be authoritative for the relationship once populated (source data UNKNOWN today). | TO-BE. | Falls back to an explicit destination-to-dealer assignment held in PostgreSQL; not a hard dependency. |

## 3. What is explicitly NOT duplicated into Neo4j

Per principle 11 (no duplicate ownership of the same transactional fact), the following never get a graph-owned copy, even though they relate to graph entities above:

- Live inventory quantities (PostgreSQL cache of an external source — see `POSTGRESQL_DATA_ARCHITECTURE.md`).
- Allocation, Order, Shipment, Service Job state — these live only in PostgreSQL. Neo4j may *reference* them by ID for relationship queries (e.g., "show me this machine's service history including this new job") but never stores their state as the source of truth.
- Pricing.

## 4. The one existing item flagged for reconciliation (not resolved in this phase)

`frontend/api/quote-request.js` currently writes a `PartsInquiry` node directly into Neo4j — this is arguably transactional, customer-submitted business data, which principle 9 says belongs in PostgreSQL once it exists. **This phase does not change that code** (Phase 2 does not modify the existing Parts Store or its APIs). It is recorded here and in `ARCHITECTURE_UNKNOWN_ITEMS.md` as a decision to make explicitly in Phase 3: whether `PartsInquiry` should migrate to PostgreSQL once the new transactional store exists, or remain a graph-only, non-fulfilment artifact outside this process's scope.

## 5. Failure handling requirement

Every backend module that reads from Neo4j (see `BACKEND_ARCHITECTURE.md`) must:

1. Treat a Neo4j failure/timeout as a degraded, non-fatal condition wherever the queried data is a *hint* rather than a requirement (fitment confidence, source topology, dealer relationship hints).
2. Never let a Neo4j failure block a stage whose Phase 1 definition does not require graph data to function (this covers every stage — Neo4j is not in the critical path of Select Part → Close by design).
3. Log/audit the degradation (see `AUDIT_ARCHITECTURE.md`, `OBSERVABILITY_ARCHITECTURE.md`) so a prolonged outage is visible operationally even though it is not user-blocking.

See `RESILIENCE_ARCHITECTURE.md` §Neo4j failure for the technical handling pattern.
