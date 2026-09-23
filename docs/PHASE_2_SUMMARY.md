# Phase 2 Summary — HCME Technical Architecture

**Phase:** 2 — Technical Architecture (complete)
**Input:** Phase 1 business process (frozen, all 15 documents read) + Phase 0 research + the existing repository (`frontend/`, `neo4j/`).
**Output:** `docs/architecture/` (25 documents) + `docs/architecture/adr/` (10 ADRs) + this summary.
**Next phase:** Phase 3 (implementation) — not started; awaiting approval.

No application code, database migration, API route, or external connection was created in this phase. The existing Parts Store and its current APIs were not touched.

## 1. Files created

**`docs/architecture/`** (25): `SYSTEM_BOUNDARY.md`, `HIGH_LEVEL_ARCHITECTURE.md`, `FRONTEND_ARCHITECTURE.md`, `BACKEND_ARCHITECTURE.md`, `POSTGRESQL_DATA_ARCHITECTURE.md`, `NEO4J_ARCHITECTURE.md`, `DATA_OWNERSHIP.md`, `CANONICAL_DATA_MODEL.md`, `API_ARCHITECTURE.md`, `STATE_TRANSITION_ARCHITECTURE.md`, `AVAILABILITY_ARCHITECTURE.md`, `FULFILMENT_ARCHITECTURE.md`, `ALLOCATION_ARCHITECTURE.md`, `ORDER_ARCHITECTURE.md`, `SHIPMENT_ARCHITECTURE.md`, `DEALER_ARCHITECTURE.md`, `SERVICE_ARCHITECTURE.md`, `INTEGRATION_ARCHITECTURE.md`, `RESILIENCE_ARCHITECTURE.md`, `SECURITY_ARCHITECTURE.md`, `AUDIT_ARCHITECTURE.md`, `OBSERVABILITY_ARCHITECTURE.md`, `ENVIRONMENT_CONFIGURATION.md`, `DEPLOYMENT_ARCHITECTURE.md`, `TESTING_ARCHITECTURE.md`, `ARCHITECTURE_UNKNOWN_ITEMS.md`.

**`docs/architecture/adr/`** (10): `ADR-001-SYSTEM-ARCHITECTURE.md` … `ADR-010-AUDIT.md`.

**`docs/PHASE_2_SUMMARY.md`** — this document.

## 2. Architecture decisions made

| Decision | Summary | ADR |
|---|---|---|
| Modular monolith, not microservices | Ten+ business domains as modules in one codebase, deployed as versioned serverless handlers extending the existing Vercel pattern | ADR-001, ADR-004 |
| Node.js/TypeScript backend | Matches existing frontend language and tooling; no new language introduced | ADR-001 |
| PostgreSQL is the transactional source of truth | Owns every entity with a lifecycle/state machine (Allocation, Order, Shipment, Service Job, Fulfilment Request, Audit) | ADR-002 |
| Neo4j scoped to relationship/context data only | Fitment (existing, confirmed) plus candidate dealer/territory relationships; never a transactional fact owner | ADR-003 |
| Integration Adapters as the only path to external systems | Nine named interfaces, all UNKNOWN/mock-only today; no system invented | ADR-005 |
| API versioning from the start | New endpoints under `/api/v1/...`; existing unversioned endpoints untouched | ADR-006 |
| Local, transaction-based allocation concurrency | Row-locked ledger in PostgreSQL enforces no-double-allocation without depending on any external system | ADR-007 |
| Uniform resilience pattern across all adapters | Bounded timeout/retry, honest `UNKNOWN` results, simple circuit breaker, no new infrastructure | ADR-008 |
| Authentication enforcement shape fixed; provider left open | Central identity check + role model designed now; Microsoft Entra ID named only as a candidate | ADR-009 |
| Audit written in the same transaction as the state change | Guarantees audit and state can never disagree | ADR-010 |

## 3. Data ownership decisions

See `DATA_OWNERSHIP.md` in full. Summary: PostgreSQL is fully authoritative for Allocation, Order, Order Line, Service Job, Service Part, and Audit Records; it is a cache/provenance record (not authoritative) for Inventory and Shipment/Shipment Event, whose real truth sits with an external inventory source and carrier respectively (both UNKNOWN today); Parts/Fitment/Machine remain owned by the existing Parts Store and Neo4j; Dealer, Customer, Price, Technician, and Territory are UNKNOWN/TO-BE, with the platform holding only the required field shape pending a confirmed source.

