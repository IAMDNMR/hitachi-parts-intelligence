# Data Ownership Matrix

> [!NOTE]
> **Architecture Decision Reconciliation (Phase 5 Consolidation)**:
> In the consolidated architecture (`docs/NEO4J_ONLY_MIGRATION.md`), all platform-owned entities (Allocation, Order, Service, Inventory Cache, Fulfilment Request, Audit) are stored in **Neo4j AuraDB** as the single database.

Formal ownership for every data domain the fulfilment process touches. Status values: `CONFIRMED` (Phase 0/1 research establishes this), `UNKNOWN` (not established), `TO-BE` (an HCME/business decision is needed), `FUTURE` (deliberately deferred, e.g., telemetry).

| Data | System of record | Platform role | Sync method | Status |
|---|---|---|---|---|
| Parts (catalogue identity) | Existing Parts Store catalogue (frontend static/data source) | Reads part number/description for Part Context; does not own or duplicate the catalogue | N/A — read at hand-off time, not synced/stored | CONFIRMED (existing system), unchanged by this phase |
| Fitment (machine↔part compatibility) | Neo4j (derived from the frozen source workbook via the existing ETL) | Reads for fitment-confidence display; never authoritative over the underlying engineering fact | Existing ETL pipeline, unchanged | CONFIRMED (data exists); authoritative *source* behind the workbook is external and UNKNOWN |
| Machine | Neo4j (existing data foundation) for reference; no live "machine master" system confirmed | Reads machine reference data where available | Existing ETL | CONFIRMED (reference data exists); authoritative live machine master is UNKNOWN |
| Dealer / Dealer Branch | UNKNOWN — official public dealer data used where available | Platform holds required fields in Neo4j (`(:Dealer)`, `(:DealerBranch)`), pending a real source | TO-BE | UNKNOWN / TO-BE |
| Customer | UNKNOWN — no customer identity/master system confirmed | Platform holds `(:Customer)` nodes in Neo4j | TO-BE | UNKNOWN / TO-BE |
| Inventory (live quantity) | UNKNOWN — no confirmed inventory system for any tier | Platform caches the last reported figure as `(:InventoryCache)` in Neo4j; never treats the cache as authoritative | Pull, via `InventoryProvider` adapter | UNKNOWN |
| Price | UNKNOWN — confirmed only that pricing is dealer/account-dependent industry-wide | Platform resolves price at order time via `PricingProvider`; never stores a static price | Pull, at order time | UNKNOWN |
| Allocation | This platform (Neo4j `(:Allocation)` & `(:InventoryLedger)`) | Fully authoritative | N/A — owned outright | CONFIRMED as platform-owned by Phase 1 design |
| Order | This platform (Neo4j `(:Order)`), for the record it creates | Authoritative for its own record | N/A today; TO-BE if an external system is confirmed | UNKNOWN whether an external order system exists; platform-owned meanwhile |
| Shipment | The carrier (once one is confirmed/integrated) | Platform records what the carrier reports in Neo4j `(:Shipment)`; not independently authoritative | Pull/Push via adapter | UNKNOWN (no carrier confirmed) |
| Tracking | The carrier | Same as Shipment | Event/webhook preferred | UNKNOWN |
| Service | This platform (Neo4j `(:ServiceJob)`), unless an external system emerges | Authoritative for Service Job/Service Part | N/A today | UNKNOWN whether an external service system exists; platform-owned meanwhile |
| Technician | UNKNOWN — no HCME technician master confirmed | Platform holds a minimal reference in Neo4j | TO-BE | UNKNOWN / TO-BE |
| Territory | UNKNOWN — no European dealer territory data confirmed | Modelled as relationships in Neo4j | TO-BE | UNKNOWN / TO-BE |
| Telematics (ConSite / Telematics API) | Confirmed to exist externally; explicitly not integrated in this phase | None — not read, not stored, not depended upon | N/A | FUTURE |

## Reading this table

- A row marked **UNKNOWN** does not get a guessed system name anywhere else in Phase 2's documents — every reference to it elsewhere points back to this table.
- A row marked **TO-BE** means the *platform's* conceptual data model already accounts for the field, but the actual source feeding it is a business decision still to be made.
- **CONFIRMED** rows are the only ones this architecture treats as facts about the existing world; everything else is a capability, not an integration.
