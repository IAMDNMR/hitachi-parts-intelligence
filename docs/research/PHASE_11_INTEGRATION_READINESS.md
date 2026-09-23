# Phase 11 — Enterprise Integration Readiness & Boundary Specifications

**Status**: PRODUCTION-READY ARCHITECTURE SPECIFICATION  
**Author**: Antigravity Autonomous Systems Agent  
**Date**: 2026-09-23  
**System Target**: Hitachi Construction Machinery Europe NV (HCME) Aftersales Ecosystem  

---

## Executive Summary

Phase 11 establishes a strict **data-truth perimeter** across the Hitachi Construction Machinery Europe (HCME) aftersales platform. While the user-facing Parts Store, Parts Intelligence Assistant, and Knowledge Graph are fully functional and backed by live Neo4j AuraDB instances, the underlying operational enterprise integrations (SAP ERP, EWM, TM, DMS, and commercial carrier networks) are formally defined as **`NOT_CONNECTED`**.

This document specifies the exact architecture, provider interfaces, authentication protocols, canonical data schemas, circuit-breaker policies, and target endpoints required to transition from the current verified synthetic demo state to live production enterprise connectivity.

```
       ┌────────────────────────────────────────────────────────┐
       │             Parts Store & E-Commerce UI               │
       └───────────────────────────┬────────────────────────────┘
                                   │
                     REST / OpenAPI / SSE Layer
                                   │
       ┌───────────────────────────▼────────────────────────────┐
       │            FastAPI Microservice Layer                  │
       └─────┬──────────────┬──────────────┬──────────────┬─────┘
             │              │              │              │
    [B1: Part Master] [B2: Inventory] [B3: Pricing] [B4: Order Alloc]
             │              │              │              │
    ┌────────▼──────────────▼──────────────▼──────────────▼─────┐
    │     Abstract Integration Boundary Layer (Dependency Inj.)  │
    └────────┬──────────────┬──────────────┬──────────────┬─────┘
             │              │              │              │
       [Active State]       │        [Production Readiness]
    Demo / Synthetic Provider│        Enterprise Connector (Pending)
   (Deterministic Mock Engine)│       (SAP OData v4, REST, EDI)
                            │
       =====================▼=============================
                 FIREWALL / INTEGRATION BOUNDARY
                 Status: NOT_CONNECTED (Declared)
       ===================================================
```

---

## 1. Enterprise Integration Boundaries

```
| Boundary ID | Domain Function | Target Enterprise System | Current Operational State | Connector Interface |
| :--- | :--- | :--- | :--- | :--- |
| **B1** | Global Part Master & Fitment | SAP S/4HANA Materials Management (MM) | `NOT_CONNECTED` (Graph/Excel Seeded) | `IPartMasterProvider` |
| **B2** | Depot Inventory & Stock Availability | SAP Extended Warehouse Mgmt (EWM) | `NOT_CONNECTED` (Synthetic Demo State) | `IInventoryProvider` |
| **B3** | Customer Pricing & Net Conditions | SAP Sales & Distribution (SD - Pricing) | `NOT_CONNECTED` (Deterministic Demo Matrix) | `IPricingProvider` |
| **B4** | Sales Order Processing & Allocation | SAP Sales & Distribution (SD - Order) | `NOT_CONNECTED` (In-Memory Atomic Engine) | `IOrderAllocationProvider` |
| **B5** | European Freight Rates & Transit Times | SAP Transportation Management (TM) | `NOT_CONNECTED` (Haversine Geo Engine) | `ITransportationProvider` |
| **B6** | Multi-Carrier Tracking & Milestones | Commercial Carriers (DHL, Schenker, DSV) | `NOT_CONNECTED` (Synthetic Event Stream) | `ICarrierTrackingProvider` |
| **B7** | Dealer Service Dispatch & Fitment | Authorized Dealer DMS / Landcros DMS | `NOT_CONNECTED` (Verified Network Directory) | `IDealerDMSProvider` |
```

---

## 2. Boundary Detail Specifications

