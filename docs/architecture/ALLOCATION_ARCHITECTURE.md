# Allocation Architecture

> [!NOTE]
> **Implementation Reconciliation (Phase 5 Consolidation)**:
> In the consolidated architecture (`docs/NEO4J_ONLY_MIGRATION.md`), the single-database transaction is implemented in **Neo4j AuraDB**.
> The platform maintains a committed quantity figure on `(:InventoryLedger)` nodes, with atomic optimistic version checking (`WHERE l.version = $version`).

Implements Phase 1 `ALLOCATION_PROCESS.md` and BR-02. This is the single most concurrency-sensitive piece of the whole platform.

## 1. The requirement, precisely

```
Inventory available = 1
Request A → allocate 1
Request B → allocate 1  (simultaneous)

Exactly one of A, B may succeed. The other must receive a definitive failure.
```

## 2. Reservation vs. Allocation

- **Reservation** is the *attempt* to hold quantity — it is the moment the concurrency-safety guarantee is enforced.
- **Allocation** (the `CONFIRMED` state) is a reservation that has been confirmed within its expiry window. Phase 1 deliberately keeps these as two states of one entity (`PROCESS_STATES.md` §B) rather than one instantaneous step.

## 3. Transaction boundary

The stock check and the reservation write happen in **one database transaction**, against **Neo4j's own Inventory Reservation ledger** (`(:InventoryLedger)`) — not against the external inventory source directly. Concretely, the platform maintains a locally-owned "committed quantity" figure per (part, source) that:

1. Starts from the last known Availability figure for that source (itself sourced externally, cached with a timestamp — see `AVAILABILITY_ARCHITECTURE.md`).
2. Is decremented, within the platform's own transaction, by every `RESERVED`/`CONFIRMED` Allocation against that (part, source).
3. Is never decremented below zero — a reservation attempt that would do so fails outright rather than partially succeeding silently.

This is what makes the guarantee enforceable: the platform does not depend on an external, UNKNOWN system to provide atomic reservation semantics — it enforces the invariant locally, over data it owns, and treats the externally-sourced figure only as the *starting* available quantity, refreshed periodically per `AVAILABILITY_ARCHITECTURE.md`.

## 4. Locking / concurrency strategy

Two simultaneous requests for the same (part, source) are serialized through standard relational-database mechanisms — conceptually:

- The reservation write is a single conditional update against the running committed-quantity figure ("reserve N units if, and only if, at least N remain"), executed inside a transaction with row-level locking on that (part, source) ledger row. The database's own transaction isolation guarantees that two concurrent attempts against the same row cannot both read a stale "still available" figure and both succeed — one necessarily waits for the other's transaction to commit or roll back, then re-evaluates against the now-current figure.
- This is intentionally described as a *pattern* (a locked read-modify-write within a single transaction against one ledger row) rather than a specific SQL statement or ORM call — the exact implementation is a Phase 3 decision, but the architectural requirement it must satisfy is fixed here: **no two transactions may both successfully commit a reservation that together exceed the available quantity.**
- No distributed lock, external lock service, or message queue is introduced for this — a single-database transaction is sufficient and simpler (principle 2), since PostgreSQL is already the sole owner of the reservation ledger.

## 5. Idempotency

Every allocation *attempt* carries a client-supplied idempotency key (see `API_ARCHITECTURE.md` §4). If the same key is retried (e.g., after a dropped network response), the platform returns the original outcome (success or failure) rather than attempting a second reservation — this prevents a retried request from ever being able to double-allocate, independent of the locking guarantee in §4, which protects against *different* requests racing for the same stock.

## 6. Timeout / expiry

A `RESERVED` allocation that is not confirmed within an expiry window automatically becomes `EXPIRED`, releasing its held quantity (Phase 1 §2 step 8). The exact window length is a TO-BE business/operational decision (Phase 1 `HCME_BUSINESS_QUESTIONS.md` Q17); architecturally, expiry is enforced by a background process (or an on-read check — Phase 3 decision) that treats "past expiry and still `RESERVED`" as equivalent to a failed confirmation.

## 7. Release

Any `RESERVED` or `CONFIRMED` allocation is released (quantity returned to the committed-quantity ledger) when:

- The Fulfilment Request is cancelled (BR-06).
- Expiry occurs (§6).
- A downstream stage fails unrecoverably (e.g., Order creation fails past its retry window — `ORDER_ARCHITECTURE.md`).

Release is itself a transactional operation against the same ledger row, using the same locking pattern as reservation.

## 8. Partial allocation

The ledger and the Allocation entity both support recording "quantity requested" separately from "quantity allocated." Whether the business accepts a partial allocation automatically, or always requires explicit confirmation, is a TO-BE policy (Phase 1 `HCME_BUSINESS_QUESTIONS.md` Q9) — the architecture supports representing either outcome without a schema or engine change.

## 9. Cancellation

Cancellation of a Fulfilment Request after allocation but before Order creation triggers release (§7); after Order creation, cancellation is handled by `ORDER_ARCHITECTURE.md` §Cancellation, which in turn triggers the same release path if the allocation had not yet been fully consumed by a completed order flow.

## 10. Failure recovery

| Failure | Recovery |
|---|---|
| Reservation attempt fails (insufficient quantity) | Allocation → `FAILED`; caller is told definitively and immediately (no ambiguous "pending" state); the Fulfilment Request returns to Fulfilment Selection to try a different option. |
| Confirmation step fails/times out after `RESERVED` | Reservation remains held until its expiry window, then auto-releases (§6) — no orphaned, permanently-held stock. |
| Database transaction itself fails (infrastructure issue) | No partial write is possible — either the whole reservation transaction commits or none of it does; the caller receives a clear failure and may safely retry using the same idempotency key (§5). |

## 11. Future business rules — capability, not policy

Per BR-07, no Hitachi-specific VOR/priority allocation policy is designed here. The architecture reserves an extension point: an Allocation request may in future carry a priority/urgency indicator, and the reservation logic in §4 may in future consult a pluggable rule when two requests contend for the same final unit (e.g., "does either request carry a higher-priority flag") — but until such a rule is defined and approved by HCME, allocation is strictly first-committed-transaction-wins, with no implicit priority of any kind.
