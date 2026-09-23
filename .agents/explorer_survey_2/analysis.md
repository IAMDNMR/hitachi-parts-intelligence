# External European Integration Landscape & Documentation Investigation
## Comprehensive Analysis Report for Phase 9 Real Integrations

**Date**: 2026-09-23  
**Investigator**: Explorer 2 (External European Integration Landscape & Documentation Investigator)  
**Target Repository**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service`  
**Milestone Scope**: Phase 9 Real Integrations (Requirements R1, R2, R3, R4)  
**Protected Database**: Neo4j AuraDB (`neo4j+ssc://fb580139.databases.neo4j.io`)  

---

## 1. Executive Summary

This investigation audits the external European integration landscape, partner interfaces, OEM portals, telematics standards, carrier logistics, and routing services relevant to the HCME Europe OEM Parts & Services Platform.

The core objective of Phase 9 is to replace prototype `NOT_CONNECTED` placeholders and mock providers with verified, concrete European integrations wherever accessible, while strictly preserving the Neo4j AuraDB single-source-of-truth runtime graph core, zero-regression test baselines, and Europe-only geographic integrity.

### Crucial Findings:
1. **The Strict Realism Rule**: Per R1 and project governance, **no integration may be marked `CONNECTED` without an actual verified live request execution or approved sandbox response.** In non-authenticated, standalone, or credential-less environments, all external systems that require commercial agreements, dealer credentials, or vendor API keys must remain strictly classified under their authoritative non-connected tiers (`ACCESS AVAILABLE — READY TO CONNECT`, `AUTHENTICATED / DEALER ACCESS REQUIRED`, `PARTNER / COMMERCIAL ACCESS REQUIRED`, `API NOT PUBLICLY DOCUMENTED`, `NOT FOUND`, `NOT APPLICABLE`, or `SYNTHETIC FALLBACK`).
2. **HCME Commercial & ERP Boundary**: Hitachi Construction Machinery Europe (HCME) does **not** expose public, self-service REST APIs for OEM spare parts master catalog queries, live depot/dealer inventory levels, parts wholesale/retail pricing, or purchase order creation. All commercial ordering and pricing operations are confined behind:
   - **Global e-Service (GES)** (`globaleservice.com`) — account-gated dealer intranet.
   - **HCME Dealer Portal** (`hcmedealerportal.com`) — SSO-authenticated dealer extranet.
   - **ConSite ISF (Intelligent Service Parts Finder)** — parts list generator behind dealer/customer login.
   - **Neovia Logistics TMS** — private enterprise logistics management operating the European Parts Centre (EPC) in Oosterhout, Netherlands (`SRC-050`).
3. **Publicly Accessible & Real European Services**:
   - **HCME Official Public Dealer Locator JSON Feed**: Publicly served at `https://www.hitachicm.com/content/hitachicm/eu/en/dealer-network/jcr:content/root/container/dealerlocator.json` (`SRC-049`). It feeds 182 verified European dealer branches across 30 countries currently stored in Neo4j AuraDB.
   - **Open Source Routing Machine (OSRM) European Demo API**: `http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}` provides real road routing, driving distance in meters, and transit durations across European road networks without authentication.
   - **DHL Express Europe API**: Developer portal (`developer.dhl.com`) provides sandbox environments and documented REST endpoints (`https://api-eu.dhl.com/track/shipments`) for European tracking and dispatch, requiring API key provisioning.
   - **PostNL API**: Operates the primary parcel/logistics infrastructure in the Netherlands (home to HCME EPC Oosterhout); sandbox available at `developer.postnl.nl` with full shipping, labelling, and tracking capabilities.
   - **HCME Telematics API**: Real, documented standard API (ISO 15143-3 / AEMP 2.0) at `https://api.hitachiconstruction.com/v1/telematics` (`SRC-025`), but strictly restricted to machine telemetry (GPS, engine hours, fuel burn, diagnostic DTC codes) and gated by client credentials.

---

## 2. Strict Architecture & Europe-Only Boundary Invariants (R3)

All Phase 9 integrations and documentation must adhere to the immutable architecture rules established across Phases 0 through 8:

1. **Sole Runtime Database**:
   - **Neo4j AuraDB** is the **sole single source of runtime truth** for all business entities (`Part`, `Machine`, `DealerBranch`, `Depot`, `FulfilmentRequest`, `Allocation`, `InventoryLedger`, `Order`, `Shipment`, `ShipmentEvent`, `ServiceJob`, `ServiceEvent`).
   - **Zero PostgreSQL, SQLite, or in-memory runtime databases** are allowed.
2. **Europe-Only Geographic Scope**:
   - Strictly 0 US, Japanese, or non-European operational entities.
   - Dealer network is strictly filtered to 44 European ISO-3166 countries (currently 182 branches across 30 countries).
   - Transcontinental and non-EU territories (`RU`, `TR`) remain excluded.
   - Physical distribution hub is anchored at the Hitachi European Parts Centre in Oosterhout, Netherlands (`SRC-050`).
