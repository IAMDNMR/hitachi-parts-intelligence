# ADR-007 — Allocation Concurrency Strategy

## Context

Phase 1 BR-02 requires: two simultaneous users must not be able to successfully allocate the same final unit of inventory. This is the single hardest correctness requirement in the whole system, and the external inventory source(s) that would ideally enforce this are UNKNOWN and not confirmed to offer any atomic reservation capability.

## Decision

The platform enforces the guarantee **locally**, using a single PostgreSQL transaction per allocation attempt against a platform-owned "committed quantity" ledger per (part, source), with row-level locking ensuring two concurrent attempts against the same ledger row are serialized (`ALLOCATION_ARCHITECTURE.md` §3–4). The externally-sourced Availability figure is only the *starting* quantity for that ledger, refreshed periodically — the platform never assumes the external system itself provides concurrency safety.

## Reason

- This is the only approach that does not depend on an UNKNOWN, unconfirmed external system's own concurrency guarantees (which cannot be relied upon, and would violate principle 13/14 to assume).
- A single-database transaction with row-level locking is a standard, well-understood pattern, sufficient for the confirmed scale, and does not require introducing new infrastructure (a distributed lock service, a message queue) that principle 2 says to avoid absent justification.
- Combining this with idempotency keys (`ALLOCATION_ARCHITECTURE.md` §5) closes the second risk (a retried request from the same caller), which the locking pattern alone does not address.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Rely on the external inventory source to handle concurrent reservation | Rejected — no external source is confirmed to exist, let alone to offer this guarantee; would be an unfounded assumption. |
| A distributed lock (e.g., a dedicated lock service) | Unjustified additional infrastructure for a guarantee a single-database transaction already provides at this scale. |
| Optimistic concurrency only (check-then-write without locking, retry on conflict) | Viable in principle, but a locked read-modify-write within one transaction is simpler to reason about correctly for this specific, high-stakes invariant, and avoids the complexity of retry-storm handling under contention; Phase 3 may still choose an optimistic implementation detail as long as it satisfies the same invariant. |
| Allow overselling and reconcile after the fact | Explicitly rejected by the brief's production requirement — this is not an eventual-consistency-tolerant fact. |

## Consequences

- Every allocation attempt is a single, bounded database transaction — this is now a hard architectural constraint that Phase 3 implementation must not work around (e.g., by splitting the check and the write across two separate calls/transactions).
- The exact SQL/locking mechanism (e.g., `SELECT ... FOR UPDATE` vs. a conditional `UPDATE`) is a Phase 3 implementation choice, but must satisfy the invariant stated in this ADR — any implementation that does not is a defect, not a valid alternative.
- A concurrency test (`TESTING_ARCHITECTURE.md` §1, "Allocation concurrency tests") is mandatory before this is considered done, per the testing strategy.

## Status

Accepted.

> [!NOTE]
> **Implementation Reconciliation (Phase 5 Consolidation)**:
> In the consolidated Neo4j-only backend (`docs/NEO4J_ONLY_MIGRATION.md`), the single-database allocation concurrency guarantee is enforced using Neo4j ACID transactions with atomic optimistic version checking on `(:InventoryLedger)` nodes (`WHERE l.version = $version`).
> The strict invariant (10 concurrent requests for 1 item → exactly 1 SUCCESS, 9 CONFLICTS) is verified by `tests/test_phase3_phase4.py::test_allocation_concurrency_lock`.
