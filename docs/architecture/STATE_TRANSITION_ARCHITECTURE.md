# State Transition Architecture

Maps the Phase 1 state machines (`PROCESS_STATES.md`) onto the backend modules (`BACKEND_ARCHITECTURE.md`) and API (`API_ARCHITECTURE.md`). **No illegal transition is possible**: every transition below is enforced server-side as an explicit, whitelisted move from a specific source state; any other requested transition is rejected (`409`), never silently coerced.

## A. Fulfilment Request

| Transition | Who can trigger | Preconditions | Data changes | Side effects | Failure behaviour | Audit |
|---|---|---|---|---|---|---|
| `DRAFT → REQUESTED` | Platform, on `POST /fulfilment-requests` | Valid, orderable Part Context | Fulfilment Request row created | None external | Validation failure → request never persists past `DRAFT` | Yes — creation event |
| `REQUESTED → AVAILABILITY_CHECKED` | Platform, on Availability query completing | Request is `REQUESTED` | Availability Results persisted | Queries `InventoryProvider` adapter(s) | Adapter failure → result recorded `UNKNOWN`, transition still occurs (BR-01) | Yes — availability-checked event with result summary |
| `AVAILABILITY_CHECKED → OPTION_SELECTED` | Customer/Dealer, via Fulfilment Selection | ≥1 valid Fulfilment Option exists; selected option still valid | Selected option flagged on the request | None | Invalid/stale option → `409`, no transition | Yes |
| `OPTION_SELECTED → ALLOCATION_PENDING → ALLOCATED` | Platform, on Allocation call | Option selected | Allocation created/confirmed (see §B) | Commits against source inventory | Allocation `FAILED` → request returns to `OPTION_SELECTED` (or `AVAILABILITY_CHECKED` if the business chooses to re-run options) | Yes — both the attempt and the outcome |
| `ALLOCATED → ORDERED` | Platform, on Order creation | Allocation `CONFIRMED` | Order + Order Lines created; Allocation → `CONSUMED` | Resolves price via `PricingProvider` | Pricing/order failure → request remains `ALLOCATED`, Allocation not yet consumed (BR-05) | Yes |
| `ORDERED → FULFILMENT → SHIPPED` | Platform, on source acceptance / Shipment dispatch | Order `ACCEPTED`; Shipment created | Shipment row created/updated | Calls `ShipmentProvider` | Shipment creation failure → request remains `ORDERED`/`FULFILMENT` | Yes |
| `SHIPPED → DELIVERED` | Platform, on carrier delivery confirmation | Shipment event confirms delivery | Shipment → `DELIVERED` | Triggers Service Job creation eligibility (Dealer stage) | Delivery disputed → Shipment `EXCEPTION`, request stays `SHIPPED` | Yes |
| `DELIVERED → COMPLETED` | Platform, automatic | Shipment `DELIVERED` **and** Service Job `COMPLETED` (Phase 1 BR-11) | Request marked `COMPLETED`, closed timestamp set | None further | N/A — this transition cannot fail once its two preconditions hold | Yes — the closing event, referencing both preconditions |
| `* → CANCELLED` | Customer (before shipment) or HCME staff | Request not already terminal | Request → `CANCELLED`; any `RESERVED`/`CONFIRMED` Allocation released (BR-06) | Allocation release; Order → `CANCELLED` if one exists | N/A | Yes |
| `* → FAILED` | Platform, on unrecoverable failure (e.g., allocation exhausted with no remaining option) | No viable path forward | Request → `FAILED` | Allocation released if held | N/A | Yes |

## B. Allocation

| Transition | Who can trigger | Preconditions | Data changes | Side effects | Failure behaviour | Audit |
|---|---|---|---|---|---|---|
| `— → PENDING` | Platform, on allocation request | Fulfilment Request `OPTION_SELECTED` | Allocation row created | None yet | N/A | Yes |
| `PENDING → RESERVED` | Platform | Source quantity check succeeds, committed atomically (see `ALLOCATION_ARCHITECTURE.md`) | Inventory Reservation persisted | None external | Insufficient quantity → `PENDING → FAILED` | Yes |
| `PENDING → FAILED` | Platform | Quantity check fails | Allocation → `FAILED` | None | Terminal for this allocation attempt | Yes |
| `RESERVED → CONFIRMED` | Platform, within the expiry window | Reservation still valid, not expired | Allocation → `CONFIRMED` | None | Window exceeded → `EXPIRED` instead | Yes |
| `RESERVED → EXPIRED` | Platform (time-based) | Expiry window elapsed without confirmation | Allocation → `EXPIRED`; held quantity released | Notifies Fulfilment Request (returns to Fulfilment Selection) | N/A | Yes |
| `CONFIRMED → CONSUMED` | Platform, on Order creation | Order successfully created | Allocation → `CONSUMED` | None further | If Order creation fails, this transition does not occur (Allocation stays `CONFIRMED`) | Yes |
| `RESERVED/CONFIRMED → RELEASED` | Platform, on cancellation/downstream failure | Fulfilment Request cancelled or a downstream stage fails unrecoverably | Allocation → `RELEASED`; quantity returned | None | N/A | Yes |

