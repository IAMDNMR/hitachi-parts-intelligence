# Phase 10 — Parts Store Fulfilment & Transportation Data Audit

**Status**: COMPLETED AUDIT REPORT  
**Date**: 2026-09-23  
**Auditor**: Antigravity (Advanced Agentic Architecture Audit)  
**Target Path**: `docs/research/PHASE_10_PARTS_STORE_FULFILMENT_DATA_AUDIT.md`  
**Purpose**: Comprehensive, end-to-end technical and data audit of the HCME Parts Store ordering, fulfilment, and transportation architecture prior to drafting the unified final implementation prompt.

---

## 1. Executive Summary & Audit Objectives

This audit examines the current implementation of the Parts Store ordering and fulfilment engine across both the frontend React application and the FastAPI/Neo4j backend.

### Core Audit Questions Answered:
1. **What data currently exists?** Official HCME parts catalogue (60 canonical parts), 77 machine models, 182 dealer branches (with GPS coordinates), 1,720 SAP supplier master records, and the central Oosterhout depot facility record (`DEPOT-OOSTERHOUT`).
2. **What data is synthetic?** Seeded demo stock snapshots (`InventorySnapshot`), simulated order pricing (`TestPricingProvider`), simulated carrier dispatches (`TestShipmentProvider`), and mock dealer service jobs (`TestServiceProvider`).
3. **What data is real/source-derived?** Part specifications and numbers, machine models, dealer branch names/locations/contacts/coordinates, supplier master records, depot facility facts, and straight-line great-circle distances between the depot and dealer coordinates.
4. **What data is NOT_CONNECTED?** Real carrier API feeds (DHL Express, Neovia TMS, PostNL, DB Schenker), live ERP stock feeds (SAP S/4HANA), live dealer stock feeds, and real European road toll/freight rate tariffs.
5. **What data is missing?** A structured, multi-modal European transport option engine (Road Standard/Express, Rail, Air Express), configurable distance-band rate cards, transit time lookup rules, and a dedicated, guided multi-stage checkout UI.
6. **What does the current fulfilment process actually do?** It generates candidate fulfilment options from inventory snapshots, lets the user select an option, locks an inventory ledger allocation, creates an internal order, simulates carrier dispatch, records tracking events, and steps through dealer service milestones.
7. **What transportation options are currently supported?** In the live UI, transport mode, carrier, transit time, and cost are displayed as **NOT_CONNECTED** because `is_confirmed` is `False` in mock providers. In the backend mocks, hardcoded values (€35/€65/€15/€45/€85) exist in `shipping_rate_mock.py` and `routing_mock.py`.
8. **What needs to be added?** A realistic, configurable, transparent **SYNTHETIC DEMO TRANSPORT MODEL** representing European freight dynamics (Road, Rail, Air) with explicit distance-band pricing and normal vs express timelines, delivered via a unified, step-by-step checkout journey.

---

## 2. Audit of Current Parts Store Flow (Stage-by-Stage Trace)

Below is the verified end-to-end trace from the live codebase across all 11 stages:

```
[1. Cart]
   ↓
[2. Requester]
   ↓
[3. Destination Dealer]
   ↓
[4. Availability]
   ↓
[5. Fulfilment Options]
   ↓
[6. Allocation]
   ↓
[7. Order]
   ↓
[8. Shipment]
   ↓
[9. Tracking]
   ↓
[10. Dealer Service]
   ↓
[11. Close]
```

### Detailed Stage Matrix

