# ADR-006 — API Versioning

## Context

The existing API surface (`frontend/api/part-enrichment.js`, `quote-request.js`) is unversioned. The new fulfilment workflow introduces a much larger, longer-lived API surface (`API_ARCHITECTURE.md`) that will evolve across Phase 3+ as real integrations and business rules are added.

## Decision

All new fulfilment-workflow endpoints are versioned from the start under `/api/v1/...`. The existing unversioned endpoints are left untouched (Phase 2 does not modify the existing Parts Store or its APIs).

## Reason

- The brief explicitly requires versioning "from the beginning."
- A ten-stage process with state machines, external integrations still to be confirmed, and business rules still to be finalized by HCME (`HCME_BUSINESS_QUESTIONS.md`) is very likely to need breaking contract changes over time (e.g., once a real `PricingProvider` is confirmed, the Order creation request/response may need new fields) — versioning gives a safe path for that without breaking whatever frontend/other consumers exist by then.
- Namespacing new endpoints separately from the existing unversioned ones also cleanly marks the boundary between "existing Parts Store, unmodified" and "new fulfilment platform," reinforcing the scope discipline in `PHASE_1_DECISIONS.md`.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| No versioning, evolve the same endpoints in place | Risks breaking any existing or in-progress consumer with no migration path; explicitly against the brief. |
| Version via a request header instead of the URL path | A path-based version (`/api/v1/...`) is simpler to reason about, log, route, and document than header-based versioning, and matches common practice for a platform at this stage of maturity — no evidence yet that header-based negotiation is needed. |
| Retroactively version the existing `part-enrichment`/`quote-request` endpoints too | Out of scope — Phase 2 does not modify the existing Parts Store APIs; if they need versioning later, that is a separate, explicit decision, not a side effect of this one. |

## Consequences

- Every new endpoint in `API_ARCHITECTURE.md` carries the `/api/v1/` prefix.
- A future `/api/v2/...` can be introduced alongside `v1` without breaking existing callers, once a genuine breaking change is needed.

## Status

Accepted.
