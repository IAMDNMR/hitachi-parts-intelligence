# Phase 1 Summary — HCME Parts-to-Service Business Process

**Phase:** 1 — Business Process Design (complete)
**Input:** `OEM Parts Fulfilment Research Package (HCME).pdf` (Phase 0)
**Output:** `docs/business-process/` (14 documents) + this summary
**Next phase:** Phase 2 (technical architecture) — not started; awaiting approval.

## The agreed business journey

```
EXISTING PARTS STORE
  ↓
SELECT PART
  ↓
AVAILABILITY
  ↓
FULFILMENT OPTIONS
  ↓
SELECT FULFILMENT
  ↓
ALLOCATE
  ↓
ORDER
  ↓
SHIPMENT
  ↓
DEALER
  ↓
SERVICE / INSTALL
  ↓
CLOSE
```

Machine telemetry (ConSite, the confirmed Telematics API) is documented only as a **possible future upstream trigger** into Select Part. It is not a dependency of any stage in this journey — see `business-process/PHASE_1_DECISIONS.md` §3.

## What was produced

| Document | Contents |
|---|---|
| `business-process/HCME_PARTS_FULFILMENT_PROCESS.md` | The full ten-stage specification: purpose, actor, trigger, input, business decision, process, output, next state, failure cases, required/unknown information — for every stage. |
| `business-process/ACTORS_AND_RESPONSIBILITIES.md` | Actor definitions, a stage-by-stage responsibility matrix, the Dealer modelled as a first-class entity with its required (mostly unconfirmed) data fields, and a RACI summary. |
| `business-process/PROCESS_STATES.md` | Four state machines — Fulfilment Request, Allocation, Shipment, Service Job — each with a diagram and a state-meaning table. |
| `business-process/BUSINESS_RULES.md` | 14 numbered, cross-cutting invariants (e.g., no double-allocation, missing data ≠ zero stock, price resolved at order time, telemetry never a dependency). |
| `business-process/AVAILABILITY_PROCESS.md` | The `ON_HAND / RESERVED / ALLOCATED / AVAILABLE / UNKNOWN` status model and the rule that missing data is never treated as zero stock. |
| `business-process/FULFILMENT_PROCESS.md` | Fulfilment Options (computing candidates) and Fulfilment Selection (choosing one), including split/partial fulfilment as a defined capability. |
| `business-process/ALLOCATION_PROCESS.md` | The AVAILABLE/RESERVED/ALLOCATED distinction, the full allocation lifecycle, and the production concurrency requirement (no two users can allocate the same final unit). |
| `business-process/ORDER_PROCESS.md` | When an order is created, its fields, and why price is resolved at order time rather than stored as a fixed part attribute. |
| `business-process/SHIPMENT_PROCESS.md` | Order → Shipment → Dispatch → Tracking → Delivery, carrier-agnostic by design. |
| `business-process/DEALER_SERVICE_PROCESS.md` | Dealer receiving, the Service Job lifecycle, and the exact deterministic condition for Close. |
| `business-process/FAILURE_AND_EXCEPTION_CASES.md` | All 22 required failure/exception scenarios, each with user-visible behaviour, resulting state, retry/manual-intervention/continuation rules, and allocation-release rules. |
| `business-process/HCME_CONFIRMED_VS_UNKNOWN.md` | The authoritative ledger — 17 areas, each marked Confirmed / Unknown / TO-BE, sourced from Phase 0. This is the document every other document defers to. |
| `business-process/HCME_BUSINESS_QUESTIONS.md` | 31 open questions for HCME stakeholders, grouped BUSINESS / DATA / INTEGRATION / SECURITY / OPERATIONS. |
| `business-process/PHASE_1_DECISIONS.md` | Scope decisions, the telemetry exclusion rule, UNKNOWN-handling convention, and the naming/modelling conventions used consistently across all documents. |

## Validation performed before delivery

1. **Every stage covered** — all ten stages (Select Part → Close) are specified in `HCME_PARTS_FULFILMENT_PROCESS.md`, each with the full set of required fields (purpose, actor, trigger, input, business decision, process, output, next state, failure cases, information required, information unknown). None were skipped.
2. **No unsupported HCME assumption introduced** — every process document that needed a fact not present in the Phase 0 research routes to `HCME_CONFIRMED_VS_UNKNOWN.md` or `HCME_BUSINESS_QUESTIONS.md` instead of asserting one. No ERP, WMS, carrier, pricing rule, allocation/VOR policy, or dealer capability was invented.
3. **All UNKNOWN items explicitly marked** — consolidated in `HCME_CONFIRMED_VS_UNKNOWN.md` across 17 areas (dealer structure, European depot structure, inventory source, ERP, WMS, pricing, allocation, VOR/priority rules, order system, shipment system, carrier, tracking, service system, authentication, customer identity, dealer identity, telematics integration).
4. **Failure paths documented** — all 22 failure/exception cases required by the brief are covered in `FAILURE_AND_EXCEPTION_CASES.md`, each answering: what the user sees, resulting state, retry possibility, manual intervention need, whether the process can continue, and whether an allocation must be released.
5. **Internal consistency** — state names, entity field names, and actor names are fixed once in `PHASE_1_DECISIONS.md` §5 and used identically across all fourteen documents (cross-checked while writing). The Fulfilment Request state machine, Allocation state machine, Shipment state machine and Service Job state machine in `PROCESS_STATES.md` match the transitions described in every stage-level document.
6. **Documentation-only validation** — this phase produced no application code, schema, or technology choice, so no automated test suite applies; validation here is a structural/consistency review of the documents themselves (per this checklist), not a test run.

## Key design decisions worth flagging

- **Dealer is a first-class entity**, not a text field — its required data (identifier, branch, territory, address, contact, stock/fulfilment/service capability) is defined even though every one of those fields is currently unconfirmed for HCME Europe.
- **Availability and Fulfilment are strictly separated** — "where is it" vs "how do we get it there" — matching the Phase 0 finding that no OEM (Hitachi included) currently exposes this distinction in one open system.
- **Pricing is never a fixed attribute** — it is resolved at order time from an approved source, reflecting the Phase 0 finding that every OEM studied uses dealer/account-dependent pricing.
- **No Hitachi allocation/VOR policy is assumed** — only Caterpillar (Services Commitment) and Volvo CE (24-hour guarantee) publish anything close to this; Hitachi does not, so this process defines the *capability* for a future policy and nothing more.
- **Telemetry is fenced off** — ConSite and the Telematics API are real and confirmed, but they cannot become a silent dependency or an automatic trigger anywhere in this workflow.

## Not done (by design — belongs to Phase 2)

No database schema (PostgreSQL/Neo4j), no API design, no frontend changes, no technology/ERP/WMS/carrier selection, no authentication implementation. These require the open questions in `HCME_BUSINESS_QUESTIONS.md` to be answered first, or are explicitly deferred regardless.

---

**Phase 1 is complete. Waiting for approval before starting Phase 2.**