| Stage | UI Component | API Endpoint | Backend Service | Neo4j Nodes & Relationships | Data Source & Provider | Provenance Status |
|---|---|---|---|---|---|---|
| **1. Cart** | `PartsStore.tsx` (`QuoteCartPanel`) | None (Client-side) | Local browser storage | None | `localStorage[hcme-parts-cart]` | **REAL / SOURCE_DERIVED** (items from HCME catalogue) |
| **2. Requester** | `AvailabilityChecker.tsx` (Name & Email fields) | `POST /api/v1/fulfilment-requests` | `app/api/v1/fulfilment.py:create_fulfilment_request` | `(:Customer {email})-[:REQUESTED]->(:FulfilmentRequest)` | User input, stored in Neo4j Customer node | **USER_INPUT** (persisted to graph) |
| **3. Destination Dealer** | `AvailabilityChecker.tsx` (Dealer selector dropdown) | `GET /api/v1/dealers` | `app/modules/dealer/service.py:list_dealers` | `(:DealerBranch)` | `dealers.csv` (182 certified European branches) | **REAL / SOURCE_DERIVED** |
| **4. Availability** | `AvailabilityChecker.tsx` (`Check Stock` button) | `POST /api/v1/fulfilment-requests/{id}/availability` | `app/modules/availability/service.py:check_availability` | `(:InventoryCache)` snapshots linked to part | `SyntheticDemoInventoryProvider` reading `(:InventorySnapshot)` | **SYNTHETIC_DEMO** (labelled clearly) |
| **5. Fulfilment Options** | `FulfilmentOptionSelector.tsx` | `POST /api/v1/fulfilment-requests/{id}/options`, `POST .../select-option` | `app/modules/fulfilment/service.py:generate_fulfilment_options` | `(:FulfilmentOption)-[:OPTION_OF]->(:FulfilmentRequest)` | `TestRoutingProvider` & `TestShippingRateProvider` | **NOT_CONNECTED** (cost & carrier null in live view) |
| **6. Allocation** | `AllocationOrderPanel.tsx` (`Allocate Inventory`) | `POST /api/v1/fulfilment-requests/{id}/allocation` | `app/modules/allocation/service.py:create_allocation` | `(:Allocation)`, `(:InventoryLedger)` | `ledger.py` (optimistic version locking) | **SYNTHETIC_DEMO** (state machine verified) |
| **7. Order** | `AllocationOrderPanel.tsx` (`Place Order`) | `POST /api/v1/fulfilment-requests/{id}/order` | `app/modules/order/service.py:create_order` | `(:Order)`, `(o)-[:BASED_ON_ALLOCATION]->(a)`, `(r)-[:HAS_ORDER]->(o)` | `TestPricingProvider` (simulated list price) | **SYNTHETIC_DEMO** |
| **8. Shipment** | `AllocationOrderPanel.tsx` (`Create Shipment`) | `POST /api/v1/shipments` | `app/modules/shipment/service.py:create_shipment` | `(:Shipment)`, `(o)-[:HAS_SHIPMENT]->(sh)`, `(sh)-[:SHIPPED_TO]->(d)` | `TestShipmentProvider` (simulated dispatch) | **SYNTHETIC_DEMO** (no real carrier API) |
| **9. Tracking** | `AllocationOrderPanel.tsx` (`Simulate Dispatch` & `Confirm Delivery`) | `POST /api/v1/shipments/{id}/dispatch`, `POST .../deliver` | `app/modules/shipment/service.py:dispatch_shipment` | `(:ShipmentEvent)-[:EVENT_OF]->(:Shipment)` | Internal state machine simulation | **SYNTHETIC_DEMO** |
| **10. Dealer Service** | `AllocationOrderPanel.tsx` (Service milestone buttons) | `POST /api/v1/service-jobs`, `.../receive-part`, `.../start`, `.../install`, `.../complete` | `app/modules/service/service.py` | `(:ServiceJob)`, `(:ServiceEvent)`, `(o)-[:HAS_SERVICE_JOB]->(sj)` | `TestServiceProvider` | **SYNTHETIC_DEMO** |
| **11. Close** | `AllocationOrderPanel.tsx` (Journey closed banner) | `POST /api/v1/service-jobs/{id}/complete` | `complete_service()` closes `FulfilmentRequest.status = 'COMPLETED'` | `FulfilmentRequest.status = 'COMPLETED'` | Automated graph closure | **SYNTHETIC_DEMO** |

---

## 3. Current State Machine & State Transitions

The system manages lifecycle progression across four coordinated entities in Neo4j:

```
FulfilmentRequest:
  REQUESTED → AVAILABILITY_CHECKED → OPTION_SELECTED → ALLOCATION_PENDING → ALLOCATED → ORDERED → FULFILMENT → SHIPPED → DELIVERED → COMPLETED

Order:
  CREATED → ACCEPTED → CANCELLED (order status remains ACCEPTED during shipment/service)

Shipment:
  CREATED → DISPATCHED → IN_TRANSIT → DELIVERED

ServiceJob:
  OPEN → PART_RECEIVED → IN_PROGRESS → PART_INSTALLED → COMPLETED
```

### Precondition & Guard Enforcement (Audited from Code):
1. `create_fulfilment_request`: Accepts quantity > 0, creates `Customer` node if email provided, sets status `REQUESTED`.
2. `check_availability`: Must be in `REQUESTED`, `DRAFT`, or `AVAILABILITY_CHECKED`. Queries `InventoryProvider`, writes `InventoryCache`, sets status `AVAILABILITY_CHECKED`.
3. `generate_fulfilment_options`: Precondition: status must be `AVAILABILITY_CHECKED` or `OPTION_SELECTED`. Reads `InventoryCache`, generates `FulfilmentOption` nodes.
4. `select_fulfilment_option`: Sets `isSelected = true`, sets `FulfilmentRequest.selectedOptionId`, transitions to `OPTION_SELECTED`.
5. `proceed_to_allocation_pending`: Transitions request from `OPTION_SELECTED` to `ALLOCATION_PENDING`.
6. `create_allocation`: Enforces `ALLOCATION_PENDING`. Checks version-locked `InventoryLedger`. Sets status `ALLOCATED`.
7. `create_order`: Requires `Allocation.status == 'CONFIRMED'`. Consumes allocation (`Allocation.status = 'CONSUMED'`), creates `Order`, transitions request to `ORDERED`.
8. `create_shipment`: Requires `Order.status in ('ACCEPTED', 'CREATED')`. Transitions order to `ACCEPTED`, creates `Shipment` with status `CREATED`.
9. `receive_part`: **Strict guard in `service.py:180`**: Refuses to transition `ServiceJob` to `PART_RECEIVED` unless linked `Shipment.status == 'DELIVERED'`.
10. `complete_service`: Transitions `ServiceJob` to `COMPLETED`, verifies `Shipment` was delivered, and updates `FulfilmentRequest.status = 'COMPLETED'`.

