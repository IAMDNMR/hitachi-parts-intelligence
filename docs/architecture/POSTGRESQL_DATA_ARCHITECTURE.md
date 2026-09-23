# PostgreSQL Data Architecture

> [!WARNING]
> **STATUS: SUPERSEDED (Phase 5 Consolidation)**:
> This relational data architecture document represents historical Phase 2 design context.
> It has been superseded by the deliberate architecture decision: **CURRENT DATABASE = NEO4J ONLY**.
> All entities below (`InventoryCache`, `Allocation`, `FulfilmentRequest`, `FulfilmentOption`, `Order`, `Shipment`, `ServiceJob`, `AuditRecord`, `IdempotencyRecord`) are implemented and mapped directly to Neo4j graph nodes and relationships in the active FastAPI backend (`backend/app/db/neo4j/schema.py`).
> See [`docs/NEO4J_ONLY_MIGRATION.md`](../NEO4J_ONLY_MIGRATION.md) for the active canonical graph data model.

**Historical Role (Phase 2 Design):** the transactional/operational data store (principle 9) — canonical for every entity that has a lifecycle, a state machine, or must support safe concurrent access.

## Entity documentation

For each entity: purpose, owner (module, from `BACKEND_ARCHITECTURE.md`), required fields (conceptual, not typed columns), relationships, lifecycle, source of truth, and whether it is transactional.

### Inventory (cached view, not owned here)

| | |
|---|---|
| Purpose | A local, time-stamped cache of what an external inventory source last reported for a part at a location — **not** the inventory system itself. |
| Owner | Availability module |
| Required fields | Part, source, location, on-hand/reserved/allocated/available quantity, inventory timestamp, inventory source/system reference, confidence/status (`ON_HAND/RESERVED/ALLOCATED/AVAILABLE/UNKNOWN`). |
| Relationships | References Part; references Source (Dealer, Depot, or Other). |
| Lifecycle | Written on every Availability query; superseded (not deleted) by the next query for audit history. |
| Source of truth | **The external inventory system is authoritative**, not this table — this table is a cache/audit trail. See `DATA_OWNERSHIP.md`. |
| Transactional? | Yes for write consistency (each write is a transaction), but it is explicitly *not* the source of truth for the real-world quantity. |

### Inventory Reservation

| | |
|---|---|
| Purpose | The platform-local record of a soft hold against a source's available quantity, supporting concurrency-safe allocation. |
| Owner | Allocation module |
| Required fields | Part, source, quantity, Fulfilment Request reference, status (`PENDING/RESERVED/CONFIRMED/CONSUMED/RELEASED/EXPIRED/FAILED` — see Phase 1 `PROCESS_STATES.md` §B), created timestamp, expiry timestamp. |
| Relationships | Belongs to one Fulfilment Request; references one source/location; becomes the Allocation once confirmed. |
| Lifecycle | Created `PENDING` → `RESERVED` → `CONFIRMED` (called "Allocation" from here on) → `CONSUMED` on Order creation, or `RELEASED`/`EXPIRED`/`FAILED`. |
| Source of truth | **This platform is authoritative for the reservation itself** — the reservation is a fact about our own commitment, even though the underlying stock figure it is checked against comes from an external, UNKNOWN system. |
| Transactional? | Yes — this is the entity carrying the no-double-allocation guarantee (Phase 1 BR-02); see `ALLOCATION_ARCHITECTURE.md` for the concurrency mechanism. |

### Fulfilment Request

| | |
|---|---|
| Purpose | The parent trace tying Select Part through Close together (Phase 1 `PROCESS_STATES.md` §A). |
| Owner | Shared, coordinated by the orchestration layer (`BACKEND_ARCHITECTURE.md` §1) |
| Required fields | Part, quantity, machine/context, customer reference, destination, required-by date, current state (`DRAFT…COMPLETED/CANCELLED/FAILED`), created/updated timestamps. |
| Relationships | Has many Availability Results, Fulfilment Options; has one selected Fulfilment Option; has one Allocation; has one Order; (via Order) has one Shipment; has one Service Job. |
| Lifecycle | `DRAFT → REQUESTED → AVAILABILITY_CHECKED → OPTION_SELECTED → ALLOCATION_PENDING → ALLOCATED → ORDERED → FULFILMENT → SHIPPED → DELIVERED → COMPLETED`, or `CANCELLED`/`FAILED`. |
| Source of truth | This platform, fully — no external system owns this concept. |
| Transactional? | Yes. |

