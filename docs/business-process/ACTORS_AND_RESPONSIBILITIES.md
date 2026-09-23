# Actors & Responsibilities

## 1. Actor definitions

| Actor | Definition |
|---|---|
| **Customer** | The end user or business that needs the part — may be a machine owner, a fleet operator, or a business buyer. Acts through the Parts Store and, downstream, receives status on their request. |
| **Dealer** | An independent HCME dealer organisation — a first-class business entity, not a contact field. See §3. |
| **Dealer Branch** | A physical location belonging to a Dealer. A Dealer may have one or more Branches, each with its own stock, service and contact capability. |
| **HCME** | Hitachi Construction Machinery Europe — the OEM layer: regional and central parts distribution, pricing authority, and the party ultimately responsible for the platform. |
| **Warehouse / Depot** | A stocking location at regional or central tier (see `AVAILABILITY_PROCESS.md`). May be operated by HCME directly or by an approved logistics partner — UNKNOWN which, per `HCME_CONFIRMED_VS_UNKNOWN.md`. |
| **Logistics Provider** | A carrier or freight partner that transports a shipment from a source to a destination. Specific providers are UNKNOWN (see `HCME_CONFIRMED_VS_UNKNOWN.md`); the process is designed so any approved provider can be integrated. |
| **Technician** | The individual at a Dealer Branch who performs the installation/service work. |
| **Platform / System** | The HCME fulfilment platform being designed across Phase 1–2 — the software actor that orchestrates the process, enforces business rules (e.g., allocation concurrency), and records state. |
| **External Enterprise Systems** | Any system outside the platform that the process must eventually read from or write to (inventory source, pricing source, order system, carrier system, service system). Named systems are UNKNOWN — see `HCME_CONFIRMED_VS_UNKNOWN.md` — Phase 1 defines only the capability to integrate with them. |

## 2. Responsibility matrix

For each stage: **who acts**, **who supplies the data**, **who decides**, **who owns the resulting state**.

| Stage | Who acts | Who provides data | Who decides | Who owns resulting state |
|---|---|---|---|---|
| Select Part | Customer (in the existing Parts Store) | Customer (part, quantity, destination, required-by date); Platform (compatibility/fitment and orderability validation) | Customer selects; Platform validates | Platform (Fulfilment Request: `DRAFT` → `REQUESTED`) |
| Availability | Platform | External Enterprise Systems (inventory source(s) — UNKNOWN which) | Platform (which sources to query); no business decision on availability itself, only reporting | Platform (Fulfilment Request → `AVAILABILITY_CHECKED`) |
| Fulfilment Options | Platform | Platform (computed from Availability Results); External Enterprise Systems (transport cost/time where available — UNKNOWN source) | Platform computes candidate options; no selection yet | Platform (options attached to the request) |
| Fulfilment Selection | Customer or Dealer (business context dependent — see `HCME_BUSINESS_QUESTIONS.md`) | Platform (presents options) | Customer/Dealer selects a valid option | Platform (Fulfilment Request → `OPTION_SELECTED`) |
| Allocation | Platform | External inventory source (current available quantity) | Platform (enforces the concurrency rule — see `ALLOCATION_PROCESS.md`); HCME (any future priority/VOR policy — UNKNOWN today) | Platform (Allocation state; Fulfilment Request → `ALLOCATED` or `FAILED`) |
| Order | Platform, on confirmed Allocation | HCME/pricing source (price — UNKNOWN system, see `ORDER_PROCESS.md`); Customer/Dealer (destination, required-by date, confirmed at Select Part) | Platform creates the order once allocation is confirmed; no further human decision required unless a failure occurs | Platform (Order state; Fulfilment Request → `ORDERED`) — ultimately the External order system of record if/when one is integrated (UNKNOWN) |
| Shipment | Logistics Provider (physical transport); Platform (records state) | Logistics Provider (tracking events, ETA); Warehouse/Depot (dispatch confirmation) | Logistics Provider (transit execution); Platform (state recording) | Platform (Shipment state; Fulfilment Request → `SHIPPED`/`DELIVERED`) |
| Dealer | Dealer Branch | Dealer Branch (receipt confirmation) | Dealer Branch (accepts/rejects receipt — see `FAILURE_AND_EXCEPTION_CASES.md`) | Platform (records receipt; Service Job → `PART_RECEIVED`) |
| Service / Installation | Technician (at Dealer Branch) | Technician (start/completion time, installation confirmation, notes) | Technician/Dealer Branch (confirms installation) | Platform (Service Job state) |
| Close | Platform | Shipment (must be `DELIVERED`); Service Job (must be `COMPLETED`) | Platform (automatic, based on both conditions being met — see `DEALER_SERVICE_PROCESS.md` §Close) | Platform (Fulfilment Request → `COMPLETED`) |

## 3. Dealer as a first-class business entity

The Dealer is modelled as a business entity with its own data, not as a text field on an order. The Dealer's role spans the process:

| Process area | Dealer's role |
|---|---|
| Availability | A potential stock source (dealer-held inventory), if and where dealer stock can be digitally queried — UNKNOWN, see `HCME_CONFIRMED_VS_UNKNOWN.md`. |
| Fulfilment | A potential fulfilment destination and, where relevant, an intermediate fulfilment point. |
| Order | The party the order may be placed through or associated with, depending on the fulfilment option selected. |
| Receiving | Confirms physical receipt of the shipped part. |
| Customer coordination | Communicates status to the customer at the local level. |
| Service | Owns the Service Job once the part is received; assigns a Technician. |
| Installation | Executes or supervises the installation. |
| Completion | Confirms the Service Job is complete, which is one of the two conditions for Close. |

### Dealer data required by this process

| Field | Purpose | Status |
|---|---|---|
| Dealer identifier | Uniquely identify the dealer organisation | UNKNOWN — no confirmed dealer master ID scheme |
| Branch identifier | Uniquely identify a physical branch | UNKNOWN |
| Territory | The geographic area the dealer/branch serves | UNKNOWN for Europe specifically (see `HCME_CONFIRMED_VS_UNKNOWN.md`) |
| Address | Physical location, for shipment destination and routing | UNKNOWN — not sourced in Phase 0 research |
| Contact | Point of contact for coordination | UNKNOWN |
| Stock capability | Whether/what the branch holds in stock, and whether it is digitally queryable | UNKNOWN |
| Fulfilment capability | Whether the branch can act as a fulfilment source or only a destination | UNKNOWN |
| Service capability | Whether/what service and installation work the branch can perform | UNKNOWN |

These fields are **required by the process design** (a Fulfilment Option or Service Job cannot be reasoned about without them) but their actual values, and the system that would supply them, are not confirmed. This is intentional: Phase 1 defines the shape of dealer data the process needs; Phase 2 and HCME stakeholders determine where it comes from (see `HCME_BUSINESS_QUESTIONS.md`).

## 4. RACI summary

| Stage | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Select Part | Customer | Platform | — | Platform |
| Availability | Platform | Platform | External Enterprise Systems | Customer/Dealer |
| Fulfilment Options | Platform | Platform | — | Customer/Dealer |
| Fulfilment Selection | Customer/Dealer | Platform | — | HCME |
| Allocation | Platform | Platform | HCME (future policy) | Customer/Dealer |
| Order | Platform | HCME | Dealer | Customer |
| Shipment | Logistics Provider | Platform | Warehouse/Depot | Customer, Dealer |
| Dealer (receiving) | Dealer Branch | Dealer Branch | — | Platform, Customer |
| Service/Installation | Technician | Dealer Branch | Customer | HCME (record) |
| Close | Platform | Platform | — | Customer, Dealer, HCME |
