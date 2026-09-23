# ADR-001 — System Architecture

## Status

**Partially superseded.** The modular-monolith-behind-`/api/v1/...` shape below was followed. The language choice was not: the Phase 3/4 backend was implemented in **Python 3.12 + FastAPI** (`backend/app/`), not Node.js/TypeScript. No replacement ADR was recorded for that change; this note and `ARCHITECTURE_UNKNOWN_ITEMS.md` are the only record of it. The rest of this document is left as originally written — the historical decision and its reasoning at the time.

## Context

Phase 1 froze a 10-stage business process (Select Part → Close) that must be built as a production-ready system. The existing repository already runs a React/Vite frontend deployed to Vercel, with backend logic as serverless functions under `frontend/api/*.js`, and Neo4j (Aura) already integrated for relationship data. The brief requires simplicity, no premature microservices, no direct browser-to-external-system calls, and backend-owned business/integration logic.

## Decision

Adopt a **modular monolith backend, deployed as versioned serverless API handlers**, extending the repository's existing pattern:

```
React/Vite Frontend → Backend API (/api/v1/...) → Business/Application Services (modular monolith) → PostgreSQL + Neo4j → Integration Adapters → External systems
```

The backend is implemented in **Node.js/TypeScript**, matching the existing frontend/tooling language (the repository already has TypeScript tooling — `tsconfig.json`, `npm run typecheck` — and a Node-based dev API server). No new language is introduced.

## Reason

- Matches the existing, proven deployment (no new infrastructure to stand up for the sake of this phase).
- Keeps the team on one language across frontend and backend, reducing operational and cognitive overhead (principle 2: as simple as possible while production-grade).
- A modular monolith satisfies "modular, evolvable" (principle 5) without the operational cost of microservices, which principle 4 says to avoid absent a demonstrated need — none exists yet (single team, low confirmed integration count, no demonstrated independent-scaling requirement).
- Serverless functions already scale per-invocation on the existing platform, so no separate scaling design is needed at this stage.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Microservices per business domain | No demonstrated need (principle 4); would multiply deployment/operational complexity for ten domains that today have no independent scaling or team-ownership requirement. |
| A different backend language (e.g., Python, Go) | Would split the codebase across two languages for no demonstrated benefit; the existing repository is already Node/TypeScript end to end. |
| A long-lived server process instead of serverless functions | Would require standing up new infrastructure not already present; the existing serverless pattern already satisfies "backend owns business logic" and scales adequately for the confirmed scope. Not precluded for later (see `HIGH_LEVEL_ARCHITECTURE.md` §3). |

## Consequences

- New backend code must be organized into the module boundaries defined in `BACKEND_ARCHITECTURE.md` from the start, even though it deploys as serverless functions — this is what preserves the option to extract a module into its own service later without a rewrite.
- Cross-module in-memory state must be avoided (each serverless invocation is stateless), which is already consistent with keeping PostgreSQL as the transactional source of truth.

## Status

Accepted.
