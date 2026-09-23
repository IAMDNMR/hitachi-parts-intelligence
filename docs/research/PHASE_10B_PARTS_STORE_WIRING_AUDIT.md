# Phase 10B — Parts Store Wiring Audit

Traced from the live source code and the running Neo4j graph, 2026-09-23. Not from memory of earlier
phases' documentation.

## 1. Current entry structure (confirmed correct — already matches §10/§11)

```
Part Details (frontend/pages/PartsStore/PartsStore.tsx, product Quick View modal)
  → "Add to Cart"  (addToCart(), line 276 — pushes a CartItem into React state + localStorage)
  → no fulfilment/ordering UI is rendered on this screen (AvailabilityChecker has exactly ONE
    usage in the file, inside QuoteCartPanel — verified by grep, not by memory)

Cart (QuoteCartPanel component)
  → per line: "Check stock & fulfil"   → opens <AvailabilityChecker> inline for that ONE cart line
  → whole cart: "Request Quote →"      → opens <QuoteRequestForm>, the SEPARATE quote journey
```

These two journeys are already properly separated and Cart-driven, not Part-Details-driven. This was
corrected in the previous Phase 10 session (per user feedback) and is confirmed intact.

## 2. Stage-by-stage wiring: Parts Order journey

| Stage | Frontend | API | Neo4j service | Node/relationship written | State transition | Gaps found |
|---|---|---|---|---|---|---|
| **Requester** | `AvailabilityChecker.tsx` — "Your name"/"Your email" fields (**added this session**) | `POST /fulfilment-requests` | `app/api/v1/fulfilment.py:create_fulfilment_request` | `(:Customer {email})-[:REQUESTED]->(:FulfilmentRequest)` (**new**) | — | Previously **no requester identity was captured at all** — `customer_id` was a hardcoded `"CUST-DEFAULT"` constant, existing only as a string, never as a real Customer node. Fixed this session. |
| **Ship-To / Receiver (Dealer)** | same form — "Destination Dealer" `<select>`, populated from `GET /api/v1/dealers` | same call, `destinationBranchId` | same | `FulfilmentRequest.destinationBranchId` (a real `DealerBranch.dealer_id`) | `DRAFT → REQUESTED` | Ship-To and Receiver are the same field (one dealer selection serves both). No separate "ship-to address" vs "receiving dealer" distinction exists — acceptable for this prototype since HCME dealers are both. |
| **Availability** | same component, same submit | `POST /fulfilment-requests/{id}/availability` | `app/modules/availability/service.py:check_availability` | `(:InventoryCache)` per source, `FulfilmentRequest.status` | `REQUESTED → AVAILABILITY_CHECKED` | none |
| **Source / Depot** | rendered inside `avail-results` | (same call, `GET /fulfilment-requests/{id}/availability` for re-read) | same | `InventoryCache.sourceId/locationId` | — | Only ever resolves to the real Oosterhout depot (`DEPOT-OOSTERHOUT`) for catalogue parts — see `synthetic_inventory_adapter.py` from the prior session's fix. |
| **Fulfilment Options / Transportation** | `FulfilmentOptionSelector.tsx` | `POST /fulfilment-requests/{id}/options`, `GET .../options` | `app/modules/fulfilment/service.py:generate_fulfilment_options` | `(:FulfilmentOption)` | (no FR status change) | Transportation is `NOT_CONNECTED` (mode/carrier/ETA/cost are null) unless a routing/rate provider is confirmed — verified live, matches §15. No fabricated €35/€65/1-day values exist anywhere in the current graph (DQ-07/DQ-09 PASS). |
| **Order Review** | *(none — no dedicated review screen)* | — | — | — | — | **Gap**: there is no explicit "review before you commit" screen; selecting an option immediately writes `isSelected: true` and the UI moves straight to Allocate. Not fixed this session — flagged as a real, honest gap rather than silently left unlabelled. |
| **Select Fulfilment** | `FulfilmentOptionSelector.tsx` "Select" | `POST /fulfilment-requests/{id}/select-option` | `select_fulfilment_option` | `FulfilmentOption.isSelected`, `FulfilmentRequest.selectedOptionId` | `AVAILABILITY_CHECKED → OPTION_SELECTED` | none |
| **Allocation** | `FulfilmentOptionSelector.tsx` "Confirm & Proceed to Allocation" then `AllocationOrderPanel.tsx` "Allocate Inventory" | `POST .../proceed-to-allocation`, `POST .../allocation` | `proceed_to_allocation_pending`, `create_allocation` | `(:Allocation)`, `InventoryLedger` (optimistic-locked) | `OPTION_SELECTED → ALLOCATION_PENDING → ALLOCATED` | Concurrency protection (version-checked ledger) preserved and unmodified — see `test_phase6_allocation_order.py` concurrency tests, all passing. |
| **Order** | `AllocationOrderPanel.tsx` "Place Order" | `POST /fulfilment-requests/{id}/order` | `create_order` | `(:Order)`, `(:Order)-[:BASED_ON_ALLOCATION]->(:Allocation)`, `(:FulfilmentRequest)-[:HAS_ORDER]->(:Order)` | `ALLOCATED → ORDERED`; `Order.status = CREATED` | **Bug found and fixed this session**: `create_order()` never tagged the `Order` node with `testRunId` even when passed one — every API-level test leaked a real Order into the live database. Fixed (§ PHASE_10B_BUSINESS_FLOW_VALIDATION.md). |
| **Shipment / Tracking** | `AllocationOrderPanel.tsx` "Create & Dispatch Shipment" / "Simulate Carrier Dispatch" / "Confirm Delivery" | `POST /shipments`, `POST /shipments/{id}/dispatch`, `POST /shipments/{id}/deliver` | `app/modules/shipment/service.py` | `(:Shipment)`, `(:ShipmentEvent)`, `FulfilmentRequest.status` | `ORDERED → FULFILMENT → SHIPPED → DELIVERED` | Carrier/tracking data is `SYNTHETIC_DEMO` and labelled as such in the UI; no real carrier integration exists (documented, not fabricated). |
| **Dealer Receipt / Service** | `AllocationOrderPanel.tsx` service milestone buttons | `POST /service-jobs`, `.../receive-part`, `.../start`, `.../install-part`, `.../complete` | `app/modules/service/service.py` | `(:ServiceJob)`, `(:ServiceEvent)` | `OPEN → PART_RECEIVED → IN_PROGRESS → PART_INSTALLED → COMPLETED` | `receive_part()` already correctly refuses to progress unless the linked Shipment is `DELIVERED` (verified in code, not assumed). |
| **Close** | same panel, "✓ Fulfilment Journey Successfully Closed" banner | (client-side only — driven by `serviceJob.status === 'COMPLETED'`) | `complete_service()` also closes the FulfilmentRequest server-side | `FulfilmentRequest.status = COMPLETED` | `DELIVERED → COMPLETED` | **Bug found and fixed this session**: the Cypher that closes the `FulfilmentRequest` looked for a direct `FulfilmentRequest-[:HAS_SERVICE_JOB]->ServiceJob` or `Order-[:HAS_SERVICE_JOB]->ServiceJob` edge; the demo data's actual shape only had `Shipment-[:HAS_SERVICE_JOB]->ServiceJob`, so `fr.status` silently stayed at `ORDERED` forever even though the UI showed "Successfully Closed". Fixed — see `PHASE_10B_BUSINESS_FLOW_VALIDATION.md` §1. **Note**: the UI's "Closed" banner is driven only by `ServiceJob.status`, not by the corrected `FulfilmentRequest.status` — this is honest (the service job genuinely did complete) but does not yet surface the FulfilmentRequest-level closure to the user; flagged as a follow-up, not fixed this session (kept the change surgical to the server-side bug). |
| **Order.status itself** | `AllocationOrderPanel.tsx` "Price: …" line | `GET /orders/{id}` | `get_order` | — | stays `ACCEPTED`/`CREATED` forever | **Not a bug** — confirmed against `docs/business-process/ORDER_PROCESS.md` §4, which explicitly states Order status is `CREATED`/`ACCEPTED`/`CANCELLED` only and that "shipment-related status lives on the Shipment entity, not the Order." The FulfilmentRequest is the documented owner of overall journey status, and that is what was actually broken (see above) — not the Order entity. |

