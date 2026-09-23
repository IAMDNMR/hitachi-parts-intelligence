# ADR-008 — External Provider Failure Strategy

## Context

Principle 12 requires failure handling for every important external dependency. Every Integration Adapter (`INTEGRATION_ARCHITECTURE.md`) has no confirmed real implementation today, and even once real providers are confirmed, they will fail, time out, or return malformed data in production.

## Decision

A uniform resilience pattern applies to every adapter call (`RESILIENCE_ARCHITECTURE.md`): bounded timeout, bounded retry for idempotent reads only, an explicit "could not determine" result (never a fabricated value — BR-01's principle generalized to every adapter, not just Inventory), a simple counter-based circuit breaker for sustained failures, and provenance-tagged audit logging for every outcome. No message broker, distributed retry queue, or dedicated resilience-infrastructure product is introduced at this phase.

## Reason

- Missing/failed external data must degrade to an honest "unknown," never a wrong-but-plausible-looking default — this is the same principle Phase 1 established for inventory (BR-01), generalized here to every integration point for consistency.
- A simple in-process retry + breaker pattern is sufficient for the confirmed dependency count and call volume (effectively zero real integrations today); introducing heavier infrastructure now would be speculative over-engineering the brief explicitly warns against.
- Keeping the pattern uniform across all nine adapter interfaces (`INTEGRATION_ARCHITECTURE.md` §1) means one well-tested resilience implementation, not nine bespoke ones.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| A message queue for all external calls, with asynchronous retry | Unjustified at current scale/dependency count; introduces operational complexity (a new infrastructure component, eventual-consistency handling in the frontend) with no demonstrated need. Not ruled out later for a specific slow integration (e.g., a carrier booking API), per `RESILIENCE_ARCHITECTURE.md` §What is deliberately not introduced. |
| No retry at all — fail immediately on any error | Would make the platform unnecessarily brittle against transient network blips that a single bounded retry resolves cheaply. |
| A full-featured resilience library/service mesh | Unjustified — the pattern needed (timeout, bounded retry, simple breaker) is well within what a small, direct implementation provides; no evidence of the request volume or dependency count that would justify heavier tooling. |

## Consequences

- Every Integration Adapter implementation (mock or real) must conform to this pattern (`INTEGRATION_ARCHITECTURE.md` §3) — enforced via the contract tests defined in `TESTING_ARCHITECTURE.md`.
- Neo4j reads follow the same degrade-gracefully posture (`NEO4J_ARCHITECTURE.md` §5), even though Neo4j is an internal store, not an external provider, because the same "never block the core flow on a non-critical dependency" logic applies.

## Status

Accepted.