---

## 4. Current Data Sources & Provenance Classification

| Data Category | Neo4j Node / Collection | Authoritative Source File / Script | Live Count | Classification |
|---|---|---|---|---|
| **Parts Catalogue** | `(:Part)` | `20260923_HCME_Master_Data.xlsx` / `parts.csv` | 60 nodes | **SOURCE_DERIVED** |
| **Machinery Catalogue** | `(:Machine)` | `20260923_HCME_Master_Data.xlsx` / `machines.csv` | 77 models | **SOURCE_DERIVED** |
| **Fitment Relationships** | `(:Machine)-[:HAS_PART_FITMENT]->(:Part)` | Official HCME machinery & parts catalogues | 1,041 edges | **SOURCE_DERIVED** |
| **Dealer Network** | `(:DealerBranch)` | `dealers.csv` (scraped from hitachicm.com/eu) | 182 branches | **SOURCE_DERIVED** |
| **Dealer Coordinates** | `DealerBranch.latitude`, `longitude` | Geocoded from dealer addresses | 181 with lat/lon | **DERIVED** |
| **Depot Facility** | `(:Depot {depot_id: "DEPOT-OOSTERHOUT"})` | HCME Official Website Press Release (SRC-050) | 1 node | **SOURCE_DERIVED** |
| **Supplier Master** | `(:Supplier)` | `20260609_Source data for Supplier.xlsx` | 1,720 records | **SOURCE_DERIVED** |
| **Inventory Snapshots** | `(:InventorySnapshot)` | `seed_phase10_demo_data.py` | ~60 records | **SYNTHETIC_DEMO** |
| **Transport Rates & Routes** | `FulfilmentOption` properties | Hardcoded in mock providers | Ephemeral | **NOT_CONNECTED** |
| **Carrier Tracking** | `(:ShipmentEvent)` | Generated in `app/modules/shipment/service.py` | Ephemeral | **SYNTHETIC_DEMO** |

---

## 5. Current Provider Architecture & Factory Registry

The integration architecture in `backend/app/integrations/factory.py` delegates operational domains to pluggable providers controlled by environment variables:

| Domain | Interface Contract | Config Env Var | Default Implementation | Available Concrete Adapters |
|---|---|---|---|---|
| **Inventory** | `InventoryProvider` | `INVENTORY_PROVIDER` | `SyntheticDemoInventoryProvider` | `TestInventoryProvider` |
| **Pricing** | `PricingProvider` | `PRICING_PROVIDER` | `TestPricingProvider` | None (Commercial link required) |
| **Order** | `OrderProvider` | `ORDER_PROVIDER` | `TestOrderProvider` | None (SAP S/4HANA required) |
| **Routing** | `RoutingProvider` | `ROUTING_PROVIDER` | `TestRoutingProvider` | `OSRMRouteAdapter` |
| **Shipping Rate** | `ShippingRateProvider` | `SHIPPING_RATE_PROVIDER` | `TestShippingRateProvider` | None |
| **Shipment** | `ShipmentProvider` | `SHIPMENT_PROVIDER` | `TestShipmentProvider` | `DHLExpressAdapter`, `PostNLAdapter`, `NeoviaLogisticsAdapter` |
| **Tracking** | `TrackingProvider` | `TRACKING_PROVIDER` | `TestTrackingProvider` | `DHLExpressAdapter`, `PostNLAdapter`, `NeoviaLogisticsAdapter` |
| **Service** | `ServiceProvider` | `SERVICE_PROVIDER` | `TestServiceProvider` | None |
| **Dealer** | `DealerProvider` | `DEALER_PROVIDER` | `TestDealerProvider` | `HitachiDealerFeedAdapter` |

---

## 6. Audit of Current Transportation Data & Implementation

### Exact Files and Locations of Transportation Values:

1. **`backend/app/integrations/mocks/shipping_rate_mock.py`**:
   - Line 21: `cost = 15.0`, `days = 0` for Dealer / SAME_DAY.
   - Line 24: `cost = 65.0`, `days = 1` for EXPRESS courier.
   - Line 27: `cost = 45.0`, `days = 2` for REMAN specialist freight.
   - Line 30: `cost = 85.0`, `days = 4` for INTERMODAL freight.
   - Line 34: `cost = 35.0`, `days = 1` for standard road freight.
   - **Crucial Flag**: `is_confirmed = False` is hardcoded on line 14 and line 43.