3. **Explicit Synthetic vs. Canonical Separation**:
   - Every synthetic, demo, or fallback node must be stamped with:
     - `synthetic: true`
     - `data_source: 'SYNTHETIC_DEMO'` (or specific demo workflow tag like `SYNTHETIC_DEMO_KPI_WORKFLOW`).
   - Canonical real records (`PT-001` through `PT-060`, `ZX210-7`, `ZW310-7`, `DLR-001` through `DLR-182`) must have `synthetic: false` or unset.
   - Live AuraDB graph integrity sweeps enforce: 0 orphan events, 0 duplicate records, 0 non-EU records, and 0 canonical nodes marked synthetic.

---

## 3. Investigation of the 9 Operational Domains

Below is the exhaustive investigation of the 9 operational domains specified in R1 and R2.

### Domain 1: Parts/Product Master
- **Role in Journey**: Authoritative identification of spare parts, SKU numbers, component descriptions, weights, hazardous material flags, machine model compatibility (`HAS_PART_FITMENT`), supersession lineages (`SUPERSEDES`), and cross-catalog equivalence (Genuine vs. Selected Parts vs. Reman).
- **External Landscape & Systems**:
  - *Global e-Service (GES)*: Factory parts books and global engineering bulletins. Access-gated.
  - *ConSite ISF (Intelligent Service Parts Finder)*: Interactive web tool for searching model code/part number and generating parts pick-lists. Login-gated (`SRC-023`).
  - *Hitachi Genuine & SELECTED PARTS Literature*: Marketing PDFs and catalog brochures for GET (Ground Engaging Tools) and Undercarriage (`SRC-028`, `SRC-030`).
  - *EU Regulatory Specifications*: EU Battery Regulation 2023/1542 compliance tracking for heavy machinery batteries (`SRC-039`, CELEX 32023R1542).
- **Public API Availability**:
  - No public self-service REST API exists from Hitachi for OEM parts master data.
- **Current Neo4j AuraDB State**:
  - 60 `Part` nodes (37 `ORDERABLE_OEM_PART`, 23 `PRODUCT_LINE_PART_FAMILY`).
  - 77 `Machine` nodes, 1,041 `HAS_PART_FITMENT` relationships.
  - 10 concept parts carrying `INTERNALLY GENERATED DATA` (`SRC-048`).
  - Graph Intelligence engine (`backend/app/modules/intelligence/`) provides deterministic cross-catalog compatibility matching and EU compliance validation.
- **Authoritative Classification**:
  - Hitachi Global e-Service / ConSite ISF: `AUTHENTICATED / DEALER ACCESS REQUIRED`
  - Public Part Master API: `API NOT PUBLICLY DOCUMENTED`
  - Internal AuraDB Graph Core: `CONNECTED` (Platform canonical store)
  - Concept/Demo parts: `SYNTHETIC FALLBACK`

### Domain 2: Inventory
- **Role in Journey**: Real-time availability calculation, checking on-hand, reserved, and available stock at central depots, regional hubs, and dealer branches prior to order placement.
- **External Landscape & Systems**:
  - *Hitachi European Parts Centre (EPC)*, Oosterhout, Netherlands (`SRC-050`): Central warehouse spanning 28,000 m², 110,000 bin locations, stocking ~80,000 SKUs. Managed by Neovia Logistics.
  - *Neovia WMS/TMS*: Internal enterprise system managing bin locations and stock counts.
  - *Dealer DMS*: Third-party dealer management systems (e.g. Flyntlok claim of real-time inventory synchronization).
- **Public API Availability**:
  - No public or partner API is reachable without dedicated commercial credentials.
- **Current Codebase Implementation**:
  - Contract: `backend/app/integrations/contracts/inventory.py` (`InventoryProvider`, `SourceAvailabilityQuery`, `SourceInventoryItem`).
  - Mock: `backend/app/integrations/mocks/inventory_mock.py` (`TestInventoryProvider`).
  - Runtime behavior: In `production`, returns `UNKNOWN` with `UNCONFIRMED_EXTERNAL_API` provenance. In `development`, provides deterministic availability scenarios.
  - Graph entities: `InventoryCache` (platform cache with TTL), `InventoryLedger` (authoritative allocation ledger), `InventorySnapshot` (synthetic demo records).
- **Authoritative Classification**:
  - HCME EPC / Neovia WMS / Dealer DMS: `PARTNER / COMMERCIAL ACCESS REQUIRED` / `AUTHENTICATED / DEALER ACCESS REQUIRED`
  - Public Inventory API: `API NOT PUBLICLY DOCUMENTED` / `NOT FOUND`
  - Runtime Adapter Posture: `SYNTHETIC FALLBACK`

### Domain 3: Pricing
- **Role in Journey**: Determination of authoritative line-item part pricing, dealer wholesale cost, net customer price, currency (EUR/GBP), and quantity discounts.
- **External Landscape & Systems**:
  - *HCME Commercial Sales Operations*: Negotiated wholesale price agreements between HCME and national dealers.
  - *Flyntlok Claim*: Third-party DMS claims live pricing file sync; requires dealer credentials.
  - *HCME Webshop* (`hcmewebshop.com`): Sells branded merchandise and scale models only, NOT machine spare parts (`SRC-045`).
