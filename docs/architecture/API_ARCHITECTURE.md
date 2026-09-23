# API Architecture

Versioned from the beginning: every endpoint below lives under `/api/v1/...`. This is a **contract design**, not an implementation — no route is built in this phase. No endpoint exposes a database table shape directly; each response is a purpose-built representation of a Phase 1 concept.

**Authentication requirement**, stated once: every endpoint below requires a validated identity (mechanism TO-BE — see `SECURITY_ARCHITECTURE.md`); the specific authorization rule (which identity types may call it) is noted per endpoint.

## 1. Fulfilment Request

### `POST /api/v1/fulfilment-requests`
| | |
|---|---|
| Purpose | Create a Fulfilment Request from the Parts Store hand-off (Phase 1 Stage 1 — Select Part). |
| Request | Part Context: part number, quantity, machine/context (optional), destination, required-by date (optional). |
| Response | `201` Fulfilment Request: id, state=`REQUESTED`, echoed input, created timestamp. |
| Authorization | Customer or Dealer identity. |
| Validation | Part number resolvable and orderable; quantity > 0; destination present. Fitment checked where machine/context given (non-blocking warning if unconfirmed — Phase 1 failure case 3). |
| Error responses | `400` invalid input; `404` part not found; `422` part not orderable. |
| Idempotency | Client-supplied idempotency key (header) required; a repeat with the same key returns the original `201` response rather than creating a duplicate request. |
| State transition | — → `DRAFT` → `REQUESTED`. |

### `GET /api/v1/fulfilment-requests/{id}`
| | |
|---|---|
| Purpose | Retrieve the current state and full trace of a Fulfilment Request (used throughout the journey and for Close). |
| Response | Fulfilment Request with state, and references to its Availability Results, selected Fulfilment Option, Allocation, Order, Shipment, Service Job — whichever exist so far. |
| Authorization | The requesting customer/dealer/HCME staff associated with this request. |
| Error responses | `404` not found; `403` not authorized for this request. |
| Idempotency | N/A (read-only). |
| State transition | None (read). |

## 2. Availability

### `GET /api/v1/fulfilment-requests/{id}/availability`
| | |
|---|---|
| Purpose | Return Availability Results for the request (Phase 1 Stage 2), triggering a fresh query if none exist yet or if stale. |
| Response | Array of Availability Results: source, location, part, on-hand/reserved/allocated/available quantity, inventory timestamp, inventory source, status (`ON_HAND/RESERVED/ALLOCATED/AVAILABLE/UNKNOWN`). |
| Authorization | Same as parent Fulfilment Request. |
| Validation | Request must be in or past `REQUESTED` state. |
| Error responses | `404` request not found; `409` request in a terminal state (`CANCELLED`/`FAILED`). |
| Idempotency | Safe to call repeatedly (read/refresh, not a mutation of business state beyond caching the latest query — see `POSTGRESQL_DATA_ARCHITECTURE.md` Inventory). |
| State transition | Request `REQUESTED` → `AVAILABILITY_CHECKED` once at least one result set is produced. Per BR-01, missing source data never becomes a `0`-quantity result — it is returned as `UNKNOWN`. |

## 3. Fulfilment Options

### `GET /api/v1/fulfilment-requests/{id}/fulfilment-options`
| | |
|---|---|
| Purpose | Return the computed set of Fulfilment Options (Phase 1 Stage 3). |
| Response | Array of options: source, destination, transport mode, provider, processing time, transit time, ETA, transport cost, total cost, currency, constraints, availability confidence. No option is marked "recommended" or auto-sorted as a decision (BR-03). |
| Authorization | Same as parent request. |
| Validation | Request must be `AVAILABILITY_CHECKED`. |
| Error responses | `404`; `409` if no Availability Results exist yet; `422` if no viable option could be calculated (Phase 1 failure case 9) — returned with an explanatory body, not a bare 500. |
| Idempotency | Safe to call repeatedly. |
| State transition | None by itself (computation only; selection is the next call). |