### Fulfilment Option

| | |
|---|---|
| Purpose | A candidate way to fulfil the request (source + transport), before selection. |
| Owner | Fulfilment module |
| Required fields | Fulfilment Request reference, source Availability Result reference, destination, transport mode, provider, processing time, transit time, ETA, transport cost, total cost, currency, constraints, availability confidence. |
| Relationships | Belongs to one Fulfilment Request; references one Availability Result. |
| Lifecycle | Created during Fulfilment Options; one is marked selected during Fulfilment Selection; the rest remain as a record of what was offered (for audit). |
| Source of truth | This platform computes and owns this entity; the transport cost/time figures within it may originate from an external `RoutingProvider`/`ShippingRateProvider` (UNKNOWN which) and are recorded with provenance. |
| Transactional? | Yes. |

### Allocation

See `ALLOCATION_ARCHITECTURE.md` for the concurrency design. Conceptually the `CONFIRMED` state of an Inventory Reservation (above); modelled as its own entity for clarity of ownership and audit.

| | |
|---|---|
| Purpose | The confirmed commitment of stock to a Fulfilment Request. |
| Owner | Allocation module |
| Required fields | Fulfilment Request reference, source, part, quantity, state, reserved-at timestamp, confirmed-at timestamp, released-at timestamp (if applicable). |
| Relationships | Belongs to one Fulfilment Request; consumed by exactly one Order. |
| Lifecycle | Phase 1 `PROCESS_STATES.md` §B. |
| Source of truth | This platform. |
| Transactional? | Yes — the entity BR-02 protects. |

### Order

| | |
|---|---|
| Purpose | The formal commercial record once allocation is confirmed. |
| Owner | Orders module |
| Required fields | Customer, dealer, allocation reference, fulfilment option reference, price, shipping cost, tax, total, destination, required-by date, status (`CREATED/ACCEPTED/CANCELLED`), order number (see `ORDER_ARCHITECTURE.md` for numbering). |
| Relationships | Belongs to one Fulfilment Request; has many Order Lines (in the general case; Phase 1 scope is single-part per request, but the model allows multiple lines without redesign); has one Shipment. |
| Lifecycle | `CREATED → ACCEPTED → (fulfilled)` or `CANCELLED`. |
| Source of truth | **This platform is authoritative for the order record it creates.** Whether this becomes a copy of a record whose real system of truth is an external order-management system is UNKNOWN (see `DATA_OWNERSHIP.md`) — if/when one is confirmed, this table becomes a local, synced projection rather than sole authority; that reconciliation is a Phase 3+ decision. |
| Transactional? | Yes. |

### Order Line

| | |
|---|---|
| Purpose | One priced line within an Order (part, quantity, unit price) — modelled even though Phase 1 scope is one part per Fulfilment Request, so the schema does not need to change if multi-line orders are needed later. |
| Owner | Orders module |
| Required fields | Order reference, part, quantity, unit price, line total. |
| Relationships | Belongs to one Order. |
| Lifecycle | Created with the Order; immutable once the Order is `ACCEPTED` (a change requires a new Order or an explicit, audited modification — see `ORDER_ARCHITECTURE.md`). |
| Source of truth | This platform. |
| Transactional? | Yes. |

### Shipment

| | |
|---|---|
| Purpose | Tracks physical movement of the ordered part. |
| Owner | Shipments module |
| Required fields | Order reference, carrier/provider, service level, tracking number, origin, destination, ETA, status (`CREATED/DISPATCHED/IN_TRANSIT/DELIVERED/EXCEPTION/CANCELLED`). |
| Relationships | Belongs to one Order; has many Shipment Events. |
| Lifecycle | Phase 1 `PROCESS_STATES.md` §C. |
| Source of truth | **The carrier is authoritative for the physical shipment; this table is our record of what the carrier has reported**, not an independent truth. See `DATA_OWNERSHIP.md`. |
| Transactional? | Yes for our own record; eventually-consistent with the external carrier by nature. |

