# Phase 1 — Scope Decisions & Conventions

This document records the working decisions made while producing the Phase 1 business-process specification, so later phases (and reviewers) understand *why* the other documents are shaped the way they are.

## 1. What Phase 1 is and is not

Phase 1 defines **what the business process must do** — actors, triggers, decisions, states, data required, and failure handling — for the HCME Parts-to-Service fulfilment journey.

Phase 1 explicitly does **not**:

- Write application code, or change the existing Parts Store frontend.
- Design a database schema (PostgreSQL, Neo4j, or otherwise).
- Choose an ERP, WMS, carrier, message broker, cloud provider, or any other technology.
- Define API endpoints, service boundaries, or an authentication implementation.
- Invent HCME-specific systems, APIs, pricing rules, allocation policies, dealer capabilities, or carriers that are not confirmed by the Phase 0 research.

Those decisions belong to Phase 2 (technical architecture) and are only made once the business process defined here is approved.

## 2. Scope boundary: where the process starts and ends

The process in scope begins **after** a part is selected in the **existing** HCME Parts Store — the Parts Store itself is not redesigned, only extended downstream — and ends at **Close**:

```
EXISTING PARTS STORE
  ↓
SELECT PART → AVAILABILITY → FULFILMENT OPTIONS → SELECT FULFILMENT
  → ALLOCATE → ORDER → SHIPMENT → DEALER → SERVICE / INSTALL → CLOSE
```

Everything upstream of "Select Part" (browsing, search, catalogue presentation) is out of scope. Everything this document calls "the process" refers only to this ten-stage chain.

## 3. Telemetry / ConSite is not a Phase 1 dependency

Machine telemetry (machine-down alerts, hydraulic-pressure alerts, predictive maintenance, automatic fault detection, automatic parts ordering from telemetry data) is explicitly **excluded** from the core workflow.

ConSite and the confirmed Telematics API (ISO 15143-3 / AEMP 2.0) are documented once, in `HCME_PARTS_FULFILMENT_PROCESS.md` §Future Inputs, as a possible **future upstream trigger** into "Select Part" — i.e., something that could one day suggest a part need — never as a dependency, an automatic allocator, or an automatic orderer. No stage in this specification requires telemetry data to function.

## 4. How UNKNOWN is handled throughout these documents

Where the Phase 0 research marked something UNKNOWN, every document in this set:

- States the UNKNOWN explicitly, rather than silently assuming a value.
- Defines the **system capability** needed to eventually hold that information (a field, a status, a source reference) without naming a specific external system, API, or policy.
- Routes the open question into `HCME_BUSINESS_QUESTIONS.md` rather than resolving it here.

An UNKNOWN never becomes a default value in these documents (e.g., missing inventory data is never treated as zero stock — see `AVAILABILITY_PROCESS.md`).

## 5. Naming and modelling conventions used across all Phase 1 documents

To keep the fourteen documents internally consistent, the following vocabulary is fixed for Phase 1. Phase 2 may rename these for a technical implementation, but Phase 1 uses them uniformly:

**Core entities:** Part, Availability Result, Fulfilment Option, Allocation, Order, Shipment, Dealer, Service Job, Fulfilment Request (the overall trace tying the other entities together).

**Inventory status vocabulary** (fixed, used only as defined in `AVAILABILITY_PROCESS.md`):
`ON_HAND`, `RESERVED`, `ALLOCATED`, `AVAILABLE`, `UNKNOWN`.

**State machines** (defined fully in `PROCESS_STATES.md`):
- Fulfilment Request: `DRAFT → REQUESTED → AVAILABILITY_CHECKED → OPTION_SELECTED → ALLOCATION_PENDING → ALLOCATED → ORDERED → FULFILMENT → SHIPPED → DELIVERED → COMPLETED`, plus `CANCELLED` and `FAILED` as terminal exception states reachable from most non-terminal states.
- Allocation: `PENDING → RESERVED → CONFIRMED → CONSUMED`, plus `RELEASED`, `EXPIRED`, `FAILED`.
- Shipment: `CREATED → DISPATCHED → IN_TRANSIT → DELIVERED`, plus `EXCEPTION` and `CANCELLED`.
- Service Job: `OPEN → PART_RECEIVED → IN_PROGRESS → PART_INSTALLED → COMPLETED`, plus `CANCELLED`.

**Actor list** (fixed, defined fully in `ACTORS_AND_RESPONSIBILITIES.md`):
Customer, Dealer, Dealer Branch, HCME, Warehouse/Depot, Logistics Provider, Technician, Platform/System, External Enterprise Systems.

## 6. Production-readiness stance

Phase 1 treats "production-ready" as a business-process requirement, not a technology requirement: every stage must define its failure/exception path, every state transition must be unambiguous, and every place where two actors could race for the same resource (see Allocation) must have an explicit business rule that a future technical design can implement safely. No performance, scaling, or infrastructure decision is made here — those belong to Phase 2.

## 7. Deliverable structure

```
docs/business-process/
├── HCME_PARTS_FULFILMENT_PROCESS.md      — end-to-end stage-by-stage specification
├── ACTORS_AND_RESPONSIBILITIES.md        — responsibility matrix
├── PROCESS_STATES.md                     — all four state machines
├── BUSINESS_RULES.md                     — cross-cutting rules (data, decisions, invariants)
├── AVAILABILITY_PROCESS.md               — detailed Availability stage
├── FULFILMENT_PROCESS.md                 — detailed Fulfilment Options / Selection stages
├── ALLOCATION_PROCESS.md                 — detailed Allocation stage
├── ORDER_PROCESS.md                      — detailed Order stage
├── SHIPMENT_PROCESS.md                   — detailed Shipment stage
├── DEALER_SERVICE_PROCESS.md             — Dealer, Service/Install, Close stages
├── FAILURE_AND_EXCEPTION_CASES.md        — every failure path in the process
├── HCME_CONFIRMED_VS_UNKNOWN.md          — the authoritative confirmed/unknown ledger
├── HCME_BUSINESS_QUESTIONS.md            — open questions for HCME stakeholders
└── PHASE_1_DECISIONS.md                  — this document

docs/PHASE_1_SUMMARY.md                   — top-level summary and the agreed journey
```
