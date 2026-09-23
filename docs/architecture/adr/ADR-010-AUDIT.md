# ADR-010 — Audit Strategy

## Context

Phase 1 requires full traceability (who, what, when, previous state, new state, source, correlation ID) for every important business action. The platform's transactional correctness (especially Allocation) depends on precise state transitions, and multiple external/unknown integrations mean disputes about "what actually happened" are likely (e.g., "why did this allocation fail," "what price was resolved and by what source").

## Decision

Audit records are written by a dedicated Audit module, **in the same PostgreSQL transaction as the state change they describe** (`AUDIT_ARCHITECTURE.md`, `POSTGRESQL_DATA_ARCHITECTURE.md` §Audit Record), append-only, never auto-deleted (retention policy TO-BE). Every state-changing action across Fulfilment Request, Allocation, Order, Shipment, and Service Job is covered, per the table in `AUDIT_ARCHITECTURE.md` §1.

## Reason

- Writing audit in the *same* transaction as the change guarantees audit and state can never drift apart — a weaker approach (e.g., a separate asynchronous audit write) would risk exactly the kind of "what really happened" ambiguity that makes audit valuable in the first place.
- Given no external system is confirmed as authoritative for pricing, inventory, carriers, etc., the platform's own audit trail is, for now, the *only* record of what data was used to make a given decision (e.g., which pricing source resolved which price) — this makes the provenance fields (source, provider identity) non-optional, not a nice-to-have.
- Ties directly into the correlation-ID-based observability design (`OBSERVABILITY_ARCHITECTURE.md` §2), so a single ID reconstructs both the operational trace and the business audit trail for one request.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Asynchronous/best-effort audit logging (write-behind, eventually consistent) | Rejected — risks audit and state disagreeing, exactly the failure mode audit exists to prevent; the brief's "production-ready from the beginning" principle favours correctness over the marginal write-latency saving. |
| A separate audit database/service | Unjustified additional infrastructure at this stage (principle 2); PostgreSQL, already the transactional store, is a sufficient and simpler home, and keeps the same-transaction guarantee easy to implement. |
| Rely on Integration Adapter logs alone for provenance, skip a dedicated audit table | Insufficient — adapter-level logs capture *calls*, not *business decisions* (e.g., an allocation release triggered by cancellation vs. by expiry looks the same at the adapter level but means something different business-wise); a dedicated, business-concept-level audit record is needed. |

## Consequences

- Every module that changes state must call into Audit as part of its own transaction (`BACKEND_ARCHITECTURE.md` §2) — this is a hard implementation requirement for Phase 3, not optional instrumentation added later.
- Retention policy remains an open question (`HCME_BUSINESS_QUESTIONS.md` Q26) — the architecture is safe by default (never deletes) until a policy is confirmed, rather than guessing a retention period that might be wrong.

## Status

Accepted.

> [!NOTE]
> **Implementation Reconciliation (Phase 5 Consolidation)**:
> In the consolidated Neo4j-only backend (`docs/NEO4J_ONLY_MIGRATION.md`), audit events are stored as `(:AuditRecord)` nodes created in Neo4j within the transaction of each state change, satisfying the same append-only provenance and immutability requirements without PostgreSQL.