- **Public API Availability**:
  - Zero public pricing APIs, price lists, or automated feeds exist.
- **Current Codebase Implementation**:
  - Contract: `backend/app/integrations/contracts/pricing.py` (`PricingProvider`, `PricingQuery`, `PriceQuote`).
  - Mock: `backend/app/integrations/mocks/pricing_mock.py` (`TestPricingProvider`).
  - Runtime behavior: Always honestly returns `status="NOT_AVAILABLE"`, `unit_price=None`, `is_confirmed=False`.
  - In AuraDB: Orders record `unitPrice: null`, `pricingStatus: 'NOT_AVAILABLE'`.
- **Authoritative Classification**:
  - HCME Commercial Pricing / Dealer DMS: `AUTHENTICATED / DEALER ACCESS REQUIRED` / `PARTNER / COMMERCIAL ACCESS REQUIRED`
  - Public Pricing API: `API NOT PUBLICLY DOCUMENTED` / `NOT FOUND`
  - Runtime Adapter Posture: `SYNTHETIC FALLBACK` (Explicit `NOT_AVAILABLE`, strictly no fabricated numbers)

### Domain 4: Dealer
- **Role in Journey**: Master directory of certified dealerships, branch facilities, geographical coverage, service capabilities, technician assignments, and order receiving locations.
- **External Landscape & Systems**:
  - *HCME Dealer Locator JSON Feed* (`SRC-049`): Public HTTP endpoint at `https://www.hitachicm.com/content/hitachicm/eu/en/dealer-network/jcr:content/root/container/dealerlocator.json`.
  - *HCME Dealer Portal* (`hcmedealerportal.com`): Extranet for authorized European dealers (login-gated).
- **Public API Availability**:
  - The public JSON feed is fully operational, publicly queryable without authentication, and contains worldwide branch locations including 182 verified European branches.
- **Current Codebase Implementation**:
  - In AuraDB: 182 `DealerBranch` nodes across 30 European countries (`DLR-001` through `DLR-182`), populated with coordinates, phone, email, supported machine categories, and provenance `SRC-049`.
  - Contract status: Conceptually defined in `docs/architecture/INTEGRATION_ARCHITECTURE.md` as `DealerProvider`. Needs formal contract file `backend/app/integrations/contracts/dealer.py` and adapter.
- **Authoritative Classification**:
  - HCME Public Dealer Locator JSON Feed: `ACCESS AVAILABLE — READY TO CONNECT`
  - HCME Dealer Portal (Extranet / DMS): `AUTHENTICATED / DEALER ACCESS REQUIRED`
  - Local AuraDB European Dealer Graph: `CONNECTED` (182 canonical nodes in AuraDB, `synthetic: false`)

### Domain 5: Order/ERP
- **Role in Journey**: Electronic purchase order placement, commercial order acknowledgement, ERP reference generation, backorder management, and status updates.
- **External Landscape & Systems**:
  - *HCME Central ERP (SAP)*: HCME's internal ERP system of record.
  - *Global e-Service (GES) / HCME Dealer Portal*: Web interface used by dealers to enter purchase orders.
  - *Flyntlok Two-Way PO Submission*: Third-party DMS claiming bidirectional PO creation via dealer credentials.
- **Public API Availability**:
  - No public REST API or EDI endpoint is exposed for order placement.
- **Current Codebase Implementation**:
  - Contract: `backend/app/integrations/contracts/order.py` (`OrderProvider`, `OrderSubmission`, `OrderSubmissionResult`).
  - Mock: `backend/app/integrations/mocks/order_mock.py` (`TestOrderProvider`).
  - Service: `backend/app/modules/order/service.py` manages lifecycle `CREATED -> ACCEPTED -> CANCELLED` in Neo4j AuraDB.
  - Runtime behavior: `submit_order` returns `accepted=False`, `status="NOT_CONNECTED"`, `message="No real HCME order system is connected"`.
- **Authoritative Classification**:
  - HCME Core ERP (SAP) / Extranet: `AUTHENTICATED / DEALER ACCESS REQUIRED` / `PARTNER / COMMERCIAL ACCESS REQUIRED`
  - Public Order Submission API: `API NOT PUBLICLY DOCUMENTED` / `NOT FOUND`
  - Runtime Adapter Posture: `SYNTHETIC FALLBACK` (Platform owns internal Order record in AuraDB; marks external submission `NOT_CONNECTED`)

### Domain 6: Allocation
- **Role in Journey**: Real-time locking and allocation of physical depot/dealer inventory against fulfilment requests, ensuring zero double-booking under concurrent load.
- **External Landscape & Systems**:
  - *Platform Internal Ledger*: The HCME platform is designed and confirmed as the authoritative system of record for real-time allocation locks.
- **Public API Availability**:
  - Not applicable — internal domain logic.
- **Current Codebase Implementation**:
  - Service: `backend/app/modules/allocation/service.py` & `ledger.py`.
  - Verified under Phase 6 concurrency stress testing: 15/15 tests passing across 3 runs with 0 deadlocks.
  - AuraDB nodes: `Allocation`, `InventoryLedger`.
