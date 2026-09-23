# Phase 10B — Business Flow Validation

Validated 2026-09-23 against the live Neo4j AuraDB and the running FastAPI backend (not from memory of
earlier phases). Evidence: `backend/tests/test_phase10b_wiring.py`, `test_phase5_fulfilment.py`,
`test_phase6_allocation_order.py`, the shipment/service suites, and `phase10_data_audit.py`.

## 1. Journey under validation

```
Part Details ──Add to Cart──▶ Cart ──"Check stock & fulfil"──▶ Guided Checkout (per cart line)
   Availability → Fulfilment options → Option selected → Allocation → Order → Shipment → Service
Cart ──"Request Quote"──▶ Quote Request (separate journey; stored in Neo4j)
```

Part Details holds no ordering UI. Fulfilment is driven only from the Cart, and the quote journey is
separate from it.

## 2. State ownership (per `docs/business-process/PROCESS_STATES.md`)

| Entity | States | Owner of the journey status |
|---|---|---|
| Order | `CREATED`, `ACCEPTED`, `CANCELLED` only | — (commercial record) |
| FulfilmentRequest | `REQUESTED` → `AVAILABILITY_CHECKED` → `OPTION_SELECTED` → `ALLOCATION_PENDING` → … → `COMPLETED` | **FulfilmentRequest** |
| Shipment | dispatched → in transit → `DELIVERED` / `CANCELLED` | Shipment |
| ServiceJob | received → started → installed → `COMPLETE` | ServiceJob |

The Order never carries journey states. A previous "Order status" oddity was a design point, not a bug: the
journey status is read from the FulfilmentRequest.

## 3. Rules validated

| Rule | How it is checked | Result |
|---|---|---|
| A step cannot be skipped (e.g. no `ALLOCATION_PENDING` before an option is selected) | `test_invalid_state_transitions_rejected` | PASS |
| Only an offered option can be selected | `test_select_fulfilment_option_invalid_option` | PASS |
| Full API journey `REQUESTED → ALLOCATION_PENDING` | `test_fulfilment_journey_api_e2e` | PASS |
| A FulfilmentRequest completes only through a delivered shipment and its service link | `test_fulfilment_request_completes_via_shipment_only_service_link` | PASS |
| It is **not** completed while the shipment is undelivered | `test_fulfilment_request_not_completed_if_shipment_not_delivered` | PASS |
| API-driven order flow leaves no untagged nodes behind | `test_api_level_order_flow_leaves_no_untagged_nodes` | PASS |
| Candidate options carry labelled synthetic EUR transport data | `test_generate_fulfilment_options_available_source` | PASS |
| Catalogue parts read labelled synthetic stock at the real Oosterhout depot | `test_catalogue_part_uses_labelled_synthetic_depot_stock` | PASS |
| Order destination is a real dealer; shipments are delivered to a dealer; service dates are ordered | audit DQ-21, DQ-22, DQ-23, DQ-24, DQ-28 | PASS |
| No orphan orders or fulfilment requests; options are linked to their request | audit DQ-18, DQ-19, DQ-20 | PASS |

## 4. Result

Full backend suite: **206 passed, 0 failed.** Data audit: **40 / 42 checks pass**; the two failing
(DQ-06 dealer coordinates, DQ-37 duplicate supplier names) are source-data limitations documented in
`PHASE_10B_DATA_QUALITY_REPORT.md`. DQ-25 (parts without fitment) and DQ-30 (BOM/fitment mismatch) pass
after the Phase 10F fitment fill and BOM reseed.

## 5. Data honesty

Transport options, stock, supplier links, BOM quantities and certificates are `SYNTHETIC_DEMO` and are
labelled `synthetic: true` / `data_source: SYNTHETIC_DEMO` on every node and edge. No live HCME ERP,
carrier, tariff or stock feed is connected, and the UI says so.

## 6. Known gaps (not implemented, stated plainly)

- Customer, Sales Order and Purchase Order entities are not modelled.
- There is no separate Ship-To / Receiver party and no Order Review screen.
- Supplier-to-part sourcing from real SAP purchasing data is NOT_CONNECTED.
