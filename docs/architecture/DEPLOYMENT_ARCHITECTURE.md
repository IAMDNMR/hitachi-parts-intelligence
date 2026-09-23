# Deployment Architecture

## 1. Deployment units

| Unit | Today | Phase 2 architecture |
|---|---|---|
| Frontend | React/Vite static build, deployed to Vercel (confirmed existing pattern) | Unchanged; new fulfilment routes ship as part of the same build (`FRONTEND_ARCHITECTURE.md`). |
| Backend API | Serverless functions under `frontend/api/*.js` (confirmed existing pattern) | Extended with new versioned handlers under `/api/v1/...`, invoking the modular-monolith business modules (`BACKEND_ARCHITECTURE.md`, `HIGH_LEVEL_ARCHITECTURE.md` §3). Same deployment unit, not a new one. |
| PostgreSQL | Not present today | New — a managed PostgreSQL instance. Specific host/vendor is a **TO-BE** choice (a managed provider compatible with the existing Vercel deployment is the natural starting point, but this document does not lock one without a concrete evaluation, per the brief's "do not lock a cloud vendor unless justified"). |
| Neo4j | Neo4j Aura (confirmed, `frontend/api/_lib/neo4j.js`) | Unchanged. |
| Integration Adapters | N/A today | Run inside the backend deployment unit (no separate service) — see `BACKEND_ARCHITECTURE.md`. |

## 2. Networking

- Frontend → Backend: same-origin HTTPS (the existing Vercel routing already proxies `/api/*` to the deployed functions; `/api/v1/*` follows the same rule).
- Backend → PostgreSQL / Neo4j: private connection strings, not publicly routable beyond the backend's own network context; credentials per `ENVIRONMENT_CONFIGURATION.md`.
- Backend → Integration Adapters → external providers: outbound HTTPS only, from the backend, never from the frontend (principle 6).
- No component other than the backend has network access to PostgreSQL, Neo4j, or any external provider.

## 3. Environment variables

Per `ENVIRONMENT_CONFIGURATION.md` — database connection strings, Neo4j credentials, and (once confirmed) Integration Adapter credentials are all environment variables scoped per deployment environment, set in the deployment platform's own configuration (matching the existing `NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD`/`NEO4J_DATABASE` pattern already in place for Vercel).

## 4. Database migrations

Not written in this phase (explicitly excluded — "do not create database migrations"). Architecturally: migrations will be versioned, forward-only scripts applied before a new backend deployment goes live, with the deployment pipeline gated on successful migration (a failed migration blocks the deploy rather than shipping code against a mismatched schema) — a standard pattern, not a novel one, deferred to Phase 3 for the actual tooling choice.

## 5. Rollback

- Frontend/Backend: redeploying the previous build (standard for the existing Vercel-based deployment model — no new capability needed).
- PostgreSQL schema: forward-only migrations (§4) mean rollback of a *schema* change requires a compensating migration, not a destructive revert — this avoids the risk of losing transactional data written under the new schema. Exact tooling is Phase 3.
- This is a principle, not a script, at this phase.

## 6. Health checks

Per `OBSERVABILITY_ARCHITECTURE.md` §4 — liveness (process responding) and readiness (PostgreSQL reachable) are the deployment platform's gate for routing traffic to a new deployment; Neo4j/adapter health is monitored but does not gate deployment or readiness, consistent with the "must keep functioning without Neo4j" rule.

## 7. Backup requirements

- PostgreSQL: regular automated backups are a requirement of "production-ready from the beginning" (principle 1) — this is the platform's sole source of truth for Allocation, Order, Shipment, Service Job state, so its backup/restore capability is not optional. Exact frequency/retention is an operational (TO-BE) decision, not fixed here.
- Neo4j: already an existing operational concern for the current Aura deployment, unchanged by this phase — this document does not introduce a new requirement here, only notes that its loss would only affect relationship/context data, never transactional state (`NEO4J_ARCHITECTURE.md`).

## 8. Scaling approach

- The modular monolith deployed as serverless functions (§1) scales the same way the existing platform already does — each function invocation scales independently under the deployment platform's own model, with no new capacity-planning burden introduced by this phase.
- PostgreSQL scaling (connection pooling, read replicas, etc.) is not needed at Phase 2's confirmed scope/scale and is not designed speculatively here (principle 2) — it becomes a Phase 3+ concern once real traffic patterns exist.
- If a genuine need for a long-lived backend process (rather than serverless functions) emerges later, `HIGH_LEVEL_ARCHITECTURE.md` §3 already notes the modular-monolith code organization does not preclude that evolution.

## 9. Cloud vendor stance

The frontend and current serverless backend already run on Vercel, and Neo4j already runs on Aura — both **confirmed, existing facts**, not new choices made by this document. This architecture does not introduce a *new* vendor lock beyond what already exists, and explicitly leaves PostgreSQL's hosting provider open (§1) rather than assuming a specific one, since no Phase 1/HCME requirement justifies committing to one yet.