- **Authoritative Classification**:
  - Internal Platform Engine: `NOT APPLICABLE` for external provider; internal graph core is `CONNECTED` in Neo4j AuraDB.
  - External ERP Allocation Synchronization: `PARTNER / COMMERCIAL ACCESS REQUIRED` (future sync with Neovia/SAP).

### Domain 7: Shipment/TMS
- **Role in Journey**: Carrier selection, physical dispatch scheduling from EPC Oosterhout or regional depots, shipping rate calculation, routing optimization, and waybill generation.
- **External Landscape & Systems**:
  - *Neovia Logistics TMS*: On-site physical logistics operator at EPC Oosterhout (`SRC-050`). Commercial TMS API / EDI.
  - *DHL Express Europe*: Primary courier partner for rapid European distribution. Developer portal at `developer.dhl.com`.
  - *PostNL*: Leading postal/parcel carrier in the Netherlands; sandbox at `developer.postnl.nl`.
  - *DPD Europe / DB Schenker*: Road freight and pallet distribution across continental Europe.
  - *European Routing Services*:
    - Open Source Routing Machine (OSRM): Public demo router at `http://router.project-osrm.org/` computes real road distance and travel time across Europe.
    - OpenRouteService (`openrouteservice.org`): Heidelberg University European routing API.
- **Current Codebase Implementation**:
  - Contracts:
    - `ShipmentProvider` (`backend/app/integrations/contracts/shipment.py`)
    - `RoutingProvider` (`backend/app/integrations/contracts/routing.py`)
    - `ShippingRateProvider` (`backend/app/integrations/contracts/shipping_rate.py`)
  - Adapters: `NeoviaLogisticsAdapter`, `DHLExpressAdapter` (`backend/app/integrations/adapters/`).
  - Mocks: `TestShipmentProvider`, `TestRoutingProvider`, `TestShippingRateProvider`.
  - Domain service: `backend/app/modules/shipment/service.py` enforces `CREATED -> DISPATCHED -> IN_TRANSIT -> DELIVERED`.
- **Authoritative Classification**:
  - Neovia Logistics TMS: `PARTNER / COMMERCIAL ACCESS REQUIRED`
  - DHL Express / PostNL / DPD / DB Schenker Dispatch API: `PARTNER / COMMERCIAL ACCESS REQUIRED` (or `ACCESS AVAILABLE — READY TO CONNECT` in sandbox with developer keys)
  - OSRM European Routing: `ACCESS AVAILABLE — READY TO CONNECT`
  - Current Runtime Dispatch: `SYNTHETIC FALLBACK` (explicit `NOT_CONNECTED`, `synthetic: true`, `data_source: 'SYNTHETIC_DEMO'`)

### Domain 8: Carrier Tracking
- **Role in Journey**: Continuous telemetry on shipment progress, milestone capture (`DISPATCHED`, `IN_TRANSIT`, `EXCEPTION`, `DELIVERED`), transit ETA recalculation, and webhook ingestion.
- **External Landscape & Systems**:
  - *DHL Unified Tracking API*: Documented at `https://developer.dhl.com/api-reference/shipment-tracking`. Endpoint: `https://api-eu.dhl.com/track/shipments`. Sandbox available. Requires `DHL-API-Key`.
  - *PostNL Shipping Status API*: Documented at `https://developer.postnl.nl/apis/shipping-status-api/`. Endpoint: `https://api-sandbox.postnl.nl/shipment/v2/status`.
  - *DB Schenker Tracking*: B2B tracking portal (`tracking.dbschenker.com`).
- **Current Codebase Implementation**:
  - Contract: `backend/app/integrations/contracts/tracking.py` (`TrackingProvider`, `TrackingQuery`, `TrackingResult`).
  - Adapters: `DHLExpressAdapter`, `NeoviaLogisticsAdapter` (implemented in Phase 7, configured for key check).
  - Mock: `TestTrackingProvider` (`backend/app/integrations/mocks/tracking_mock.py`).
  - In AuraDB: `(:Shipment)-[:HAS_EVENT]->(:ShipmentEvent)`.
- **Authoritative Classification**:
  - DHL Express Tracking API: `ACCESS AVAILABLE — READY TO CONNECT` (Sandbox accessible with developer credentials) / `PARTNER / COMMERCIAL ACCESS REQUIRED` (Live production)
  - PostNL Tracking API: `ACCESS AVAILABLE — READY TO CONNECT` (Sandbox accessible) / `PARTNER / COMMERCIAL ACCESS REQUIRED`
  - Current Codebase State: `SYNTHETIC FALLBACK` (explicit `NOT_CONNECTED`, mock event stream tagged `synthetic: true`)

### Domain 9: Service
- **Role in Journey**: Dealership workshop work orders, field technician dispatch, part receipt confirmation, part installation, warranty recordation, and job completion.
- **External Landscape & Systems**:
  - *HCME Telematics API*: ISO 15143-3 / AEMP 2.0 compliant (`SRC-025`). Machine telemetry (GPS, engine hours, fuel, fault codes). Gated by client credentials.
  - *ConSite Pocket & ISF*: Proprietary mobile app and web maintenance notifications.
  - *Dealer Service Execution*: Conducted locally by certified technicians at dealer branches (`DLR-001` to `DLR-182`).