2. **`backend/app/integrations/mocks/routing_mock.py`**:
   - Line 34: `transport_mode = "INTERNAL_TRANSFER"`, `service_level = "SAME_DAY"`, `days = 0`.
   - Line 48: `transport_mode = "ROAD"`, `service_level = "STANDARD"`, `days = 1`.
   - Line 60: `transport_mode = "COURIER"`, `service_level = "EXPRESS"`, `days = 1`.
   - Line 74: `transport_mode = "ROAD"`, `service_level = "STANDARD"`, `days = 2` (Reman).
   - Line 88: `transport_mode = "ROAD"`, `service_level = "STANDARD"`, `days = 4` (Central).
   - **Crucial Flag**: `is_confirmed = False` on every route option.

3. **`backend/app/integrations/adapters/osrm_adapter.py`**:
   - Line 34–57: `KNOWN_COORDINATES` dictionary containing hardcoded coordinates for `DEPOT-OOSTERHOUT`, Munich, Paris, Antwerp, Hamburg, Lyon, Madrid, Warsaw.
   - Line 130: Road winding factor: `road_km = round(crow_fly * 1.30, 2)`.
   - Line 131: Average truck speed: `duration_hours = round(road_km / 70.0, 2)` (70 km/h).
   - Lines 165–173: Transit day tiering based on driving hours:
     - $\le 14\text{ hours} \rightarrow 1\text{ day}$
     - $\le 28\text{ hours} \rightarrow 2\text{ days}$
     - $> 28\text{ hours} \rightarrow \lceil\text{hours} / 14\rceil\text{ days}$.

4. **`backend/app/modules/fulfilment/service.py`**:
   - Lines 185–186: Collapse unconfirmed routes: `if routes and not any(r.is_confirmed for r in routes): routes = routes[:1]`.
   - Lines 198–208: Strict honesty gate:
     ```python
     route_ok = route.is_confirmed
     rate_ok = route_ok and rate is not None and rate.is_confirmed
     transport_status = "CONFIRMED" if rate_ok else "NOT_CONNECTED"
     transit_days = route.estimated_transit_days if route_ok else None
     cost = rate.shipping_cost if rate_ok else None
     ```
   - **Result**: Because neither the mock routing nor mock rate provider returned `is_confirmed = True`, `transit_days` and `cost` were saved as `null`, and `transportDataStatus` was saved as `"NOT_CONNECTED"`.

5. **`frontend/components/FulfilmentOptionSelector.tsx`**:
   - Lines 163–172:
     ```tsx
     {opt.transport_data_status === 'CONFIRMED' ? (
       <>
         <span>Mode: <strong>{opt.transport_mode}</strong> ({opt.carrier_code})</span>
         <span>Transit: <strong>{opt.transit_days} {opt.transit_days === 1 ? 'day' : 'days'}</strong></span>
         {opt.eta && <span>ETA: <strong>{new Date(opt.eta).toLocaleDateString('en-GB')}</strong></span>}
       </>
     ) : (
       <span>Carrier, transit time and ETA: <strong>not connected</strong> (no HCME carrier data)</span>
     )}
     ```
   - Lines 178–180: Displays `"Not connected"` when `opt.transport_cost == null`.

---

## 7. Transport Modes Evaluation for European Prototype

| Transport Mode | European Operational Context | Prototype Suitability | Recommended Prototype Designation |
|---|---|---|---|
| **ROAD** | Primary mode for European spare parts distribution from Oosterhout, NL across BeNeLux, Germany, France, and Western Europe. | **MANDATORY** | **SYNTHETIC DEMO MODEL** (standard and express van/truck) |
| **RAIL** | Sustainable bulk intermodal freight for heavier subassemblies (undercarriage, counterweights, engines) across Alpine and Central corridors (Rotterdam → Duisburg → Milan/Vienna). | **HIGH VALUE** | **SYNTHETIC DEMO MODEL** (lower cost, eco-friendly, longer transit) |
| **AIR** | Critical machine-down ("AOG/Machine Down") emergency courier for small, urgent parts (electrical controllers, sensors, hydraulic valves) to remote or distant branches (Northern Scandinavia, Southern Iberia, British Isles, Eastern Europe). | **HIGH VALUE** | **SYNTHETIC DEMO MODEL** (emergency express, highest cost, shortest transit) |
| **INTERNAL_TRANSFER / LOCAL_PICKUP** | Parts already at a local dealer branch or neighboring hub. | **SUPPORTED** | **SYNTHETIC DEMO MODEL** (same-day, minimal cost) |
| **MARITIME / SEA** | Overseas container freight (Japan factory → Rotterdam port). Not relevant for customer after-sales order dispatch from European depot. | **EXCLUDED** | **NOT APPLICABLE** (inbound replenishment only) |

