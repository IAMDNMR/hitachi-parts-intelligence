# ADR-003 — Neo4j Responsibility

> **PARTIALLY SUPERSEDED (2026-09-22):** the platform is now Neo4j-only at
> runtime (no PostgreSQL) — see the note on ADR-002. Neo4j now also owns
> the transactional entities described there (`FulfilmentRequest`,
> `InventoryCache`, `Allocation`, `AuditRecord`, etc. — see
> `backend/app/db/neo4j/schema.py`), which contradicts this ADR's original
> "relationship data only" boundary. That boundary is superseded; this
> document is kept for the historical fitment-modelling rationale, which
> still holds. See ADR-011 for Parts Intelligence's use of this same graph.
>
> **FURTHER UPDATE (2026-09-22):** the Node/Vercel-style serverless layer
> referenced below (`frontend/api/*.js`, `frontend/api/_lib/neo4j.js`,
> `frontend/api/_lib/enrichment.js`) has been retired. Its two routes
> (part enrichment, quote request) are now `backend/app/api/v1/part_enrichment.py`
> and `backend/app/api/v1/quote_request.py`, using the same shared Neo4j
> driver (`backend/app/db/neo4j/connection.py`) as every other FastAPI
> module. There is now a single backend surface (`/api/v1/*` on FastAPI)
> and a single Neo4j connection for the whole platform — the "two separate
> Neo4j drivers" state this ADR was written against no longer exists.


## Context

Neo4j (Aura) is already integrated and in production use for machine↔part fitment queries, confirmed via `frontend/api/_lib/neo4j.js` and `frontend/api/_lib/enrichment.js`. Architectural principle 10 says to use Neo4j where it provides genuine relationship value; principle 11 forbids duplicating transactional ownership across PostgreSQL and Neo4j; and the brief requires the core workflow to keep functioning if Neo4j is unavailable.

## Decision

Neo4j's scope for this platform is **relationship/context data only**: today, `Machine→Part` fitment (existing, confirmed); as candidates once source data exists, `Dealer→Warehouse`, `Dealer→Customer`, `Dealer→Service`, `Machine→Dealer`, `Part→Warehouse/Depot`, and `Territory` relationships (`NEO4J_ARCHITECTURE.md` §2). Neo4j never holds a transactional fact (inventory quantity, allocation/order/shipment/service state) that PostgreSQL also owns. Every read from Neo4j is treated as an optional enrichment, not a hard dependency, for every stage of the fulfilment process.

## Reason

- Fitment/relationship questions ("which parts fit this machine," "which dealers cover this territory") are graph-natural and already proven to work well in this codebase.
- Principle 11 requires a single owner per transactional fact; PostgreSQL is that owner for everything with a lifecycle (ADR-002), so Neo4j's role is cleanly bounded to what it does uniquely well.
- The existing codebase already treats Neo4j as non-load-bearing for the catalogue (`part-enrichment.js`'s own stated design intent) — this decision formalizes and extends that same posture to the new fulfilment workflow, rather than introducing a new, stricter dependency on Neo4j.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Use Neo4j as the sole database (both relationship and transactional data) | Violates principle 11 (no single fact should need to be reconciled between two data models) and makes the "must function without Neo4j" requirement impossible to satisfy for the transactional flow. |
| Duplicate transactional entities into Neo4j for richer relationship queries on them | Rejected — this is exactly what principle 11 forbids; any relationship query needing transactional data can instead join across a reference ID from PostgreSQL, without owning a second copy. |
| Drop Neo4j entirely and move fitment data into PostgreSQL | Rejected — Neo4j is an existing, working, confirmed asset for exactly this kind of relationship query; replacing it would be unjustified rework with no demonstrated benefit, contradicting "do not rebuild what already works." |

## Consequences

- Every backend module reading from Neo4j must implement the graceful-degradation behaviour in `RESILIENCE_ARCHITECTURE.md` (treat failure/timeout as "hint unavailable," never block the stage).
- New relationship data (dealer, territory) cannot be populated into Neo4j until its source is confirmed (UNKNOWN today) — until then, those candidate relationships remain undesigned-in-detail, tracked in `ARCHITECTURE_UNKNOWN_ITEMS.md`.
- The existing `PartsInquiry` write (a transactional-shaped fact currently in Neo4j) is flagged, not resolved, as an inconsistency with this ADR to address in Phase 3.

## Status

**REVISED / SUPERSEDED IN PART**

> [!NOTE]
> **Architecture Decision Reconciliation (Phase 5 Consolidation)**:
> In Phase 5, the architectural decision was made to consolidate to **Neo4j as the sole database and single source of truth** (`CURRENT DATABASE = NEO4J ONLY`).
> Neo4j's role was expanded from relationship-context-only to encompass all operational and state machine entities (FulfilmentRequest, FulfilmentOption, Allocation, InventoryCache, AuditRecord, IdempotencyRecord, PartsInquiry) using Cypher graph models and ACID transaction semantics. PostgreSQL was removed completely. See `docs/NEO4J_ONLY_MIGRATION.md`.