- **Current Codebase Implementation**:
  - Service: `backend/app/modules/service/service.py` manages lifecycle `OPEN -> PART_RECEIVED -> IN_PROGRESS -> PART_INSTALLED -> COMPLETED` in Neo4j AuraDB (`ServiceJob`, `ServiceEvent`).
  - Verified under Phase 8: Links `Order`, `Shipment`, `DealerBranch`, `Part`, and `Machine`.
  - Contract status: Conceptually defined in `INTEGRATION_ARCHITECTURE.md` as `ServiceProvider`. Needs formal contract file `backend/app/integrations/contracts/service.py` and adapter.
- **Authoritative Classification**:
  - HCME Telematics API (ISO 15143-3): `AUTHENTICATED / DEALER ACCESS REQUIRED` (Real documented API, client credentials required)
  - Dealer DMS Service Job Dispatch: `AUTHENTICATED / DEALER ACCESS REQUIRED`
  - Platform Service Job Engine: Platform-owned internal system in Neo4j AuraDB (`synthetic: false` for canonical workflow)
  - External Service Provider Adapter: `SYNTHETIC FALLBACK` / `NOT_CONNECTED`

---

## 4. Real European Logistics, Carrier & Routing Services Assessment

### 4.1 DHL Express & Parcel Europe
- **Provider & Owner**: Deutsche Post DHL Group.
- **Developer Portal**: `https://developer.dhl.com/`
- **Primary APIs**:
  - *DHL Express Tracking API (MyDHL)*: `https://api-eu.dhl.com/track/shipments`
  - *DHL Express Shipment Dispatch API*: `https://api-eu.dhl.com/express/v1/shipments`
- **Authentication**: `DHL-API-Key` (header) or OAuth2 Bearer token generated from Client ID and Secret.
- **Sandbox Environment**:
  - DHL Developer Portal provides instant self-service app registration and sandbox API keys.
  - Sandbox allows sending test tracking queries (e.g. `7777777770`, `1234567890`) returning mock European tracking milestones without live transit side-effects.
- **European Coverage**: Unmatched coverage across all 30 European countries where HCME dealers operate.

### 4.2 PostNL (Netherlands Central Hub)
- **Provider & Owner**: PostNL N.V. (The Hague, Netherlands).
- **Developer Portal**: `https://developer.postnl.nl/`
- **Relevance to HCME**: HCME's central European Parts Centre is located in Oosterhout, Netherlands (`SRC-050`). PostNL is the native national logistics backbone for Benelux and rapid trans-border dispatch into Germany, France, and Belgium.
- **Primary APIs**:
  - *Shipping Status API*: `https://api-sandbox.postnl.nl/shipment/v2/status`
  - *Shipment Labelling & Confirming API*: `https://api-sandbox.postnl.nl/shipment/v2/confirm`
- **Authentication**: API Key in request header (`apikey: {key}`).
- **Sandbox Environment**: Available on developer portal with pre-defined test tracking codes.

### 4.3 DPD Europe & DB Schenker
- **DPDgroup**: Road courier network spanning 28 European countries. Suitable for standard 24–48 hour parcel delivery between Oosterhout and Western European dealer branches. Commercial API requires merchant account.
- **DB Schenker**: Deutsche Bahn AG logistics arm. Crucial for heavy excavator buckets, complete undercarriage tracks, hydraulic cylinders, and palletized engines requiring heavy freight haulage rather than parcel delivery. B2B portal / EDI interface.

### 4.4 European Routing: OSRM (Open Source Routing Machine)
- **Service Name**: Open Source Routing Machine (OSRM).
- **Public European Endpoint**: `http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false`
- **Capabilities**:
  - Real road network calculations across all of geographic Europe based on OpenStreetMap.
  - Returns actual driving distance in meters and travel duration in seconds.
  - Enables calculating authentic road transit times from Oosterhout EPC (`4.86, 51.64`) to any of the 182 dealer branches (e.g. Munich, Hamburg, Paris, Milan, Lyon).
- **Access & Authentication**: Completely open; no API key required for low-volume non-commercial queries. Rate-limited to reasonable developer testing.

---

## 5. Authoritative Master Integration Inventory Matrix

This table synthesizes the complete status across all operational domains and external services under the strict 8-tier classification required by R1:

| # | Operational Domain | External System / Service | Owner / Operator | Interface Type | Endpoint / Portal URL | Authentication Requirement | Authoritative Classification | Current Codebase State | AuraDB Provenance & Boundary |
|---|---|---|---|---|---|---|---|---|---|
| **1** | Parts/Product Master | Global e-Service (GES) | HCME / HCM Japan | Web Extranet | `globaleservice.com` | Account Login / SSO | **AUTHENTICATED / DEALER ACCESS REQUIRED** | Master catalog read from AuraDB | Canonical nodes: `synthetic: false`, `data_class: 'CORE'` |
| **2** | Parts/Product Master | ConSite ISF (Parts Finder) | HCME | Web App | `hitachicm.com/.../online-parts-finder/` | Customer/Dealer Auth | **AUTHENTICATED / DEALER ACCESS REQUIRED** | Reference research only (`SRC-023`) | `SRC-023`, `confidence: HIGH` |
| **3** | Parts/Product Master | EU Battery Regulation 2023/1542 | European Union | Regulatory Standard | CELEX 32023R1542 | Public Law | **CONNECTED** (Graph Rule) | Enforced in Neo4j intelligence module | `SRC-039`, `COMP-EU-BATT-2023` |
| **4** | Inventory | HCME EPC Oosterhout Warehouse | Neovia Logistics | WMS / EDI | `neovialogistics.com` | Partner Commercial Contract | **PARTNER / COMMERCIAL ACCESS REQUIRED** | `TestInventoryProvider` | `SRC-050` facility facts; `InventorySnapshot` demo tagged |
| **5** | Inventory | Dealer Branch Stock | European Dealers | DMS / B2B | Proprietary per dealer | Dealer DMS Auth | **AUTHENTICATED / DEALER ACCESS REQUIRED** | `TestInventoryProvider` returns `UNKNOWN` in prod | `InventoryCache`: `provenance: 'UNCONFIRMED_EXTERNAL_API'` |
| **6** | Pricing | HCME Commercial Parts Pricing | HCME Commercial Ops | ERP / DMS | Internal SAP | Dealer Contractual Terms | **AUTHENTICATED / DEALER ACCESS REQUIRED** | `TestPricingProvider` | Orders record `pricingStatus: 'NOT_AVAILABLE'` |
| **7** | Pricing | HCME Webshop | The Merchandise Co. | Shopify Store | `hcmewebshop.com` | Public Storefront | **NOT APPLICABLE** (Merchandise only) | Not integrated | Corrected research finding (`SRC-045`) |
| **8** | Dealer | HCME Public Dealer Locator Feed | HCME | JSON REST Feed | `hitachicm.com/.../dealerlocator.json` | Public / None | **ACCESS AVAILABLE — READY TO CONNECT** | 182 `DealerBranch` nodes in AuraDB | `SRC-049`, 30 EU countries, `synthetic: false` |
| **9** | Dealer | HCME Dealer Portal | HCME | SSO Extranet | `hcmedealerportal.com` | Dealer Login | **AUTHENTICATED / DEALER ACCESS REQUIRED** | Reference research only (`SRC-046`) | Documented login wall |
| **10** | Order/ERP | HCME Central ERP | HCME / SAP | B2B EDI / RFC | Internal Corporate Network | Corporate VPN / Partner Auth | **PARTNER / COMMERCIAL ACCESS REQUIRED** | `TestOrderProvider` (`NOT_CONNECTED`) | Orders: `provenance: 'INTERNAL_TEST_WORKFLOW'` |
| **11** | Order/ERP | Dealer DMS PO Gateway | Dealer DMS (Flyntlok, etc.) | REST / SOAP | Dealer DMS Gateway | Dealer API Credentials | **AUTHENTICATED / DEALER ACCESS REQUIRED** | `TestOrderProvider` (`NOT_CONNECTED`) | Order node status in AuraDB |
| **12** | Allocation | Platform Allocation Ledger | Platform Core | Cypher / ACID | AuraDB Connection | Bolt SSC Protocol | **CONNECTED** (Internal System of Record) | `AllocationLedger` fully operational | Authoritative `Allocation` & `InventoryLedger` nodes |
| **13** | Shipment/TMS | Neovia Logistics TMS | Neovia Logistics | TMS API / EDI | `api.neovialogistics.com` | Commercial B2B Credentials | **PARTNER / COMMERCIAL ACCESS REQUIRED** | `NeoviaLogisticsAdapter` | Carrier dispatch record, `synthetic: true` in test |
| **14** | Shipment/TMS | DHL Express Europe Dispatch | DHL Express | REST API | `api-eu.dhl.com/express/v1` | `DHL-API-Key` / Client Secret | **PARTNER / COMMERCIAL ACCESS REQUIRED** | `DHLExpressAdapter` | Waybill metadata in AuraDB |
| **15** | Shipment/TMS | OSRM European Road Router | OpenStreetMap / Project OSRM | Public REST API | `router.project-osrm.org` | Public / None | **ACCESS AVAILABLE — READY TO CONNECT** | `TestRoutingProvider` fallback | Real transit duration & distances |
| **16** | Carrier Tracking | DHL Unified Tracking API | DHL Express | REST API | `api-eu.dhl.com/track/shipments` | `DHL-API-Key` (Sandbox available) | **ACCESS AVAILABLE — READY TO CONNECT** (Sandbox) | `DHLExpressAdapter` (`NOT_CONNECTED`) | `(:Shipment)-[:HAS_EVENT]->(:ShipmentEvent)` |
| **17** | Carrier Tracking | PostNL Shipping Status API | PostNL | REST API | `api-sandbox.postnl.nl` | PostNL API Key (Sandbox available) | **ACCESS AVAILABLE — READY TO CONNECT** (Sandbox) | Contract defined | `ShipmentEvent` records |
| **18** | Service | HCME Telematics API | HCM Global | REST (ISO 15143-3) | `api.hitachiconstruction.com` | OAuth2 Client Credentials | **AUTHENTICATED / DEALER ACCESS REQUIRED** | Excluded from parts scope (`SRC-025`) | Telemetry hours/GPS only |
| **19** | Service | Dealer Field Service & Workshop | European Dealers | Dealer DMS / Field App | Local Dealership Systems | Dealership Account | **AUTHENTICATED / DEALER ACCESS REQUIRED** | `backend/app/modules/service/` | Authoritative `ServiceJob` & `ServiceEvent` nodes |