### Boundary B1: Global Part Master & Fitment
- **Operational Purpose**: Authoritative source of truth for part numbers, descriptions, dimensions, weight, lifecycle status (active, superseded, obsolete), supersession chains, and machine fitment compatibility.
- **Current State**: `NOT_CONNECTED`. Sourced from `HITACHI_AFTERSALES_ECOM_GRAPH_MASTER.xlsx`, validated against official HCME publications, and loaded into Neo4j AuraDB.
- **Target System**: SAP S/4HANA Material Master via SAP Business Accelerator Hub (API `API_PRODUCT_SRV` or `A_Product`).
- **Protocol & Auth**: HTTPS / OData v4 with OAuth 2.0 mTLS (Client Credentials grant).
- **Target Schema**:
```json
{
  "Product": "4663907",
  "ProductType": "ZPRT",
  "BaseUnit": "EA",
  "GrossWeight": 24.5,
  "WeightUnit": "KGM",
  "ProductGroup": "ELEC",
  "to_Description": [
    { "Language": "EN", "ProductDescription": "Genuine 12V 120Ah Heavy-Duty Battery" }
  ],
  "to_ProductPlant": [
    { "Plant": "NL01", "IsMarkedForDeletion": false }
  ]
}
```
- **Fallback / Circuit Breaker**: Fallback to Neo4j cached local graph with an explicit UI banner: `Cached catalog state · Live SAP sync degraded`.

---

### Boundary B2: Central Depot Inventory & Stock Availability
- **Operational Purpose**: Real-time ATP (Available-To-Promise) queries against HCME European Parts Centre (EPC) in Oosterhout, Netherlands (Plant NL01, Storage Location 0001).
- **Current State**: `NOT_CONNECTED`. Uses deterministic synthetic availability initialized at 15–45 units per verified part.
- **Target System**: SAP EWM (Extended Warehouse Management) or SAP S/4HANA Stock Availability API (`API_STOCK_AVAILABILITY`).
- **Protocol & Auth**: HTTPS / REST JSON or OData v4; API Key + JWT Bearer.
- **Target Schema**:
```json
{
  "Material": "4663907",
  "Plant": "NL01",
  "StorageLocation": "0001",
  "AvailableStock": 42,
  "Unit": "EA",
  "NextInboundDate": "2026-09-30T08:00:00Z",
  "NextInboundQty": 50
}
```
- **Fallback / Circuit Breaker**: If query fails or times out (>1500ms), lock checkout button to `Stock Enquiry Required` and prevent speculative order booking.

---

### Boundary B3: Customer-Specific Pricing & Conditions
- **Operational Purpose**: Determination of net dealer purchase price, customer tier discounts, bulk rebates, surcharges, VAT, and core deposit values (remanufactured components).
- **Current State**: `NOT_CONNECTED`. Synthetic demo pricing based on baseline benchmark rates.
- **Target System**: SAP SD Pricing Engine (Condition Technique via BAPI or `API_SALES_PRICING`).
- **Protocol & Auth**: HTTPS / RFC via SAP NetWeaver Cloud Connector or SAP Integration Suite.
- **Target Schema**:
```json
{
  "CustomerNumber": "DLR-10822",
  "SalesOrganization": "1000",
  "DistributionChannel": "10",
  "Division": "00",
  "Items": [
    {
      "Material": "4663907",
      "Quantity": 1,
      "NetPrice": 185.00,
      "Currency": "EUR",
      "ConditionType": "PR00",
      "TaxAmount": 38.85
    }
  ]
}
```
- **Fallback / Circuit Breaker**: Present indicative list price clearly watermarked: `Demo Pricing · Binding commercial quotation subject to SAP confirmation`.

---

### Boundary B4: Sales Order Processing & Allocation
- **Operational Purpose**: Immediate reservation of warehouse stock, generation of SAP Sales Order document (SO), and commit of picking task.
- **Current State**: `NOT_CONNECTED`. Handled by local FastAPI concurrency-safe atomic allocation service with UUID tracking.
- **Target System**: SAP S/4HANA Sales Order Processing (`API_SALES_ORDER_SRV`).
- **Protocol & Auth**: HTTPS / OData v4 POST with 2-phase idempotency key header (`X-Idempotency-Key`).
- **Target Schema**:
```json
{
  "SalesOrderType": "OR",
  "SalesOrganization": "1000",
  "SoldToParty": "DLR-10822",
  "PurchaseOrderByCustomer": "HCME-ORD-20260923-001",
  "to_Item": [
    {
      "Material": "4663907",
      "RequestedQuantity": 2,
      "Plant": "NL01"
    }
  ]
}
```
- **Fallback / Circuit Breaker**: Store order in persistent transaction outbox (`PENDING_SAP_TRANSMISSION`) with automatic retry queue (exponential backoff).