### `POST /api/v1/fulfilment-requests/{id}/fulfilment-selection`
| | |
|---|---|
| Purpose | Record the chosen Fulfilment Option (Phase 1 Stage 4). |
| Request | Selected option ID. |
| Response | `200` updated Fulfilment Request, state=`OPTION_SELECTED`. |
| Authorization | Customer or Dealer, per Phase 1's open question on who selects (`ACTORS_AND_RESPONSIBILITIES.md` §2) — enforced once that TO-BE decision is made. |
| Validation | Option ID must belong to this request and still be valid (re-validated against current Availability — Phase 1 §Fulfilment Selection failure case). |
| Error responses | `400` invalid option; `409` option no longer valid (client should re-fetch options); `404`. |
| Idempotency | Re-submitting the same option ID is a no-op success; submitting a different one after selection is rejected (`409`) — selection is a one-time transition per request. |
| State transition | `AVAILABILITY_CHECKED` → `OPTION_SELECTED`. |

## 4. Allocation

### `POST /api/v1/fulfilment-requests/{id}/allocation`
| | |
|---|---|
| Purpose | Request allocation against the selected option's source (Phase 1 Stage 5). |
| Response | `201` Allocation: id, state, source, quantity, reserved/confirmed timestamps — or `409`/`422` on failure (see below). |
| Authorization | System-triggered following selection, or explicitly invoked by the frontend — either way, scoped to the request's own customer/dealer. |
| Validation | Request must be `OPTION_SELECTED`. Enforces the concurrency-safe commit described in `ALLOCATION_ARCHITECTURE.md` — this is the one call in the whole API where a race between two callers is expected and must be handled correctly. |
| Error responses | `409` allocation failed (insufficient stock at commit time — Phase 1 failure case 11); `422` invalid state. |
| Idempotency | Client-supplied idempotency key required; required because a client retry after a dropped response must never risk a second allocation attempt succeeding independently. |
| State transition | `OPTION_SELECTED` → `ALLOCATION_PENDING` → `ALLOCATED` (or Allocation `FAILED`, request returns toward selection). |

### `GET /api/v1/fulfilment-requests/{id}/allocation`
| | |
|---|---|
| Purpose | Retrieve current Allocation status (e.g., to detect `EXPIRED`). |
| Response | Allocation record. |
| Authorization | Same as parent request. |
| Error responses | `404` no allocation yet. |
| Idempotency | N/A (read). |
| State transition | None. |

## 5. Order

### `POST /api/v1/fulfilment-requests/{id}/order`
| | |
|---|---|
| Purpose | Create the Order once Allocation is `CONFIRMED` (Phase 1 Stage 6). |
| Response | `201` Order: id, order number, price, shipping cost, tax, total, status=`CREATED`. |
| Authorization | Same as parent request. |
| Validation | Allocation must be `CONFIRMED`; price must be resolvable from an approved pricing source (BR-04) — if not, the call fails rather than defaulting a price. |
| Error responses | `409` allocation not confirmed; `502` pricing source unavailable (Phase 1 failure case 13); `422`. |
| Idempotency | Client-supplied idempotency key required; also naturally idempotent server-side because an Allocation can only be `CONSUMED` once (attempting to order an already-`CONSUMED` allocation returns the existing Order rather than erroring). |
| State transition | Allocation `CONFIRMED` → `CONSUMED`; request `ALLOCATED` → `ORDERED`. |

### `GET /api/v1/orders/{orderId}`
| | |
|---|---|
| Purpose | Retrieve an Order (Phase 1 Stage 6 output; also used by Dealer/Service views). |
| Response | Order with lines, references to Allocation, Shipment, Service Job. |
| Authorization | Customer, associated Dealer, or HCME staff. |
| Error responses | `404`; `403`. |
| Idempotency | N/A. |
| State transition | None. |

## 6. Shipment & Tracking

### `GET /api/v1/orders/{orderId}/shipment`
| | |
|---|---|
| Purpose | Retrieve the Shipment for an Order (Phase 1 Stage 7). |
| Response | Shipment: carrier/provider, service level, tracking number, origin, destination, ETA, status. |
| Authorization | Customer, associated Dealer, or HCME staff. |
| Error responses | `404` no shipment yet (order not yet `ACCEPTED`/dispatched). |
| Idempotency | N/A (read). |
| State transition | None. |

### `GET /api/v1/shipments/{shipmentId}/tracking`
| | |
|---|---|
| Purpose | Retrieve the Shipment Event history. |
| Response | Ordered array of events (type, timestamp, source). |
| Authorization | Same as Shipment. |
| Error responses | `404`. |
| Idempotency | N/A. |
| State transition | None (events are appended by an internal/webhook process, not by this read endpoint — see `SHIPMENT_ARCHITECTURE.md`). |