## 4. Major API boundaries

Versioned under `/api/v1/...` (`API_ARCHITECTURE.md`): Fulfilment Request creation/retrieval, Availability, Fulfilment Options + Selection, Allocation (creation-critical, idempotent, concurrency-safe), Order creation/retrieval, Shipment retrieval + Tracking, Dealer retrieval, Service Job creation/update/completion. Every endpoint specifies method, request/response shape, authorization requirement, validation, error responses, idempotency, and the state transition it drives — no endpoint exposes a raw database table shape.

## 5. Major integration boundaries

Nine adapter interfaces (`INTEGRATION_ARCHITECTURE.md`): `InventoryProvider`, `PricingProvider`, `OrderProvider`, `RoutingProvider`, `ShippingRateProvider`, `ShipmentProvider`, `TrackingProvider`, `ServiceProvider`, `DealerProvider`. All nine are currently UNKNOWN/mock-only — no real implementation is confirmed or connected. Neo4j (already integrated) and the Telematics API (confirmed to exist, explicitly excluded from this phase) are the only two external-facing dependencies with any confirmed status.

## 6. Confirmed vs unknown items

Full ledger: `ARCHITECTURE_UNKNOWN_ITEMS.md` (architecture-level) plus the unchanged Phase 1 `HCME_CONFIRMED_VS_UNKNOWN.md` (business-level, still authoritative). Confirmed and reused in this phase: React/Vite frontend, Vercel serverless deployment pattern, Neo4j Aura integration and its credential-handling pattern, the existing Parts Store catalogue. Newly flagged UNKNOWN/TO-BE at the architecture level: PostgreSQL hosting provider, authentication provider, every Integration Adapter's real implementation, inventory freshness threshold, allocation expiry window, order-retry window, split/partial-fulfilment default policy, audit retention period, observability tooling, and the reconciliation of the existing `PartsInquiry` Neo4j write against the new PostgreSQL-ownership principle.

## 7. Risks requiring HCME confirmation

In priority order (blocking real functionality, not just polish):

1. **No confirmed inventory source at any tier** — until one is confirmed, Availability will honestly return `UNKNOWN` for every source in production (`AVAILABILITY_ARCHITECTURE.md` §3). This is the single biggest functional risk.
2. **No confirmed pricing source** — Order creation cannot succeed in production without one (`ORDER_ARCHITECTURE.md` §5).
3. **No confirmed authentication provider** — blocks real dealer/customer login; only the enforcement shape exists today (ADR-009).
4. **No confirmed carrier/shipment/tracking system** — Shipment stays manually-updated only until one exists (`SHIPMENT_ARCHITECTURE.md`).
5. **No confirmed dealer/branch master data** — Dealer, a first-class entity by design, has no real data source yet (`DEALER_ARCHITECTURE.md`).
6. **The existing `PartsInquiry` Neo4j write** is arguably transactional data that principle 9 says belongs in PostgreSQL — needs an explicit HCME/engineering decision before Phase 3 touches that code path.

None of these block Phase 3 from *starting* (schema, module scaffolding, mock-backed end-to-end flow) — they block real, non-mock functionality in production.

## 8. Phase 3 prerequisites

- Provision a PostgreSQL instance (hosting provider TO-BE, `DEPLOYMENT_ARCHITECTURE.md` §1).
- Translate `CANONICAL_DATA_MODEL.md` / `POSTGRESQL_DATA_ARCHITECTURE.md` into an actual schema and migrations.
- Scaffold the backend modules per `BACKEND_ARCHITECTURE.md`, with mock adapter implementations satisfying the contracts in `INTEGRATION_ARCHITECTURE.md`.
- Implement the `/api/v1/...` endpoints per `API_ARCHITECTURE.md`, enforcing the state machines in `STATE_TRANSITION_ARCHITECTURE.md`.
- Implement and load-test the allocation concurrency mechanism (ADR-007) with the concurrency test from `TESTING_ARCHITECTURE.md` §1 as a hard gate.
- Resolve or explicitly defer, with a decision recorded, each item in §7 above.
- Choose an authentication provider (or confirm Entra ID) before any real dealer/customer account can be used.

## 9. Validation results