---

## 8. Geographic Distance & Coordinate Audit

### Live Database Coordinate Inspection:
- **`DealerBranch` Nodes**: Exactly **181 out of 182** records have valid `latitude` and `longitude` properties populated in Neo4j AuraDB.
  - Examples:
    - `DLR-001` (Inverness, GB): $57.4909^\circ\text{N}, -4.2274^\circ\text{W}$
    - `DLR-004` (Kirchroth, DE): $48.9485^\circ\text{N}, 12.5469^\circ\text{E}$
    - `DLR-006` (Warburg, DE): $51.4982^\circ\text{N}, 9.1291^\circ\text{E}$
- **`Depot` Node (`DEPOT-OOSTERHOUT`)**:
  - `depot_id`: `"DEPOT-OOSTERHOUT"`
  - `city`: `"Oosterhout"`, `country`: `"NL"`
  - `latitude`/`longitude`: Currently `null` on the database node itself, but canonically verified as **$(51.6431^\circ\text{N}, 4.8569^\circ\text{E})$** in `osrm_adapter.py`.
- **Distance Calculation Feasibility**:
  - Using Neo4j spatial point calculation:
    ```cypher
    point.distance(
      point({latitude: d.latitude, longitude: d.longitude}),
      point({latitude: 51.6431, longitude: 4.8569})
    ) / 1000.0 AS straight_line_km
    ```
  - Tested live and verified:
    - Warburg, DE: 295.99 km (Straight-line)
    - Kirchroth, DE: 623.28 km (Straight-line)
    - Inverness, GB: 874.61 km (Straight-line)
    - Zvārtes, LV: 1,367.85 km (Straight-line)

### Crucial Data Discipline:
- **Classification**: Because these are computed from Great-Circle distance between coordinates without actual turn-by-turn road networks, this must be explicitly classified as:
  $$\text{Provenance: } \mathbf{DERIVED\ (STRAIGHT\text{-}LINE\ DISTANCE)}$$
- It must **never** be presented as audited road distance. If an estimated road distance is shown, it must be computed as:
  $$\text{Estimated Road Distance} = \text{Straight-Line Distance} \times 1.25\quad (\text{European Highway Winding Factor})$$

---

## 9. Recommended Distance-Band Model

To support realistic European transportation options without fabricating non-existent carrier contracts, the backend should employ a transparent, configurable distance-band model derived from the straight-line distance from Oosterhout ($51.6431^\circ\text{N}, 4.8569^\circ\text{E}$):

### Distance Bands for European Distribution:

| Band ID | Straight-Line Distance Range | Typical Geographic Scope (from Oosterhout, NL) | Eligible Transport Modes |
|---|---|---|---|
| **BAND_1** | $0 \le d < 100\text{ km}$ | Local Netherlands, Antwerp, Brussels, North Rhine border | Road Standard, Road Express, Local Courier |
| **BAND_2** | $100 \le d < 300\text{ km}$ | BeNeLux, Ruhrgebiet, Frankfurt, Cologne, Lille | Road Standard, Road Express |
| **BAND_3** | $300 \le d < 600\text{ km}$ | Central Germany, Paris / Northern France, Hamburg, Stuttgart | Road Standard, Road Express, Rail Freight |
| **BAND_4** | $600 \le d < 1,000\text{ km}$ | Southern Germany (Munich), Austria, Switzerland, Lyon, London | Road Standard, Road Express, Rail Freight, Air Express |
| **BAND_5** | $1,000 \le d < 1,500\text{ km}$ | Northern Italy, Poland, Czechia, Scotland, Pyrenees | Road Standard, Road Express, Rail Freight, Air Express |
| **BAND_6** | $1,500\text{ km}+$ | Spain, Portugal, Southern Italy, Scandinavia, Baltic States, Balkans | Road Standard, Air Express |

---

## 10. Recommended Normal vs Express Service Level Model

| Dimension | Normal / Standard Delivery | Express / Priority Delivery |
|---|---|---|
| **Primary Value** | Cost efficiency, consolidation, lower CO2 | Maximum speed, emergency machine-down response |
| **Target Transit Time** | 2–5 business days depending on distance band | 1–2 business days (next-day for Bands 1–3, 24–48h for Bands 4–6) |
| **Cutoff Time** | 14:00 CET for same-day dispatch from Oosterhout | 17:00 CET for expedited carrier collection |
| **Eligible Modes** | Road Standard, Rail Freight | Road Express, Air Express |
| **Cost Structure** | Base rate + lower distance-band rate | Higher base rate + higher distance-band rate ($1.6\times$ to $2.2\times$ multiplier) |
| **Weekend Handling** | Standard weekday delivery only | Priority weekend/Saturday delivery option if enabled |

---

## 11. Recommended Transport Option Data Model & Schema

Each generated transport option will adhere to this structured contract:

