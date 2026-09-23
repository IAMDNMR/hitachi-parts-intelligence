# Observability Architecture

Minimum production observability — deliberately not over-built (no monitoring product is selected here that isn't already justified by a concrete need).

## 1. Structured application logs

Every backend module logs in a structured (not free-text) format, including the correlation/request ID (§2), so logs from one request can be filtered and read together regardless of which module produced them. Continues the existing pattern already present in the codebase (`part-enrichment.js` logs the error server-side and never echoes internal detail to the client).

## 2. Request/correlation IDs

Every inbound API request is assigned a correlation ID (generated if not supplied by the caller); it is threaded through every downstream call — business module, adapter call, database write, audit record (`AUDIT_ARCHITECTURE.md` §2) — so a single ID reconstructs the full path of one request end to end.

## 3. Error tracking

Unhandled errors and business-level failures (Phase 1 `FAILURE_AND_EXCEPTION_CASES.md`) are captured centrally, tagged with the correlation ID and the failing module/adapter. The specific tool (e.g., a hosted error-tracking service) is a **TO-BE selection** — this document fixes the requirement (centralized, correlated capture), not the vendor.

## 4. Health checks

- A basic liveness check (is the backend process responding at all) and a readiness check (can it reach PostgreSQL) are exposed for the deployment platform to use (`DEPLOYMENT_ARCHITECTURE.md` §Health checks).
- Neo4j and every Integration Adapter are checked separately, but their unavailability does **not** fail the platform's overall readiness check — per `NEO4J_ARCHITECTURE.md`'s critical rule and `RESILIENCE_ARCHITECTURE.md`, the platform is designed to keep serving the parts of the process that do not depend on them.

## 5. External integration monitoring

Each Integration Adapter (`INTEGRATION_ARCHITECTURE.md`) reports, at minimum: call count, failure count, timeout count, and current circuit-breaker state (where one exists — `RESILIENCE_ARCHITECTURE.md`) so a degraded provider is visible operationally before it becomes a widespread customer-facing problem, even though no single failure blocks the whole platform.

## 6. Database monitoring

- PostgreSQL: connection health, transaction failure rate, and (specifically for `ALLOCATION_ARCHITECTURE.md`) lock-wait time on the reservation ledger — a rising figure here is an early signal of contention worth watching as real volume grows.
- Neo4j: query latency and failure rate, tracked separately from PostgreSQL since its failure mode is "degrade gracefully," not "platform down" (`NEO4J_ARCHITECTURE.md` §5).

## 7. Critical workflow monitoring

The following are flagged as the workflows to monitor first, because they are where a silent failure would be most damaging:

- Allocation success/failure rate (a spike in failures may indicate a real stock/demand mismatch, or a concurrency bug).
- Order creation failure rate (Phase 1 failure case 13).
- Shipment tracking staleness (shipments with no event update beyond an expected interval).
- Service Job jobs stuck in a non-terminal state beyond an expected duration.

## 8. Tooling — explicitly TO-BE

No specific logging platform, APM, or monitoring SaaS is selected in this phase. The requirements above (structured logs, correlation IDs, health checks, adapter-level metrics) are tool-agnostic; the actual product choice is deferred to Phase 3 implementation, once deployment environment (`DEPLOYMENT_ARCHITECTURE.md`) is finalised.