---

## 6. Blueprint & Required Content for `docs/research/PHASE_9_INTEGRATION_INVENTORY.md`

To satisfy Acceptance Criteria 1 and Requirement R1, `docs/research/PHASE_9_INTEGRATION_INVENTORY.md` must be constructed with the following authoritative sections:

### 1. Document Control & Objective
- Explicit declaration of Phase 9 scope: replace prototype placeholders with verified real European integrations where accessible, preserving Neo4j AuraDB graph core.

### 2. Authoritative Classification Taxonomies & Criteria
- Rigorous definition of the 8 authoritative status categories:
  1. `CONNECTED`: Verified live request execution or approved sandbox response.
  2. `ACCESS AVAILABLE — READY TO CONNECT`: Publicly reachable API / sandbox with verified specification, ready for adapter instantiation.
  3. `AUTHENTICATED / DEALER ACCESS REQUIRED`: Genuine OEM system, access restricted to authorized Hitachi dealers.
  4. `PARTNER / COMMERCIAL ACCESS REQUIRED`: Enterprise logistics or ERP interface requiring commercial SLA.
  5. `API NOT PUBLICLY DOCUMENTED`: Commercial system exists, but no developer documentation is published.
  6. `NOT FOUND`: No interface or system identified matching the capability.
  7. `NOT APPLICABLE`: US, non-European, or incompatible architecture items.
  8. `SYNTHETIC FALLBACK`: Explicitly tagged mock provider (`synthetic: true`, `data_source: 'SYNTHETIC_DEMO'`).
- The Strict Non-Fabrication Rule: Formal declaration that no integration is marked `CONNECTED` without live or sandbox verification.

### 3. Comprehensive Master Matrix (9 Operational Domains)
- Complete tabular inventory covering all 9 operational domains (as specified in Section 5 of this report).

### 4. Domain-by-Domain Technical Deep Dives (Sections 4.1 through 4.9)
- Detailed breakdown of each domain:
  - Technical role in fulfilment journey
  - External systems and documented endpoints
  - Security, authentication, and token handling
  - Request/response payload schemas
  - Neo4j AuraDB entity mapping and provenance recording
  - Concrete adapter class vs. synthetic fallback class

### 5. European Carrier & Logistics Landscape Review
- Detailed technical evaluation of DHL Express, PostNL, DPD, DB Schenker, and OSRM European road routing.
- Sandbox endpoint configurations and header specifications.

### 6. Architecture & Data Governance Boundaries
- Invariant enforcement: Neo4j AuraDB as single runtime store, 0 SQLite/PostgreSQL, 0 US records.
- Provenance tagging rules (`synthetic`, `data_source`, `source_id`, `synced_at`).

### 7. Integration Health & Status API Design (`/api/v1/health/integrations`)
- Endpoint contract and JSON response model.

---

## 7. Concrete Adapter Architecture & AuraDB Synchronization (R2)

To satisfy Requirement R2, concrete adapters must be implemented behind provider contracts without leaking vendor specifics into core domain services:

### 7.1 Provider Contract Matrix:
The codebase currently contains 7 provider contracts in `backend/app/integrations/contracts/` and must be expanded to all 9:
1. `InventoryProvider` (`contracts/inventory.py`) — Existing
2. `PricingProvider` (`contracts/pricing.py`) — Existing
3. `OrderProvider` (`contracts/order.py`) — Existing
4. `RoutingProvider` (`contracts/routing.py`) — Existing
5. `ShippingRateProvider` (`contracts/shipping_rate.py`) — Existing
6. `ShipmentProvider` (`contracts/shipment.py`) — Existing
7. `TrackingProvider` (`contracts/tracking.py`) — Existing
8. `ServiceProvider` (`contracts/service.py`) — **Required New Contract**
9. `DealerProvider` (`contracts/dealer.py`) — **Required New Contract**

### 7.2 Implementation Guidelines:
1. **Concrete Adapters**:
   - `DHLExpressAdapter`: Real HTTP client with configurable timeout (e.g. 5.0s), handling live or sandbox API responses when `DHL_API_KEY` is present; falling back to `NOT_CONNECTED` when missing.
   - `NeoviaLogisticsAdapter`: Real TMS HTTP/EDI client with timeout and structured logging when `NEOVIA_API_KEY` is present.
   - `OSRMRouteAdapter`: Concrete implementation of `RoutingProvider` querying `router.project-osrm.org` for authentic European road transit distances and driving times.
   - `HitachiDealerFeedAdapter`: Concrete implementation of `DealerProvider` connecting to the public HCME dealer locator JSON feed.