## C. Shipment

| Transition | Who can trigger | Preconditions | Data changes | Side effects | Failure behaviour | Audit |
|---|---|---|---|---|---|---|
| `— → CREATED` | Platform, on Order `ACCEPTED` | Order accepted, Fulfilment Option has a transport plan | Shipment row created | Calls `ShipmentProvider` | Provider failure → creation retried per resilience policy (`RESILIENCE_ARCHITECTURE.md`); Order remains `ACCEPTED` until it succeeds | Yes |
| `CREATED → DISPATCHED` | `ShipmentProvider` event (webhook/poll) | Carrier confirms pickup | Shipment status updated | None | Missing/late event → status stays `CREATED`, flagged if overdue | Yes |
| `DISPATCHED → IN_TRANSIT` | `TrackingProvider` event | Carrier reports transit | Shipment Event appended | None | N/A | Yes |
| `IN_TRANSIT → DELIVERED` | `TrackingProvider` event or Dealer confirmation | Delivery confirmed | Shipment → `DELIVERED` | Enables Dealer/Service stage | Disputed delivery → `EXCEPTION` | Yes |
| `DISPATCHED/IN_TRANSIT → EXCEPTION` | `TrackingProvider` event (delay/loss/damage) | Carrier reports an issue | Shipment → `EXCEPTION`, event logged | Customer/dealer notified | May resolve back to `IN_TRANSIT` or escalate to `CANCELLED` | Yes |
| `* → CANCELLED` | HCME staff / Platform | Shipment confirmed unrecoverable, or cancelled pre-dispatch | Shipment → `CANCELLED` | Triggers business decision on replacement (Phase 1, TO-BE) | N/A | Yes |

## D. Service Job

| Transition | Who can trigger | Preconditions | Data changes | Side effects | Failure behaviour | Audit |
|---|---|---|---|---|---|---|
| `— → OPEN` | Platform, on Order `ACCEPTED` (created early, held until receipt) or on Shipment `DELIVERED` | Order exists | Service Job row created | None | N/A | Yes |
| `OPEN → PART_RECEIVED` | Dealer Branch, `POST .../service-jobs` | Shipment `DELIVERED`; received part/qty matches Order (BR-12) | Receipt recorded | None | Mismatch → `422`, job stays `OPEN`, flagged (Phase 1 failure case 17/18) | Yes |
| `PART_RECEIVED → IN_PROGRESS` | Technician/Dealer Branch, `PATCH` | Job `PART_RECEIVED` | Start time, technician recorded | None | N/A | Yes |
| `IN_PROGRESS → PART_INSTALLED` | Technician, `PATCH` | Job `IN_PROGRESS` | Installation confirmation, notes recorded | None | Cannot-install case → job stays `IN_PROGRESS`, flagged (Phase 1 failure case 19) | Yes |
| `PART_INSTALLED → COMPLETED` | Technician/Dealer Branch, `.../complete` | Job `PART_INSTALLED` | Completion time recorded | Triggers Fulfilment Request Close check (§A) | N/A | Yes |
| `* → CANCELLED` | Dealer Branch / Customer (via HCME) | Job not already terminal | Job → `CANCELLED`, reason recorded | Fulfilment Request does not close via this job (business decision on outcome, TO-BE) | N/A | Yes |

## E. Order (status, not a full Phase 1 state machine, but transitions are equally guarded)

| Transition | Who can trigger | Preconditions | Data changes | Side effects | Failure behaviour | Audit |
|---|---|---|---|---|---|---|
| `— → CREATED` | Platform, on Order creation | Allocation `CONFIRMED`, price resolved | Order + Order Lines created | Allocation → `CONSUMED` | Pricing/creation failure → no Order row committed | Yes |
| `CREATED → ACCEPTED` | Platform, on source acceptance | Order `CREATED` | Status updated | Enables Shipment creation | Rejection → business decision (TO-BE); order may be cancelled | Yes |
| `* → CANCELLED` | Customer/HCME, before shipment | Order not yet shipped | Status updated; linked Allocation released if not yet consumed elsewhere | Fulfilment Request → `CANCELLED` | N/A | Yes |

## Enforcement pattern (applies to all four/five machines)

Every transition is implemented as a single function per (entity type, source state, event) triple that:

1. Loads the current state within a transaction.
2. Verifies the source state matches what the caller expects (optimistic-concurrency style — see `ALLOCATION_ARCHITECTURE.md` for where this is strictest).
3. Applies the new state and any associated data changes atomically.
4. Writes the Audit record in the same transaction (`AUDIT_ARCHITECTURE.md`).
5. Returns the new state to the caller; any attempted transition not in the whitelisted table above is rejected before step 1 completes.

This keeps "no illegal state transition is possible" a property of the code path itself, not a convention callers must follow.