## 7. Dealer

### `GET /api/v1/dealers/{dealerId}`
| | |
|---|---|
| Purpose | Retrieve Dealer/Dealer Branch data (Phase 1 Stage 8 context; used wherever a destination or receiving party needs to be shown). |
| Response | Dealer: id, branches, territory, address, contact, stock/fulfilment/service capability flags — populated only where CONFIRMED/TO-BE data exists (see `DEALER_ARCHITECTURE.md`); unpopulated fields are returned as explicitly absent, not defaulted. |
| Authorization | Any authenticated identity associated with that dealer, or HCME staff. |
| Error responses | `404`. |
| Idempotency | N/A. |
| State transition | None. |

## 8. Service

### `POST /api/v1/orders/{orderId}/service-jobs`
| | |
|---|---|
| Purpose | Open a Service Job once the Dealer confirms receipt (Phase 1 Stage 8→9). |
| Request | Dealer Branch confirming receipt; condition notes. |
| Response | `201` Service Job: id, state=`OPEN`→`PART_RECEIVED`, machine, dealer, order references. |
| Authorization | Dealer Branch staff. |
| Validation | Order's Shipment must be `DELIVERED`; received part/quantity checked against the Order (BR-12) — mismatch is a failure case, not silently accepted. |
| Error responses | `409` shipment not yet delivered; `422` receipt mismatch (Phase 1 failure case 17). |
| Idempotency | One Service Job per Order — a repeat call returns the existing job. |
| State transition | Service Job `OPEN` → `PART_RECEIVED`. |

### `PATCH /api/v1/service-jobs/{id}`
| | |
|---|---|
| Purpose | Update Service Job progress (technician assignment, `IN_PROGRESS`, `PART_INSTALLED`, notes/evidence) — Phase 1 Stage 9. |
| Request | Field(s) to update (status transition, technician, timestamps, notes). |
| Response | `200` updated Service Job. |
| Authorization | Dealer Branch / Technician. |
| Validation | Only forward-legal transitions accepted (`PART_RECEIVED → IN_PROGRESS → PART_INSTALLED`) — see `STATE_TRANSITION_ARCHITECTURE.md`; no illegal jump (e.g., `OPEN → COMPLETED` directly) is possible. |
| Error responses | `409` illegal transition; `422` invalid field. |
| Idempotency | Re-sending the same target status is a no-op success. |
| State transition | As requested, forward-only per §above. |

### `POST /api/v1/service-jobs/{id}/complete`
| | |
|---|---|
| Purpose | Confirm Service Job completion (Phase 1 Stage 9→10). |
| Request | Completion confirmation, completion timestamp, evidence reference if required. |
| Response | `200` Service Job state=`COMPLETED`; if the linked Shipment is also `DELIVERED`, the parent Fulfilment Request is closed in the same operation (Phase 1 `DEALER_SERVICE_PROCESS.md` §3). |
| Authorization | Dealer Branch / Technician. |
| Validation | Job must be `PART_INSTALLED` before it can complete. |
| Error responses | `409` job not yet `PART_INSTALLED`. |
| Idempotency | Re-calling on an already-`COMPLETED` job returns the same result. |
| State transition | Service Job `PART_INSTALLED` → `COMPLETED`; Fulfilment Request → `COMPLETED` if both close conditions are met. |

## Cross-cutting API rules

- **No internal database shape leaks**: every response above is a purpose-built DTO named for its business concept (Availability Result, Fulfilment Option, Allocation, Order, Shipment, Service Job), not a raw table row.
- **Idempotency keys** are required on every state-changing (`POST`) call that could plausibly be retried by a flaky client — most importantly Allocation and Order creation, where a duplicate attempt must never double-commit.
- **Errors are structured** (`{ "error": { "code": ..., "message": ..., "details": ... } }` — exact shape is a Phase 3 implementation detail) and never leak internal system details (matches the existing `part-enrichment.js` pattern of logging server-side, returning a generic message).
- **UNKNOWN data is a normal response, not an error** — e.g., an Availability Result with status `UNKNOWN` is returned in a `200`, not surfaced as a failure.