2. **Security & Logging**:
   - Zero credential leakage in logs: All API keys and tokens must be masked (e.g. `dhl_key[:4] + '****'`).
   - All timeouts strictly bounded (connect timeout: 3s, read timeout: 5s).
   - Network errors caught gracefully and translated into typed error results (`status="UNAVAILABLE"`), never unhandled exceptions.
3. **Neo4j AuraDB Provenance Synchronization**:
   - When external responses are received, write synchronization metadata onto the corresponding AuraDB nodes:
     - `externalId`: e.g. carrier tracking number or partner waybill ID.
     - `syncedAt`: ISO-8601 UTC timestamp of last successful sync.
     - `dataSource`: e.g. `'DHL_EXPRESS_EU'`, `'NEOVIA_TMS_OOSTERHOUT'`, `'OSRM_EUROPE'`.
     - `synthetic`: `false` for verified real/sandbox records; `true` for demo fallbacks.

---

## 8. Integration Health & Status API Design (`/api/v1/health/integrations`) (R4)

To satisfy Requirement R4, an integration status endpoint must be exposed:
- **Route**: `GET /api/v1/health/integrations`
- **Output Schema**:
```json
{
  "timestamp": "2026-09-23T11:20:00Z",
  "status": "UP",
  "database": {
    "provider": "Neo4j AuraDB",
    "status": "CONNECTED",
    "latency_ms": 12.4
  },
  "integrations": [
    {
      "domain": "Parts/Product Master",
      "provider": "AuraDB Graph Core",
      "classification": "CONNECTED",
      "status": "ACTIVE",
      "mode": "CANONICAL"
    },
    {
      "domain": "Inventory",
      "provider": "Neovia WMS / EPC Oosterhout",
      "classification": "PARTNER / COMMERCIAL ACCESS REQUIRED",
      "status": "NOT_CONNECTED",
      "mode": "SYNTHETIC_FALLBACK"
    },
    {
      "domain": "Pricing",
      "provider": "HCME Commercial Pricing",
      "classification": "AUTHENTICATED / DEALER ACCESS REQUIRED",
      "status": "NOT_AVAILABLE",
      "mode": "HONEST_PLACEHOLDER"
    },
    {
      "domain": "Dealer",
      "provider": "HCME Public Dealer Locator Feed",
      "classification": "ACCESS AVAILABLE — READY TO CONNECT",
      "status": "CONNECTED",
      "mode": "LIVE_FEED_SYNCED"
    },
    {
      "domain": "Order/ERP",
      "provider": "HCME Core ERP (SAP)",
      "classification": "PARTNER / COMMERCIAL ACCESS REQUIRED",
      "status": "NOT_CONNECTED",
      "mode": "SYNTHETIC_FALLBACK"
    },
    {
      "domain": "Allocation",
      "provider": "AuraDB Distributed Ledger",
      "classification": "NOT APPLICABLE (INTERNAL ENGINE)",
      "status": "ACTIVE",
      "mode": "CANONICAL"
    },
    {
      "domain": "Shipment/TMS",
      "provider": "OSRM European Road Router",
      "classification": "ACCESS AVAILABLE — READY TO CONNECT",
      "status": "CONNECTED",
      "mode": "PUBLIC_SERVICE"
    },
    {
      "domain": "Carrier Tracking",
      "provider": "DHL Express Europe",
      "classification": "ACCESS AVAILABLE — READY TO CONNECT",
      "status": "NOT_CONNECTED",
      "mode": "SYNTHETIC_FALLBACK"
    },
    {
      "domain": "Service",
      "provider": "AuraDB Service Job Engine",
      "classification": "NOT APPLICABLE (INTERNAL ENGINE)",
      "status": "ACTIVE",
      "mode": "CANONICAL"
    }
  ]
}
```

---

## 9. Quality Assurance & Non-Regression Roadmap

To satisfy Requirement R4 and Acceptance Criteria:
1. **Backend Pytest Suite**: All 98 baseline tests + new Phase 9 integration tests must pass with 100% success rate.
2. **Phase 6 Allocation Concurrency**: 15 tests executed across 3 consecutive runs (45 tests total) with 0 deadlocks and 0 race conditions.
3. **Frontend Tests**: 82/82 unit/component tests passing.
4. **TypeScript & Build**: `tsc --noEmit` returns 0 errors; `npm run build` succeeds cleanly.
5. **AuraDB Graph Verification**: Integrity script validates:
   - 0 orphan ShipmentEvents or ServiceEvents
   - 0 duplicate part numbers, dealer IDs, or order IDs
   - 0 US/non-European records
   - 0 real canonical nodes marked synthetic
   - 100% demo/fallback nodes tagged `synthetic: true` and `data_source: 'SYNTHETIC_DEMO'`.