```typescript
interface TransportOption {
  // Identification
  transport_option_id: string       // e.g. "TR-OPT-ROAD-STD-001"
  fulfilment_request_id: string     // Link to FulfilmentRequest parent
  source_id: string                 // e.g. "DEPOT-OOSTERHOUT"
  destination_branch_id: string     // e.g. "DLR-006"

  // Service Definition
  mode: 'ROAD' | 'RAIL' | 'AIR' | 'INTERNAL_TRANSFER'
  service_level: 'STANDARD' | 'EXPRESS'
  display_name: string              // e.g. "Road Freight Standard", "Air Priority Express"
  carrier_label: string             // e.g. "European Road Logistics Partner (Demo)"

  // Distance & Routing Metrics
  straight_line_distance_km: number // e.g. 295.99
  estimated_road_distance_km: number// e.g. 369.99 (distance_km * 1.25)
  distance_band: string             // e.g. "BAND_2 (100–300 km)"

  // Timeline & Schedule
  transit_days: number              // e.g. 2
  estimated_delivery_date: string   // ISO 8601 Date: "2026-09-25"
  dispatch_cutoff_time: string      // "14:00 CET"

  // Pricing & Currency
  currency: 'EUR'
  base_cost: number                 // Base handling & pickup fee
  distance_cost: number             // Variable distance charge
  service_level_cost: number        // Express premium
  total_transport_cost: number      // Total calculated transport cost

  // Governance & Transparency
  data_class: 'SYNTHETIC_DEMO'
  provenance_note: string           // "Calculated from straight-line distance using synthetic European freight rate model."
  is_selected: boolean
}
```

---

## 12. Current Data Inventory Table

| Data Element | Exists in System? | Current Source | Real / Synthetic / Not Connected | Current Use in Parts Store | Missing Gaps |
|---|---|---|---|---|---|
| **Part** | Yes | `parts.csv` | **REAL / SOURCE_DERIVED** | Store catalogue display, fitment checking | None |
| **Machine** | Yes | `machines.csv` | **REAL / SOURCE_DERIVED** | Applicability filter, machine drawer | None |
| **Dealer** | Yes | `dealers.csv` | **REAL / SOURCE_DERIVED** | Destination branch selector dropdown | Ship-to vs receiving branch distinction |
| **Supplier** | Yes | `20260609_Source data for Supplier.xlsx` | **REAL / SOURCE_DERIVED** | Supplier Risk / Intelligence | Not used in customer store checkout |
| **Depot** | Yes | Neo4j `(:Depot)` | **REAL / SOURCE_DERIVED** | Fulfilment origin location | Lat/long properties missing on node |
| **Customer** | Yes | Graph `(:Customer)` | **USER_INPUT** (stored in graph) | Requester name & email | Saved customer address book |
| **Inventory** | Yes | `(:InventorySnapshot)` | **SYNTHETIC_DEMO** | Availability check (`check_availability`) | No real WMS/ERP feed |
| **Availability Status**| Yes | `(:InventoryCache)` | **SYNTHETIC_DEMO** | Availability badge (AVAILABLE / UNCONFIRMED) | Real stock count |
| **Fulfilment Source** | Yes | `source_id` | **REAL (Depot ID)** | Origin facility designation | Multi-depot routing |
| **Straight-Line Dist**| Partially | Python Haversine in OSRM adapter | **DERIVED** | OSRM fallback | Not written to `FulfilmentOption` |
| **Road Distance** | No | OSRM public API (often offline) | **NOT_CONNECTED** | Unconfirmed in live database | Reliable offline approximation |
| **Transport Mode** | Partially | `routing_mock.py` | **SYNTHETIC_DEMO** (Null in live UI) | Set to null because unconfirmed | Multi-modal selection (Rail, Air) |
| **Service Level** | Partially | `routing_mock.py` | **SYNTHETIC_DEMO** (Null in live UI) | Set to null because unconfirmed | User-selectable Standard vs Express |
| **Transit Time** | Partially | `routing_mock.py` | **SYNTHETIC_DEMO** (Null in live UI) | Set to null because unconfirmed | Consistent distance-band transit time |
| **ETA** | Partially | `fulfilment/service.py` | **SYNTHETIC_DEMO** (Null in live UI) | Set to null because unconfirmed | Delivery calendar calculation |
| **Transport Cost** | Partially | `shipping_rate_mock.py` | **SYNTHETIC_DEMO** (Null in live UI) | Set to null because unconfirmed | Transparent breakdown (base + distance) |
| **Currency** | Yes | `EUR` | **STATIC** | Currency symbol display | Multi-currency (GBP, CHF, SEK) |
| **Carrier** | Partially | `carrier_code` | **NOT_CONNECTED** | Labelled NOT_CONNECTED | Realistic synthetic carrier partner |
| **Order** | Yes | `(:Order)` | **SYNTHETIC_DEMO** | Order record creation | Real SAP order number |
| **Allocation** | Yes | `(:Allocation)` | **SYNTHETIC_DEMO** | Inventory reservation & ledger lock | Real ERP reservation |
| **Shipment** | Yes | `(:Shipment)` | **SYNTHETIC_DEMO** | Shipment creation & dispatch | Real tracking carrier integration |
| **Tracking Events** | Yes | `(:ShipmentEvent)` | **SYNTHETIC_DEMO** | Event log (Created, Dispatched, Delivered) | Real GPS carrier telematics |
| **Dealer Service** | Yes | `(:ServiceJob)` | **SYNTHETIC_DEMO** | Service workflow milestones | Real dealer DMS integration |
| **Part Price** | Partially | `pricing_mock.py` | **SYNTHETIC_DEMO** | Stored on Order node (€) | Catalogue list price not in Parts Store |