| # | Question | Result |
|---|---|---|
| 1 | Does the architecture support all 10 business stages? | Yes — every stage in Phase 1 `HCME_PARTS_FULFILMENT_PROCESS.md` maps to a named module, API endpoint, and data entity (`BACKEND_ARCHITECTURE.md`, `API_ARCHITECTURE.md`, `CANONICAL_DATA_MODEL.md`). |
| 2 | Does every Phase 1 state have a technical owner? | Yes — `STATE_TRANSITION_ARCHITECTURE.md` maps all four Phase 1 state machines (Fulfilment Request, Allocation, Shipment, Service Job) plus Order status to specific modules and enforced transitions. |
| 3 | Is every transactional entity assigned to one source of truth? | Yes — `DATA_OWNERSHIP.md` and `POSTGRESQL_DATA_ARCHITECTURE.md` assign exactly one owner per entity; no entity is dual-owned. |
| 4 | Is Neo4j used only where it provides relationship value? | Yes — `NEO4J_ARCHITECTURE.md` scopes it to fitment (confirmed) and candidate relationship data only; no transactional fact is duplicated there (ADR-003). |
| 5 | Can the system function without Neo4j when graph data is not required? | Yes — every Neo4j read is documented as an optional enrichment with a defined degrade-gracefully behaviour (`NEO4J_ARCHITECTURE.md` §5, `RESILIENCE_ARCHITECTURE.md`), matching the existing `part-enrichment.js` precedent. |
| 6 | Can external providers be replaced? | Yes — every external dependency is behind an adapter interface (`INTEGRATION_ARCHITECTURE.md`); swapping an implementation is a configuration change, not a business-logic change. |
| 7 | Can inventory failures be handled safely? | Yes — `AVAILABILITY_ARCHITECTURE.md` and BR-01 (carried from Phase 1) ensure missing data is never treated as zero stock, at every layer including the frontend. |
| 8 | Can two concurrent users attempt allocation safely? | Yes — `ALLOCATION_ARCHITECTURE.md` and ADR-007 define a transaction-scoped, row-locked mechanism specifically for this, with a mandatory concurrency test. |
| 9 | Are orders idempotent? | Yes — `ORDER_ARCHITECTURE.md` §4 and `API_ARCHITECTURE.md`'s idempotency-key requirement; a retried order-creation call against an already-consumed allocation returns the existing order. |
| 10 | Are shipment updates traceable? | Yes — Shipment Events are append-only with source (carrier vs. manual) recorded, and every status change is audited (`SHIPMENT_ARCHITECTURE.md`, `AUDIT_ARCHITECTURE.md`). |
| 11 | Is the dealer a first-class entity? | Yes — `DEALER_ARCHITECTURE.md` models Dealer/Dealer Branch/Territory/Capability as real entities referenced by ID everywhere, never a text field (BR-10). |
| 12 | Is telemetry excluded from the core dependency chain? | Yes — no module, API endpoint, or state transition depends on ConSite or the Telematics API anywhere in this architecture (`SYSTEM_BOUNDARY.md`, BR-08/BR-09 carried from Phase 1). |
| 13 | Are unknown HCME systems clearly marked? | Yes — every UNKNOWN item is recorded in `DATA_OWNERSHIP.md`, `INTEGRATION_ARCHITECTURE.md`, and consolidated in `ARCHITECTURE_UNKNOWN_ITEMS.md`; none was silently resolved into an assumption in another document. |
| 14 | Are credentials kept server-side? | Yes — `SECURITY_ARCHITECTURE.md` §4, §11–13 and `ENVIRONMENT_CONFIGURATION.md` §3, consistent with the existing codebase's own pattern (`frontend/api/_lib/neo4j.js`). |
| 15 | Is the architecture production-ready without unnecessary complexity? | Yes — every "why not X" alternative considered across the ten ADRs was rejected specifically for adding complexity without a demonstrated need (microservices, message queues, distributed locks, new database technologies), consistent with principle 2. |
| 16 | Can Phase 3 implement the foundation without redesigning the architecture? | Yes, with the caveat in §7/§8: Phase 3 can scaffold the full system (schema, modules, API, mock-backed end-to-end flow) immediately; it cannot reach *real* production behaviour for Availability, Pricing, Authentication, Shipment tracking, or Dealer data until HCME confirms the corresponding UNKNOWN item — which is the correct, honest state for this architecture to be in, not a gap in the architecture itself. |

---

**Phase 2 is complete. Waiting for approval before starting Phase 3.**