---

### Boundary B5: European Road Transportation & Carrier Rates
- **Operational Purpose**: Dynamic freight calculation, routing selection (Road Standard, Road Express, Rail Standard, Air Express), and transit-day computation from Oosterhout Depot.
- **Current State**: `NOT_CONNECTED`. Deterministic multi-modal rate calculator based on 6 European distance bands, Haversine road routing (1.25x curvature factor), and business-day calendar rules.
- **Target System**: SAP Transportation Management (TM) or Enterprise TMS (Transporeon / MercuryGate).
- **Protocol & Auth**: HTTPS / REST JSON or EDIFACT IFTMIN/IFTSTA.
- **Target Schema**:
```json
{
  "Origin": { "City": "Oosterhout", "Country": "NL", "PostalCode": "4906 AA" },
  "Destination": { "City": "Matrei am Brenner", "Country": "AT", "PostalCode": "6143" },
  "WeightKg": 49.0,
  "RequestedServiceLevel": "ROAD_EXPRESS",
  "CalculatedDistanceKm": 866.15,
  "EstimatedTransitDays": 2,
  "CalculatedFreightRateEur": 155.00
}
```
- **Fallback / Circuit Breaker**: Maintain current deterministic rate engine as the fallback baseline pricing matrix.

---

### Boundary B6: Multi-Carrier Real-Time Milestone Tracking
- **Operational Purpose**: Polling and Webhook ingestion of package transit checkpoints (`PICKED_UP`, `DEPARTED_DEPOT`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`).
- **Current State**: `NOT_CONNECTED`. Synthetic stateful event engine (`test_phase7_shipment_tracking.py`) providing simulated milestone telemetry.
- **Target System**: Multi-carrier aggregation API (Project44, Shippeo, or direct DHL Freight / Schenker APIs).
- **Protocol & Auth**: Webhooks (HMAC SHA-256 signature verification) + REST JSON fallback.
- **Target Schema**:
```json
{
  "TrackingNumber": "TRK-NL01-2026-092301",
  "CarrierCode": "DHL_FREIGHT_EU",
  "MilestoneCode": "IN_TRANSIT",
  "Timestamp": "2026-09-24T14:22:00Z",
  "Location": "Frankfurt Hub, Germany",
  "Latitude": 50.1109,
  "Longitude": 8.6821,
  "EstimatedDelivery": "2026-09-25T17:00:00Z"
}
```
- **Fallback / Circuit Breaker**: Gracefully render last-known status timestamp with `Carrier tracking live updates pending` status.

---

### Boundary B7: Dealer Network Service Dispatch & Fitment
- **Operational Purpose**: Dispatch of parts to certified dealer branches, technician appointment scheduling, and work order creation in dealer local Dealer Management System (DMS).
- **Current State**: `NOT_CONNECTED`. Sourced from 182 verified European dealer branches (181 mapped with GPS, 1 unmapped) in Neo4j AuraDB.
- **Target System**: Certified Dealer DMS (CDK Global, Keyloop, Reynolds & Reynolds, or Hitachi Landcros Connect DMS).
- **Protocol & Auth**: REST / GraphQL with dealer API gateway token.
- **Target Schema**:
```json
{
  "DealerBranchId": "DLR-10822",
  "WorkOrderType": "CUSTOMER_SERVICE_PARTS_FITMENT",
  "MachineModel": "ZX210LC-7",
  "SerialPin": "HCMDFJ00E00012345",
  "ScheduledDate": "2026-09-26T09:00:00Z",
  "RequiredParts": ["4663907"]
}
```
- **Fallback / Circuit Breaker**: Standard service booking stored locally, generating an automated email/fax dispatch notification to the branch service desk.

---

## 3. Data Truth Compliance Statement

To ensure zero ambiguity during enterprise demos, technical reviews, and production handover:
1. **No synthetic data** shall ever be represented to customer stakeholders or end-users as real-time SAP inventory or carrier telemetry.
2. The UI headers and confirmation screens explicitly carry the **`SYNTHETIC DEMO DATA`** or **`DEMO DATA (NOT CONNECTED)`** badge.
3. Every API payload emitted by demo endpoints includes the header `X-HCME-Data-Source: DEMO_SYNTHETIC` and `X-HCME-Connected: FALSE`.
4. Transition to live production requires only providing verified endpoint URLs and credential secrets to the abstract provider factory without redesigning application code.