---

## 13. Data Provenance Problem & Misleading Value Analysis

To maintain absolute data integrity and client trust, the following current risks must be guarded:

1. **Carrier Name Illusion**:
   - `dhl_adapter.py` mentions `"DHL Express Europe"`. If presented without a disclaimer, users might believe HCME has a live DHL API connection.
   - **Remedy**: Explicitly label carrier output as: `"European Express Logistics Partner (Simulated Model)"`.
2. **Hardcoded Price Fallback**:
   - In `shipping_rate_mock.py`, values like €35.00 and €65.00 are static constants without distance scaling. A 50 km delivery cost the same as a 2,000 km delivery.
   - **Remedy**: Replace arbitrary static constants with the formal Distance-Band Rate Model.
3. **Depot-to-Dealer Distance Label**:
   - If distance is labeled as "Distance: 500 km" without qualification, it implies a turn-by-turn road route was calculated.
   - **Remedy**: Always label distance as `"Straight-Line Distance: 400 km (Est. Road: 500 km)"` with provenance tag `DERIVED`.
4. **Order List Price**:
   - `Order.unitPrice` uses simulated pricing from `TestPricingProvider`.
   - **Remedy**: Order cards must continue to carry the badge: `DEMO PRICING (COMMERCIAL ERP NOT CONNECTED)`.

---

## 14. One-Page vs Step-by-Step UI Architecture

### The Current Problem:
Currently, when a user clicks "Check stock & fulfil" in `PartsStore.tsx`:
- It opens `AvailabilityChecker.tsx` inside the cart modal.
- Submitting the check appends `FulfilmentOptionSelector.tsx` below the form.
- Selecting an option appends `AllocationOrderPanel.tsx` below that.
- Inside `AllocationOrderPanel`, five different sub-steps (Allocate, Place Order, Create Shipment, Dispatch, Service Milestones) all stack vertically on a single overflowing drawer.
- The user experiences visual overload and confusion about where they are in the journey.

### The Solution: One Application Journey, One Stage at a Time

The checkout journey must be refactored into a clear, unified, progressive wizard:

```
[ Stage 1: Cart Review ]
       ↓ Continue
[ Stage 2: Customer Requester Info ]
       ↓ Continue
[ Stage 3: Destination Dealer Selection ]
       ↓ Continue
[ Stage 4: Stock Availability Inspection ]
       ↓ Continue
[ Stage 5: Transportation Options (Compare Mode, Time, Cost) ]
       ↓ Continue
[ Stage 6: Final Review & Order Placement ]
       ↓ Continue
[ Stage 7: Shipment Tracking & Dealer Service Milestones ]
```

### Component Reusability Analysis:
- `AvailabilityChecker.tsx`: Can be decomposed into Stage 2 (Requester), Stage 3 (Dealer), and Stage 4 (Availability Results).
- `FulfilmentOptionSelector.tsx`: Can be upgraded into Stage 5 (Transportation Comparison Matrix).
- `AllocationOrderPanel.tsx`: Can be cleanly split into Stage 6 (Review & Allocation/Order) and Stage 7 (Post-Order Journey: Shipment, Tracking, Service Milestones).

---

## 15. Transport User Decision Model

In Stage 5 (Transportation), the user must be presented with an intuitive comparison card matrix:

```
+-----------------------------------------------------------------------------------------+
| CHOOSE TRANSPORTATION OPTION                                                            |
| Origin: Hitachi European Parts Centre (Oosterhout, NL)                                  |
| Destination: AC Plant Sales (Inverness, GB) · Distance: 875 km (Band 4)                |
+-----------------------------------------------------------------------------------------+

[ Option A: ROAD STANDARD ]             [ Option B: ROAD EXPRESS ]
  Mode: Road Freight                      Mode: Road Courier
  Service: Standard (Economy)             Service: Priority Express
  Transit: 3 Business Days                Transit: 1-2 Business Days
  Estimated Delivery: 26 Sep 2026         Estimated Delivery: 25 Sep 2026
  Cost: €45.00                            Cost: €95.00
  Cutoff: 14:00 CET                       Cutoff: 17:00 CET
  [ Select Option ]                       [ Select Option ]

[ Option C: RAIL INTERMODAL ]           [ Option D: AIR EMERGENCY EXPRESS ]
  Mode: Rail Freight (Eco)                Mode: Air Freight
  Service: Standard Green                 Service: Urgent Machine-Down
  Transit: 4 Business Days                Transit: Next-Day Priority
  Estimated Delivery: 27 Sep 2026         Estimated Delivery: 24 Sep 2026
  Cost: €38.00 (Lowest Carbon)            Cost: €185.00 (Critical Uptime)
  Cutoff: 12:00 CET                       Cutoff: 18:30 CET
  [ Select Option ]                       [ Select Option ]

+-----------------------------------------------------------------------------------------+
| Provenance: SYNTHETIC DEMO TRANSPORT MODEL · Calculated from European Distance Bands   |
+-----------------------------------------------------------------------------------------+
```

---

## 16. Important Data Rule (Integrity Protocol)

To ensure this project maintains the highest standard of technical honesty:
1. **No Fake Carrier Credentials**: Never pretend that live DHL, Neovia, or PostNL credentials are active.
2. **Transparent Provenance Tags**: Every transport rate, transit time, and ETA must carry `provenance: "SYNTHETIC_DEMO"`.
3. **No Arbitrary Random Numbers**: Rates and transit days must be deterministically calculated by the backend distance-band engine based on real dealer coordinates.
4. **Zero Production Code / Database Modifications During Audit**: Verified — this audit has left all production databases, schemas, and endpoints untouched.

---

## 17. Final Recommendations Summary

### A. KEEP
- **Part, Machine, and Dealer Graph**: The 60 parts, 77 machines, 1,041 fitment edges, and 182 certified dealer branches represent authoritative, source-derived master data.
- **State Machine Architecture**: The multi-entity state transitions (`FulfilmentRequest`, `Allocation`, `Order`, `Shipment`, `ServiceJob`) and idempotency handling are robust and well-guarded.
- **Neo4j Spatial Distance Calculation**: Using `point.distance()` between the Oosterhout depot and dealer coordinates is mathematically sound and fast.

### B. MODIFY
- **`generate_fulfilment_options()` in `fulfilment/service.py`**:
  - Replace the current behavior (which collapses unconfirmed routes to null/NOT_CONNECTED) with generation of structured, labelled `SYNTHETIC_DEMO` options for Road, Rail, and Air based on distance bands.
- **`AvailabilityChecker.tsx` and `AllocationOrderPanel.tsx`**:
  - Refactor from vertically stacked inline forms into a guided, step-by-step 7-stage checkout application journey.
- **`FulfilmentOptionSelector.tsx`**:
  - Upgrade into a rich, comparative transportation selection grid allowing the user to weigh Time vs Cost vs Mode.

### C. ADD
- **Configurable Distance-Band Transport Rate Engine**:
  - A backend module (`app/modules/transport/`) that takes origin/destination coordinates, determines the distance band (Bands 1–6), and returns standard and express options for Road, Rail, and Air.
- **Depot Coordinates on Neo4j Node**:
  - Enrich `(:Depot {depot_id: "DEPOT-OOSTERHOUT"})` with `latitude: 51.6431, longitude: 4.8569` so all distance queries can run natively in Cypher.
- **Explicit Review Stage (Stage 6)**:
  - Add an order review step summarizing items, requester, dealer destination, chosen transport option, transit ETA, and total cost before committing allocation and order creation.

### D. REMOVE
- **Static Hardcoded Rates in `shipping_rate_mock.py`**:
  - Remove arbitrary €35/€65/€15 constants that do not scale with distance or transport mode.
- **Duplicate "Check Stock & Fulfil" Panels**:
  - Disallow multiple open fulfilment drawers across cart items; transition to a dedicated single-order checkout flow.

### E. NOT_CONNECTED
- **Real Carrier Telematics**: Explicitly declare live courier tracking and rate APIs as NOT_CONNECTED.
- **Live Commercial ERP Stock**: Explicitly declare SAP S/4HANA live inventory as NOT_CONNECTED.
- **Payment Processing**: Payment gateways remain NOT_CONNECTED (Hitachi After-Sales operates on commercial dealer credit terms).

### F. SYNTHETIC DEMO
- **European Transport Model**: Formally adopt the Road / Rail / Air distance-band rate and transit engine as a first-class, clearly labelled `SYNTHETIC_DEMO` subsystem.
- **Inventory Snapshots**: Retain seeded warehouse stock snapshots clearly labelled as demo stock.
- **Carrier Events**: Retain simulated dispatch, in-transit, and delivery milestones.
- **Dealer Service Milestones**: Retain service job progression (Part Received → In Progress → Installed → Completed).

---

*End of Phase 10 Parts Store Fulfilment & Transportation Data Audit Report.*
