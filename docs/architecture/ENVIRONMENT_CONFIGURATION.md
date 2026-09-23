# Environments & Configuration

## 1. Environments

| Environment | Purpose | Notes |
|---|---|---|
| Development | Local development. `frontend/server/dev-api.mjs` proxies the pre-existing unversioned `/api/*` routes (`part-enrichment`, `quote-request`) locally, as planned. | As actually implemented, `/api/v1/...` did **not** follow the same local-dev proxy pattern: it is served directly by the Python FastAPI backend (`backend/app/main.py`, run standalone via `uvicorn`), not proxied through `dev-api.mjs`. Wiring the Vite dev proxy to route `/api/v1/*` to FastAPI is tracked as outstanding work, not yet done. Mock/test Integration Adapters (`INTEGRATION_ARCHITECTURE.md` §2) are registered in the Python backend. |
| Testing (CI) | Automated test execution (`TESTING_ARCHITECTURE.md`). | Isolated PostgreSQL/Neo4j instances or equivalents; no real external provider credentials ever present. |
| Staging | Pre-production verification against production-like configuration. | Mirrors production's adapter registration (real providers where confirmed/approved) but against non-production data and credentials. |
| Production | Live platform. | No mock adapters registered for any UNKNOWN-classified interface (`INTEGRATION_ARCHITECTURE.md` §2) — an unconfirmed integration simply returns `UNKNOWN`/fails honestly rather than serving mock data. |

## 2. Configuration differences

| Concern | How it varies by environment |
|---|---|
| Database connection (PostgreSQL, Neo4j) | Environment-specific credentials and connection strings, never shared across environments. |
| Integration Adapter registration | Mock/test implementations in Development/Testing only; real implementations (once confirmed) in Staging/Production. |
| Log verbosity | More verbose in Development; structured and production-appropriate elsewhere (`OBSERVABILITY_ARCHITECTURE.md`). |
| Rate limits | Relaxed/off in Development; enforced in Staging/Production (`SECURITY_ARCHITECTURE.md` §8). |
| Authentication | TO-BE overall (`SECURITY_ARCHITECTURE.md` §1); whatever provider is chosen will have environment-specific tenant/app registrations. |

## 3. Rules (mandatory, from architectural principles 7 and the brief)

- **No secrets in source code**, in any environment, ever.
- **External provider credentials are environment-specific** — a Staging credential is never valid in Production and vice versa, so a misconfiguration cannot cause cross-environment data leakage.
- **Credentials never reach the frontend**, in any environment — including Development, where it may be tempting to shortcut this; the existing codebase already avoids this (`frontend/api/_lib/neo4j.js` reads from server-side env vars, falling back to a git-ignored `.env` file locally, never bundled into frontend code) and this phase's new configuration follows the same rule.

## 4. Configuration source

Environment variables (matching the existing pattern — `dotenv` is already a dependency), loaded server-side only. The specific secrets-management approach for Staging/Production (a platform-native secret store vs. a dedicated secrets manager) is a Phase 3/deployment-platform decision (see `DEPLOYMENT_ARCHITECTURE.md`), not fixed here.