## 3. Quote Request journey (separate, unmodified)

```
Cart → "Request Quote →" → QuoteRequestForm (name/email/phone/note)
  → POST /api/v1/quote-request
  → (:Customer {email}) -[:SUBMITTED]-> (:PartsInquiry) -[:REQUESTS]-> (:RequestedPart) -[:FOR_PART]-> (:Part)
```

Confirmed unchanged and untouched by this session's fixes. Does not intersect with the Order journey's
`FulfilmentRequest`/`Order` graph at all — verified by grep (`quote-request` only appears in
`PartsStore.tsx` and `backend/app/api/v1/quote_request.py`).

## 4. Failure cases exercised

| Case | Where enforced | Verified |
|---|---|---|
| Allocate against `UNKNOWN`/stale availability | `create_allocation()` raises `UnprocessableError` | existing test, still passing |
| Order before allocation `CONFIRMED` | `create_order()` raises `ConflictError` | existing test, still passing |
| Dealer receipt before shipment `DELIVERED` | `receive_part()` raises `ConflictError` | existing test + new Phase 10B test |
| Complete service against an undelivered shipment | **new defence-in-depth check** in the FulfilmentRequest-closing query (`sh.status = 'DELIVERED'` guard) | new Phase 10B test |
| Concurrent allocation against the same ledger row | optimistic version check in `attempt_inventory_allocation` | existing tests, unmodified, still passing |
