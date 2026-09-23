# ADR-002 — PostgreSQL Responsibility

> **SUPERSEDED (2026-09-22):** the platform was subsequently restructured to
> exactly two app roots (`frontend/`, `backend/`) with **Neo4j as the sole
> runtime database** — see `backend/app/db/neo4j/connection.py` and
> `backend/app/config.py` (no `DATABASE_URL`/SQLAlchemy config remains).
> This document is kept for historical context only; do not use it to
> justify introducing PostgreSQL. See ADR-011 for the current data
> architecture as it pertains to Parts Intelligence.


## Context

Architectural principle 9 mandates PostgreSQL as the transactional source for operational state. The platform has no database today for Allocation, Order, Shipment, or Service Job data — Neo4j exists but is used for relationship/context data (fitment), not transactional state.

## Decision

PostgreSQL is the sole source of truth for every entity with a lifecycle/state machine: Inventory (cache/provenance only, not the real quantity), Inventory Reservation, Fulfilment Request, Fulfilment Option, Allocation, Order, Order Line, Shipment, Shipment Event, Service Job, Service Part, Users/Access (local mapping), and Audit Records — detailed in `POSTGRESQL_DATA_ARCHITECTURE.md`.

## Reason

- A relational, ACID-transactional database is the correct fit for entities whose defining requirement is safe, consistent state transitions under concurrency — most critically Allocation (`ALLOCATION_ARCHITECTURE.md`), where the no-double-allocation guarantee (BR-02) depends on transactional isolation.
- Keeping all transactional ownership in one database (rather than split across PostgreSQL and Neo4j) satisfies principle 11 (no duplicate ownership of the same fact) directly — there is never a question of which store is authoritative for, say, an Order's status.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Store transactional state in Neo4j alongside relationship data | Violates principle 11 and principle 10 (Neo4j is for relationship/context value, not transactional facts); graph databases are not the natural fit for strict state-machine/concurrency guarantees. |
| A NoSQL document store for flexibility | No demonstrated need for schema flexibility beyond what a well-modelled relational schema provides; would add a third data technology without justification, working against "as simple as possible" (principle 2). |
| No dedicated transactional store; rely on the external systems (once confirmed) as sources of truth | Rejected — those systems are UNKNOWN today, and even once confirmed, the platform still needs its own durable record of Allocation/Order/Shipment/Service state to support the safe-concurrency and audit requirements that are the platform's own responsibility, not delegable to an external system. |

## Consequences

- New infrastructure (a managed PostgreSQL instance) must be provisioned before Phase 3 implementation — hosting provider is deliberately left TO-BE (`DEPLOYMENT_ARCHITECTURE.md` §1, §9).
- Every module's PostgreSQL access is scoped to the tables it owns (`BACKEND_ARCHITECTURE.md` §1), enforced by convention now and by database-level least-privilege access in Phase 3.
- The existing `PartsInquiry` write into Neo4j (`frontend/api/quote-request.js`) is *not* migrated by this decision — flagged as a Phase 3 reconciliation item (`ARCHITECTURE_UNKNOWN_ITEMS.md`), not resolved here.

## Status

**SUPERSEDED**

> [!NOTE]
> **Architecture Decision Reconciliation (Phase 5 Consolidation)**:
> This decision has been superseded by the deliberate architecture decision: **CURRENT DATABASE = NEO4J ONLY**.
> The target architecture is `React + TypeScript + Vite → Python + FastAPI → Neo4j AuraDB`.
> Neo4j is currently the single database and source of truth for both relationship context and lifecycle entities (FulfilmentRequest, FulfilmentOption, Allocation, InventoryCache, AuditRecord, IdempotencyRecord, PartsInquiry).
> PostgreSQL dependencies (SQLAlchemy, psycopg) have been removed. See `docs/NEO4J_ONLY_MIGRATION.md`.
