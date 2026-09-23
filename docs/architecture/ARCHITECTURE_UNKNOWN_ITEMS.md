# Architecture Unknown Items

Every UNKNOWN/TO-BE item introduced or carried forward across the Phase 2 architecture documents, in one place — the architecture-level companion to Phase 1's `HCME_CONFIRMED_VS_UNKNOWN.md`. Nothing here has been silently resolved into a decision elsewhere in `docs/architecture/`.

## Carried forward from Phase 1 (unchanged, still open)

All UNKNOWN rows in Phase 1 `HCME_CONFIRMED_VS_UNKNOWN.md` remain open: dealer structure, European depot structure, inventory source, ERP, WMS, pricing source, allocation/VOR policy, order system, shipment system, carrier, tracking, service system, authentication, customer identity, dealer identity detail, telematics integration specifics.

## New architecture-level TO-BE items introduced in Phase 2

| Item | Where discussed | Status |
|---|---|---|
| PostgreSQL hosting provider | `DEPLOYMENT_ARCHITECTURE.md` §1, §9 | TO-BE — not locked, no Phase 1/HCME requirement justifies a specific vendor yet. |
| Authentication/identity provider (e.g., whether Microsoft Entra ID is used) | `SECURITY_ARCHITECTURE.md` §1 | TO-BE — named only as a candidate, not selected. |
| Inventory freshness threshold (when data becomes "stale" → `UNKNOWN`) | `AVAILABILITY_ARCHITECTURE.md` §1 | TO-BE — operational/business tuning decision. |
| Allocation reservation expiry window length | `ALLOCATION_ARCHITECTURE.md` §6 | TO-BE — same Phase 1 open question (`HCME_BUSINESS_QUESTIONS.md` Q17), needs a concrete value before Phase 3. |
| Order-creation retry window before releasing an unconsumed allocation | `ORDER_ARCHITECTURE.md` §Idempotency-adjacent, `RESILIENCE_ARCHITECTURE.md` | TO-BE. |
| Whether split/partial fulfilment is offered by default | `FULFILMENT_ARCHITECTURE.md` §4 | TO-BE — Phase 1 business decision, not an architecture one. |
| Whether partial allocation is auto-accepted or requires explicit confirmation | `ALLOCATION_ARCHITECTURE.md` §8 | TO-BE. |
| Who is authorized to make Fulfilment Selection (customer, dealer, or both contextually) | `API_ARCHITECTURE.md` §3 | TO-BE (Phase 1 `HCME_BUSINESS_QUESTIONS.md` Q8). |
| Order numbering scheme | `ORDER_ARCHITECTURE.md` §3 | Phase 3 implementation detail, not fixed here. |
| Database migration tooling | `DEPLOYMENT_ARCHITECTURE.md` §4 | Phase 3 decision. |
| Secrets-management approach for Staging/Production | `ENVIRONMENT_CONFIGURATION.md` §4 | Phase 3/deployment-platform decision. |
| Observability tooling (logging platform, APM, error tracking vendor) | `OBSERVABILITY_ARCHITECTURE.md` §8 | Explicitly TO-BE, tool-agnostic requirements fixed instead. |
| Backup frequency/retention for PostgreSQL | `DEPLOYMENT_ARCHITECTURE.md` §7 | Operational (TO-BE) decision. |
| Audit record retention period | `AUDIT_ARCHITECTURE.md` §4 | TO-BE (Phase 1 `HCME_BUSINESS_QUESTIONS.md` Q26). |
| Rate limit thresholds | `SECURITY_ARCHITECTURE.md` §8 | Phase 3 tuning decision. |
| Reconciliation of the existing `PartsInquiry` Neo4j write (`frontend/api/quote-request.js`) against the new PostgreSQL-as-transactional-store principle | `NEO4J_ARCHITECTURE.md` §4 | Flagged, not resolved — explicit Phase 3 decision, no code touched in Phase 2. |
| Exact backend language/framework implementation details beyond "modular monolith, deployed as versioned serverless handlers consistent with the existing codebase" (see `ADR-001`) | `HIGH_LEVEL_ARCHITECTURE.md`, `ADR-001` | RESOLVED in Phase 3 implementation: Python 3.12 + FastAPI (`backend/app/`), not the Node.js/TypeScript direction `ADR-001` set — `ADR-001` was superseded rather than followed. No new ADR was recorded for this change; flagging it here per this document's own rule. |
| Data residency/privacy constraints for European data | `SECURITY_ARCHITECTURE.md` §10 | UNKNOWN (Phase 1 `HCME_BUSINESS_QUESTIONS.md` Q27). |

## Rule

Any of the above being resolved updates this document (and, where it also answers a Phase 1 question, `HCME_BUSINESS_QUESTIONS.md`) — it does not get silently assumed into a downstream architecture document without a recorded decision here or in an ADR.