### Shipment Event

| | |
|---|---|
| Purpose | The timestamped history of status/tracking updates. |
| Owner | Shipments module |
| Required fields | Shipment reference, event type, event timestamp, event source (carrier webhook, polling, manual entry), raw payload reference (for audit). |
| Relationships | Belongs to one Shipment. |
| Lifecycle | Append-only. |
| Source of truth | The carrier, relayed. |
| Transactional? | Yes (append is transactional); the content is externally sourced. |

### Service Job

| | |
|---|---|
| Purpose | Tracks part installation at the dealer. |
| Owner | Service module |
| Required fields | Machine, dealer (branch), order reference, part, technician, status (`OPEN/PART_RECEIVED/IN_PROGRESS/PART_INSTALLED/COMPLETED/CANCELLED`), start time, completion time, installation confirmation, notes/evidence reference. |
| Relationships | Belongs to one Order (via the Fulfilment Request); references one Dealer Branch, one Technician. |
| Lifecycle | Phase 1 `PROCESS_STATES.md` §D. |
| Source of truth | This platform — unless/until a confirmed external service-job system is identified (UNKNOWN today, see `HCME_CONFIRMED_VS_UNKNOWN.md`). |
| Transactional? | Yes. |

### Service Part

| | |
|---|---|
| Purpose | Records which specific part(s) were installed against a Service Job — supports the general case of more than one part per job even though Phase 1's traced scope is one part per Fulfilment Request. |
| Owner | Service module |
| Required fields | Service Job reference, part, quantity installed. |
| Relationships | Belongs to one Service Job. |
| Lifecycle | Created when installation is confirmed. |
| Source of truth | This platform. |
| Transactional? | Yes. |

### Users / Access (where appropriate)

| | |
|---|---|
| Purpose | Local record of *who* is acting (customer, dealer staff, HCME staff) for authorization and audit purposes. |
| Owner | Authentication/Authorization module |
| Required fields | Identity reference (from whatever provider is eventually chosen — TO-BE), role/type, dealer/customer association where applicable. |
| Relationships | Referenced by every audit record and by actor fields across the model (Order's customer, Service Job's technician, etc.). |
| Lifecycle | TO-BE — depends entirely on the authentication approach chosen (see `SECURITY_ARCHITECTURE.md`, `ADR-009`). |
| Source of truth | **UNKNOWN whether an external identity provider is authoritative** (likely, once one is chosen) **or this table is** — this platform would hold, at most, a local reference/role mapping, not the identity itself. |
| Transactional? | Yes, for the local mapping; identity itself is external once a provider is chosen. |

### Audit Record

| | |
|---|---|
| Purpose | Full traceability for every important business action (see `AUDIT_ARCHITECTURE.md`). |
| Owner | Audit module |
| Required fields | Actor, action, timestamp, entity type, entity ID, previous state, new state, source, correlation/request ID. |
| Relationships | References whichever entity the action concerned (polymorphic by entity type + ID). |
| Lifecycle | Append-only, retained per an eventual retention policy (TO-BE — see Phase 1 `HCME_BUSINESS_QUESTIONS.md` Q26). |
| Source of truth | This platform. |
| Transactional? | Yes — written in the same transaction as the state change it records, so audit can never silently fall out of sync with the entity it describes. |

## Summary ownership table

| Entity | PostgreSQL owns | External system is authoritative for |
|---|---|---|
| Inventory (cache) | The cached figure + provenance | The real quantity |
| Inventory Reservation / Allocation | Fully | — |
| Fulfilment Request | Fully | — |
| Fulfilment Option | Fully (figures may originate externally, recorded with provenance) | Transport cost/time inputs, once a provider is confirmed |
| Order | The platform's own order record | Possibly an external order system, if/when confirmed (UNKNOWN today) |
| Order Line | Fully | — |
| Shipment / Shipment Event | The platform's record of carrier-reported state | The carrier |
| Service Job / Service Part | Fully (unless an external service system is later confirmed) | — |
| Users/Access | A local role/reference mapping | The identity provider, once chosen |
| Audit Record | Fully | — |
