# Order Architecture

```
Fulfilment Request → Allocation → Order
```

Implements Phase 1 `ORDER_PROCESS.md` and BR-04/BR-05.

## 1. Order ownership

The Orders module (`BACKEND_ARCHITECTURE.md`) owns the Order and Order Line entities outright in PostgreSQL. Whether this becomes, in a later phase, a synced projection of an external order-management system is UNKNOWN today (see `DATA_OWNERSHIP.md`) — this architecture does not assume one exists.

## 2. Order lifecycle

`CREATED → ACCEPTED → (fulfilled)`, or `CANCELLED` — see `STATE_TRANSITION_ARCHITECTURE.md` §E for the full transition table.

## 3. Order numbering

A human-readable order number is generated at creation, separate from the internal database identifier, so it can be communicated to customers/dealers without exposing internal keys. The exact numbering scheme (sequence, prefix, per-region format) is a Phase 3 implementation detail; the architectural requirement is that it is generated atomically with the Order row (no gap where an Order could exist without a number, and no scheme that could collide under concurrent creation).

## 4. Idempotency

Order creation is called once per confirmed Allocation (`API_ARCHITECTURE.md` §5). Because an Allocation can only be `CONFIRMED → CONSUMED` once, a retried order-creation call against an already-`CONSUMED` allocation returns the existing Order rather than creating a second one — idempotency here is a natural consequence of the Allocation state machine, reinforced by the same idempotency-key mechanism used elsewhere (`API_ARCHITECTURE.md` §Cross-cutting rules).

## 5. Pricing resolution

Per BR-04, price is **never** a stored, static attribute of a Part. At Order creation:

1. The Orders module calls a `PricingProvider` adapter (see `INTEGRATION_ARCHITECTURE.md`) with (customer, part, quantity, dealer) as input.
2. If a price is returned, the Order is created with that price, and the resolution is recorded (provider, timestamp) for audit.
3. If no price can be resolved, Order creation fails (`502`, Phase 1 failure case 13) — no default, cached, or estimated price is ever substituted.

No real `PricingProvider` implementation is confirmed today (see `DATA_OWNERSHIP.md`); only a mock/test implementation may exist for development, never presented as a real price.

## 6. Shipping cost and tax

- Shipping cost is carried over from the selected Fulfilment Option (`FULFILMENT_ARCHITECTURE.md`), not re-resolved at Order time.
- Tax is resolved via the same class of external-source dependency as pricing (jurisdiction/customer-type rules) — UNKNOWN system, same failure discipline as §5 (no fabricated tax figure).

## 7. Total

`total = price + shipping cost + tax`, computed once all three inputs are resolved; if any one fails to resolve, the whole Order creation fails rather than proceeding with a partial total.

## 8. Cancellation

- Before shipment: Order → `CANCELLED`; any Allocation not yet otherwise consumed is released (`ALLOCATION_ARCHITECTURE.md` §7, §9); Fulfilment Request → `CANCELLED`.
- After shipment has begun: cancellation becomes a shipment-level concern (`SHIPMENT_ARCHITECTURE.md`) — the Order itself is not silently reverted once physical fulfilment is underway; the business decision on how to handle an in-flight cancellation is TO-BE (Phase 1 `HCME_BUSINESS_QUESTIONS.md`).

## 9. Modification

Order Lines are immutable once the Order is `ACCEPTED` (`POSTGRESQL_DATA_ARCHITECTURE.md`). A change after acceptance is modelled as a new Fulfilment Request (and therefore a new Order), not an in-place edit — this keeps the audit trail unambiguous and avoids retroactively changing a record another system (once confirmed) may already have acted on.

## 10. Audit

Every Order creation, acceptance, and cancellation is an audited event (`AUDIT_ARCHITECTURE.md`), including the pricing resolution's provider/timestamp, so a disputed price can always be traced to exactly what was resolved, by whom (which provider), and when.
