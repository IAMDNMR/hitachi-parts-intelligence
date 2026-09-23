# Audit Architecture

Every important business action is traceable: **who, what, when, previous state, new state, source, correlation/request ID** — recorded by the Audit module (`BACKEND_ARCHITECTURE.md`), in the same PostgreSQL transaction as the change it describes (`POSTGRESQL_DATA_ARCHITECTURE.md` §Audit Record), so audit and state can never disagree.

## 1. Audited actions (minimum, per the brief)

| Action | Who (actor) | What | Previous → New state | Source | Correlation |
|---|---|---|---|---|---|
| Availability decision (query executed, results returned) | Platform (on behalf of Customer/Dealer) | Availability query for a Fulfilment Request | `REQUESTED → AVAILABILITY_CHECKED` | `InventoryProvider` per source (or `UNKNOWN`) | Fulfilment Request ID |
| Fulfilment selection | Customer/Dealer | Option chosen | `AVAILABILITY_CHECKED → OPTION_SELECTED` | User action | Fulfilment Request ID |
| Allocation (attempt and outcome) | Platform | Reservation/confirmation attempt | `PENDING → RESERVED/FAILED`, `RESERVED → CONFIRMED/EXPIRED` | Internal (ledger) | Fulfilment Request ID, Allocation ID |
| Allocation release | Platform (system) or Customer (via cancellation) | Release of held quantity | `RESERVED/CONFIRMED → RELEASED` | Cancellation, expiry, or downstream failure | Allocation ID |
| Order creation | Platform | Order assembled | `— → CREATED`; Allocation `CONFIRMED → CONSUMED` | `PricingProvider` resolution reference | Order ID, Fulfilment Request ID |
| Order cancellation | Customer/HCME staff | Order cancelled | `CREATED/ACCEPTED → CANCELLED` | User action | Order ID |
| Shipment creation | Platform | Shipment created via `ShipmentProvider` | `— → CREATED` | Provider response reference | Shipment ID, Order ID |
| Shipment update | `TrackingProvider` event or manual entry | Status/event change | Per `STATE_TRANSITION_ARCHITECTURE.md` §C | Carrier event / manual actor | Shipment ID |
| Service status change | Technician/Dealer Branch | Job progress | Per `STATE_TRANSITION_ARCHITECTURE.md` §D | User action | Service Job ID |

## 2. Record shape (conceptual)

| Field | Description |
|---|---|
| Actor | The identity (customer/dealer staff/technician/HCME staff/"platform" for system-triggered actions) that performed the action. |
| Action | A fixed vocabulary of action names, one per row-type in §1 (e.g., `ALLOCATION_RESERVED`, `ORDER_CANCELLED`). |
| Timestamp | When the action was recorded (server time, not client-supplied). |
| Entity type + ID | Which entity (Fulfilment Request, Allocation, Order, Shipment, Service Job, …) this action concerns. |
| Previous state | The state before this action, where applicable. |
| New state | The state after. |
| Source | Where the triggering data came from (a specific adapter/provider, a user action, an internal timer) — critical for the "unknown vs failed vs confirmed" distinction to remain traceable after the fact. |
| Correlation/request ID | Ties every audit record from a single API call (and any downstream adapter calls it triggered) together, so a support investigation can reconstruct the full causal chain from one ID. |

## 3. What audit is not

- Not a substitute for the state machines themselves (`PROCESS_STATES.md`, `STATE_TRANSITION_ARCHITECTURE.md`) — audit *records* transitions; it does not enforce them.
- Not a general application log — see `OBSERVABILITY_ARCHITECTURE.md` for operational logging, which is a separate (though correlated, via the same request ID) concern.
- Not exposed to any frontend by default — audit records are for HCME/compliance/support use, surfaced through a separate, later-designed internal tool if needed, not through the customer/dealer-facing API in `API_ARCHITECTURE.md`.

## 4. Retention

Retention period is an open question (Phase 1 `HCME_BUSINESS_QUESTIONS.md` Q26) — the architecture stores audit records as append-only and never auto-deletes them; an actual retention/archival policy is a Phase 3+/operational decision once HCME confirms requirements.
