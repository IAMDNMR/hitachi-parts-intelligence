# Architecture & Existing Provider Contracts Investigation Report

**Investigator:** Explorer 1 (Architecture & Existing Provider Contracts Investigator)  
**Date:** 2026-09-23  
**Target Milestone:** Phase 9 Real Integrations  
**Workspace:** `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\backend`  

---

## 1. Executive Summary

Phase 9 mandates replacing prototype `NOT_CONNECTED` and test-provider boundaries with verified real European integrations where accessible, while preserving the existing Neo4j AuraDB runtime graph core and Phase 0–8 verified state.

This investigation conducted a comprehensive, read-only architectural survey of the Python FastAPI backend, provider contracts, mock/test implementations, dependency injection wiring, Neo4j AuraDB repository schemas, and health check endpoints.

### Key Architectural Findings
1. **Provider Contracts (7 Defined, 2 Missing):**
   - Seven abstract provider contracts are currently defined in `backend/app/integrations/contracts/`: `InventoryProvider`, `PricingProvider`, `OrderProvider`, `RoutingProvider`, `ShippingRateProvider`, `ShipmentProvider`, and `TrackingProvider`.
   - Two contracts specified in architecture documentation (`docs/architecture/INTEGRATION_ARCHITECTURE.md` and `ADR-005`) are **not yet defined in code**: `ServiceProvider` and `DealerProvider`.
2. **Existing Concrete Adapters & Mocks:**
   - Seven mock provider implementations exist in `backend/app/integrations/mocks/`: `TestInventoryProvider`, `TestPricingProvider`, `TestOrderProvider`, `TestRoutingProvider`, `TestShippingRateProvider`, `TestShipmentProvider`, and `TestTrackingProvider`.
   - Two European logistics carrier adapters already exist in `backend/app/integrations/adapters/`: `DHLExpressAdapter` and `NeoviaLogisticsAdapter`. However, they inherit from a generic `CarrierAdapter` base class and are **completely unwired / unused** by `shipment/service.py`.
3. **Dependency Injection & Wiring Gap:**
   - There is currently **no dynamic dependency injection or provider registry** for integrations.
   - Services hardcode mock instantiations directly:
     - `app/modules/availability/service.py` calls `provider = TestInventoryProvider()` inline.
     - `app/modules/fulfilment/service.py` instantiates module-level singletons `TestRoutingProvider()` and `TestShippingRateProvider()`.
     - `app/modules/order/service.py` instantiates module-level singletons `TestOrderProvider()` and `TestPricingProvider()`.
     - `app/modules/shipment/service.py` instantiates module-level singletons `TestShipmentProvider()` and `TestTrackingProvider()`.
   - Conversely, `app/modules/intelligence/providers.py` provides a clean precedent using a factory pattern (`get_llm_provider()`) that inspects configuration settings.
4. **Neo4j AuraDB Data Layer & Provenance Modeling:**
   - Sole single source of runtime truth (zero SQLite/Postgres). Pool tuned to 50 max connections, 60s acquisition timeout, 3600s lifetime.
   - `Order`: Missing `external_order_id`, `synced_at`, `synthetic`, and `data_source` properties.
   - `Shipment`: Persists `synthetic: true`, `data_source: 'SYNTHETIC_DEMO'`, `provenance: 'INTERNAL_TEST_WORKFLOW'`. Needs `external_shipment_id`, `synced_at`, and carrier-specific `data_source` when live.
   - `DealerBranch`: 182 canonical European branches imported from official HCME locator. **Critical Caveat:** `app/modules/intelligence/context.py` and `tests/test_operational_demo_data.py` assert `WHERE d.synthetic IS NOT NULL RETURN count(d)` is 0! Setting `synthetic = false` on existing `DealerBranch` nodes would break this regression test unless reconciled.
   - `ServiceJob`: Persists internal lifecycle (`OPEN` → `PART_RECEIVED` → `IN_PROGRESS` → `PART_INSTALLED` → `COMPLETED`) with `synthetic: true`, `data_source: 'SYNTHETIC_DEMO'`. Needs `external_job_id` and `synced_at` for external service/DMS connections.
5. **Health Check Endpoint Extension:**
   - `backend/app/api/v1/health.py` currently mounts `/liveness` and `/readiness` under prefix `/health`.
   - `/api/v1/health/integrations` can be cleanly integrated as `@router.get("/integrations")` in `app/api/v1/health.py`.

---

## 2. Provider Contracts & Interface Specifications (All 9 Domains)

### 2.1 InventoryProvider
- **Location:** `backend/app/integrations/contracts/inventory.py`
- **Class Definition:**
  ```python
  class InventoryProvider(ABC):
      @abstractmethod
      def get_availability(self, query: SourceAvailabilityQuery) -> List[SourceInventoryItem]:
          """Fetch inventory availability from external or internal sources"""
          pass
  ```
- **Input Model:** `SourceAvailabilityQuery`
  - `part_number: str`
  - `quantity: int`
  - `destination_branch_id: str`
  - `customer_id: str`
  - `machine_context: Optional[str] = None`
  - `preferred_sources: Optional[List[str]] = None`
- **Output Model:** `List[SourceInventoryItem]`
  - `source_id: str`
  - `source_name: str`
  - `source_type: SourceType` (`DEALER`, `REGIONAL_DEPOT`, `CENTRAL_DEPOT`, `REMAN_FACILITY`)
  - `location_id: str`
  - `on_hand_qty: int = 0`
  - `reserved_qty: int = 0`
  - `allocated_qty: int = 0`
  - `available_qty: int = 0`
  - `status: InventoryStatus` (`ON_HAND`, `RESERVED`, `ALLOCATED`, `AVAILABLE`, `UNKNOWN`)
  - `inventory_timestamp: str` (ISO 8601)
  - `provenance: str = "SYSTEM"`
  - `is_stale: bool = False`
- **Current Status:** Abstract contract defined. Backed by `TestInventoryProvider` in `mocks/inventory_mock.py`.

---

### 2.2 PricingProvider
- **Location:** `backend/app/integrations/contracts/pricing.py`
- **Class Definition:**
  ```python
  class PricingProvider(ABC):
      @abstractmethod
      def get_price(self, query: PricingQuery) -> PriceQuote:
          """Return an authoritative price quote, or NOT_AVAILABLE if none is connected."""
          pass
  ```
- **Input Model:** `PricingQuery`
  - `part_number: str`
  - `quantity: int`
  - `customer_id: Optional[str] = None`
- **Output Model:** `PriceQuote`
  - `part_number: str`
  - `unit_price: Optional[float] = None`
  - `currency: Optional[str] = None`
  - `status: str = "NOT_AVAILABLE"` (`NOT_AVAILABLE` | `CONFIRMED`)
  - `is_confirmed: bool = False`
- **Current Status:** Abstract contract defined. Backed by `TestPricingProvider` in `mocks/pricing_mock.py` (honestly returns `unit_price=None, status="NOT_AVAILABLE"` per HCME research).

---

### 2.3 OrderProvider
- **Location:** `backend/app/integrations/contracts/order.py`
- **Class Definition:**
  ```python
  class OrderProvider(ABC):
      @abstractmethod
      def submit_order(self, submission: OrderSubmission) -> OrderSubmissionResult:
          """
          Submit an order to the authoritative HCME order/ERP system.
          No real HCME order endpoint is confirmed to exist. Any implementation
          used in this codebase MUST honestly report NOT_CONNECTED rather than
          fabricate acceptance from a real system.
          """
          pass
  ```
- **Input Model:** `OrderSubmission`
  - `order_id: str`
  - `part_number: str`
  - `quantity: int`
  - `source_id: str`
  - `destination_branch_id: str`
- **Output Model:** `OrderSubmissionResult`
  - `accepted: bool`
  - `external_order_reference: Optional[str] = None`
  - `status: str = "NOT_CONNECTED"` (`NOT_CONNECTED` | `ACCEPTED` | `REJECTED`)
  - `message: str = ""`
- **Current Status:** Abstract contract defined. Backed by `TestOrderProvider` in `mocks/order_mock.py`.

---

### 2.4 RoutingProvider
- **Location:** `backend/app/integrations/contracts/routing.py`
- **Class Definition:**
  ```python
  class RoutingProvider(ABC):
      @abstractmethod
      def find_routes(self, query: RouteQuery) -> List[RouteOption]:
          """Determine feasible transport routes and estimated transit time from source to destination."""
          pass
  ```
- **Input Model:** `RouteQuery`
  - `origin_location_id: str`
  - `destination_branch_id: str`
  - `part_number: str`
  - `quantity: int`
- **Output Model:** `List[RouteOption]`
  - `route_id: str`
  - `origin_location_id: str`
  - `destination_branch_id: str`
  - `transport_mode: str` (`ROAD`, `COURIER`, `INTERNAL_TRANSFER`, `AIR`, `UNKNOWN`)
  - `carrier_code: str`
  - `service_level: str` (`STANDARD`, `EXPRESS`, `UNKNOWN`)
  - `estimated_transit_days: int`
  - `is_confirmed: bool = False`
- **Current Status:** Abstract contract defined. Backed by `TestRoutingProvider` in `mocks/routing_mock.py`.

---

### 2.5 ShippingRateProvider
- **Location:** `backend/app/integrations/contracts/shipping_rate.py`
- **Class Definition:**
  ```python
  class ShippingRateProvider(ABC):
      @abstractmethod
      def get_rate(self, query: ShippingRateQuery) -> Optional[ShippingRate]:
          """Return shipping rate estimate for a carrier, route, and package details."""
          pass
  ```
- **Input Model:** `ShippingRateQuery`
  - `carrier_code: str`
  - `service_level: str`
  - `origin_location_id: str`
  - `destination_branch_id: str`
  - `weight_kg: Optional[float] = None`
  - `quantity: int = 1`
- **Output Model:** `Optional[ShippingRate]`
  - `carrier_code: str`
  - `service_level: str`
  - `shipping_cost: float`
  - `currency: str = "EUR"`
  - `estimated_delivery_days: int`
  - `is_confirmed: bool = False`
- **Current Status:** Abstract contract defined. Backed by `TestShippingRateProvider` in `mocks/shipping_rate_mock.py`.

---

### 2.6 ShipmentProvider
- **Location:** `backend/app/integrations/contracts/shipment.py`
- **Class Definition:**
  ```python
  class ShipmentProvider(ABC):
      """Authoritative abstraction over logistics / carrier shipment creation."""
      @abstractmethod
      def create_shipment(self, request: ShipmentCreationRequest) -> ShipmentCreationResult:
          """Create and register a shipment with the carrier system."""
          pass
  ```
- **Input Model:** `ShipmentCreationRequest`
  - `order_id: str`
  - `part_number: str`
  - `quantity: int`
  - `origin_source_id: str`
  - `destination_branch_id: str`
  - `service_tier: str = "STANDARD"`
- **Output Model:** `ShipmentCreationResult`
  - `status: str` (`SUCCESS` / `FAILED` / `NOT_CONNECTED`)
  - `carrier: str`
  - `tracking_number: Optional[str] = None`
  - `estimated_delivery: Optional[str] = None`
  - `message: str`
- **Current Status:** Abstract contract defined. Backed by `TestShipmentProvider` in `mocks/shipment_mock.py`.

---

### 2.7 TrackingProvider
- **Location:** `backend/app/integrations/contracts/tracking.py`
- **Class Definition:**
  ```python
  class TrackingProvider(ABC):
      """Authoritative abstraction over carrier tracking telemetry."""
      @abstractmethod
      def get_tracking(self, query: TrackingQuery) -> TrackingResult:
          """Fetch tracking events and current status for a given tracking reference."""
          pass
  ```
- **Input Model:** `TrackingQuery`
  - `tracking_number: str`
- **Output Model:** `TrackingResult`
  - `tracking_number: str`
  - `carrier: str`
  - `status: str` (`CREATED`, `DISPATCHED`, `IN_TRANSIT`, `DELIVERED`, `EXCEPTION`)
  - `estimated_delivery: Optional[str] = None`
  - `events: List[TrackingEventPayload]`
  - `integration_status: str = "NOT_CONNECTED"`
- **Current Status:** Abstract contract defined. Backed by `TestTrackingProvider` in `mocks/tracking_mock.py`.

---

### 2.8 ServiceProvider (Missing in Code — Architecture Specified)
- **Status:** **NOT YET IMPLEMENTED IN CODE**.
- **Architectural Reference:** `docs/architecture/INTEGRATION_ARCHITECTURE.md` §1 ("Optional future adapter to an external service-job system, if one is confirmed beyond ConSite").
- **Current Implementation:** In Phase 8 (`app/modules/service/service.py`), service operations (`create_service_job`, `receive_part`, `start_service`, `install_part`, `complete_service`, `cancel_service_job`) are handled directly against Neo4j AuraDB nodes (`ServiceJob`, `ServiceEvent`).
- **Required Phase 9 Specification:**
  - File: `backend/app/integrations/contracts/service.py`
  - Proposed Abstract Class:
    ```python
    class ServiceProvider(ABC):
        @abstractmethod
        def register_service_job(self, order_id: str, dealer_id: str, part_number: str) -> ServiceJobSyncResult: ...
        @abstractmethod
        def get_service_job_status(self, external_job_id: str) -> ServiceJobStatusResult: ...
    ```
  - Mock Implementation: `TestServiceProvider` in `backend/app/integrations/mocks/service_mock.py`.

---

### 2.9 DealerProvider (Missing in Code — Architecture Specified)
- **Status:** **NOT YET IMPLEMENTED IN CODE**.
- **Architectural Reference:** `docs/architecture/INTEGRATION_ARCHITECTURE.md` §1 ("Source of Dealer/Dealer Branch/Territory/Capability data (`DEALER_ARCHITECTURE.md`) — UNKNOWN / Future").
- **Current Implementation:** 182 real European dealer branch records are statically loaded into Neo4j via `docs/data/neo4j/import/nodes/dealers.cypher`. No backend adapter interface exists for dynamic synchronization or query.
- **Required Phase 9 Specification:**
  - File: `backend/app/integrations/contracts/dealer.py`
  - Proposed Abstract Class:
    ```python
    class DealerProvider(ABC):
        @abstractmethod
        def get_dealer_branch(self, dealer_id: str) -> Optional[DealerBranchInfo]: ...
        @abstractmethod
        def sync_dealer_network(self) -> DealerNetworkSyncResult: ...
    ```
  - Mock Implementation: `TestDealerProvider` in `backend/app/integrations/mocks/dealer_mock.py`.

---

## 3. Existing Concrete & Mock Providers and Dependency Injection Analysis

### 3.1 Inventory of Concrete & Mock Implementations

| Interface | Mock Class | Concrete / Adapter Class | File Path |
|---|---|---|---|
| `InventoryProvider` | `TestInventoryProvider` | None | `app/integrations/mocks/inventory_mock.py` |
| `PricingProvider` | `TestPricingProvider` | None | `app/integrations/mocks/pricing_mock.py` |
| `OrderProvider` | `TestOrderProvider` | None | `app/integrations/mocks/order_mock.py` |
| `RoutingProvider` | `TestRoutingProvider` | None | `app/integrations/mocks/routing_mock.py` |
| `ShippingRateProvider` | `TestShippingRateProvider` | None | `app/integrations/mocks/shipping_rate_mock.py` |
| `ShipmentProvider` | `TestShipmentProvider` | `DHLExpressAdapter`, `NeoviaLogisticsAdapter` | `app/integrations/mocks/shipment_mock.py`<br>`app/integrations/adapters/dhl_adapter.py`<br>`app/integrations/adapters/neovia_adapter.py` |
| `TrackingProvider` | `TestTrackingProvider` | `DHLExpressAdapter`, `NeoviaLogisticsAdapter` | `app/integrations/mocks/tracking_mock.py`<br>`app/integrations/adapters/dhl_adapter.py`<br>`app/integrations/adapters/neovia_adapter.py` |
| `ServiceProvider` | *None* | *None* | Missing (`contracts/service.py` & `mocks/service_mock.py`) |
| `DealerProvider` | *None* | *None* | Missing (`contracts/dealer.py` & `mocks/dealer_mock.py`) |

### 3.2 Analysis of Existing Adapters: `DHLExpressAdapter` & `NeoviaLogisticsAdapter`
Both adapters in `app/integrations/adapters/` inherit from `CarrierAdapter` in `carrier_base.py`.
- **Method Mismatch:**
  - `CarrierAdapter` defines `dispatch_shipment(request)` and `track_shipment(query)`.
  - `ShipmentProvider` defines `create_shipment(request)`.
  - `TrackingProvider` defines `get_tracking(query)`.
  - Therefore, `DHLExpressAdapter` and `NeoviaLogisticsAdapter` do **not** directly implement `ShipmentProvider` or `TrackingProvider` interfaces!
- **Wiring Mismatch:**
  - `shipment/service.py` imports only `TestShipmentProvider` and `TestTrackingProvider`.
  - The adapters are never imported or instantiated outside of `adapters/__init__.py`.
  - Neither adapter is wired to handle live calls.

### 3.3 Wiring & Dependency Injection Patterns
Inspection reveals that domain service modules instantiate mock providers directly:
1. `app/modules/availability/service.py` (line 90):
   ```python
   provider = TestInventoryProvider()
   raw_sources = provider.get_availability(query_dto)
   ```
2. `app/modules/order/service.py` (lines 40–41):
   ```python
   order_provider = TestOrderProvider()
   pricing_provider = TestPricingProvider()
   ```
3. `app/modules/fulfilment/service.py` (lines 34–35):
   ```python
   routing_provider = TestRoutingProvider()
   rate_provider = TestShippingRateProvider()
   ```
4. `app/modules/shipment/service.py` (lines 33–34):
   ```python
   shipment_provider = TestShipmentProvider()
   tracking_provider = TestTrackingProvider()
   ```

**Architectural Assessment:**
The direct hardcoded instantiation violates the requirement that providers should be configurable and swappable based on environment/credentials.

**Recommended Phase 9 DI Pattern:**
Follow the precedent established in `app/modules/intelligence/providers.py` (lines 222–230):
```python
def get_llm_provider() -> LLMProvider:
    if settings.GEMINI_API_KEY:
        return GeminiLLMProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    return DeterministicLLMProvider()
```
We should introduce a unified provider registry or provider factory (`app/integrations/factory.py`) with getters:
- `get_inventory_provider() -> InventoryProvider`
- `get_pricing_provider() -> PricingProvider`
- `get_order_provider() -> OrderProvider`
- `get_routing_provider() -> RoutingProvider`
- `get_shipping_rate_provider() -> ShippingRateProvider`
- `get_shipment_provider() -> ShipmentProvider`
- `get_tracking_provider() -> TrackingProvider`
- `get_service_provider() -> ServiceProvider`
- `get_dealer_provider() -> DealerProvider`

---

## 4. Neo4j AuraDB Data Layer & Provenance Modeling Deep-Dive

### 4.1 AuraDB Configuration & Lifecycle
- **File:** `backend/app/db/neo4j/connection.py`
- **Driver:** Process-level singleton with `max_connection_pool_size=50`, `connection_acquisition_timeout=60`, `max_connection_lifetime=3600`.
- **FastAPI Dependency:** `get_neo4j_session()` yields a session per request and cleans it up.
- **Context Manager:** `neo4j_transaction()` available for transactional blocks.

### 4.2 Entity Property & Relationship Model

#### A. Order (`:Order`)
- **Constraints & Indexes:**
  - Constraint: `Order_id` unique on `id`.
  - Index: `Order_fulfilmentRequestId` on `fulfilmentRequestId`.
- **Current Properties (persisted at `order/service.py:105`):**
  - `id`: `order-<uuid>`
  - `fulfilmentRequestId`: string
  - `partNumber`: string
  - `quantity`: int
  - `sourceId`: string
  - `destinationBranchId`: string
  - `unitPrice`: float or null
  - `currency`: string or null
  - `pricingStatus`: "NOT_AVAILABLE" | "CONFIRMED"
  - `status`: "CREATED" | "ACCEPTED" | "CANCELLED"
  - `provenance`: "INTERNAL_TEST_WORKFLOW"
  - `createdAt`: datetime()
  - `updatedAt`: datetime()
- **Missing Properties for Phase 9:**
  - `external_order_id`: External ERP/SAP/partner order reference.
  - `synced_at`: ISO datetime of external synchronization.
  - `synthetic`: boolean (`false` for canonical live orders; `true` for demo fallbacks).
  - `data_source`: string (e.g. `'HCME_SAP_ERP'` vs `'SYNTHETIC_DEMO'`).

#### B. Shipment (`:Shipment`)
- **Constraints & Indexes:**
  - Constraint: `Shipment_id` unique on `shipment_id`.
- **Current Properties (persisted at `shipment/service.py:116`):**
  - `shipment_id`: `ship-<uuid>`
  - `order_id`: string
  - `status`: "CREATED" | "DISPATCHED" | "IN_TRANSIT" | "DELIVERED" | "EXCEPTION" | "CANCELLED"
  - `carrier`: string
  - `tracking_number`: string
  - `origin`: string
  - `destination_branch`: string
  - `service_tier`: "STANDARD" | "EXPEDITED"
  - `eta`: string (YYYY-MM-DD)
  - `synthetic`: boolean (`true`)
  - `data_source`: `'SYNTHETIC_DEMO'`
  - `provenance`: `'INTERNAL_TEST_WORKFLOW'`
  - `createdAt`: datetime()
  - `updatedAt`: datetime()
  - `shipped_at`: datetime() (optional)
  - `delivered_at`: datetime() (optional)
- **Relationships:**
  - `(:Order)-[:HAS_SHIPMENT]->(:Shipment)`
  - `(:Shipment)-[:SHIPPED_TO]->(:DealerBranch)`
  - `(:Shipment)-[:HAS_EVENT]->(:ShipmentEvent)`
- **Requirements for Phase 9:**
  - When real carrier adapter dispatches: set `synthetic: false`, `data_source: 'DHL_EXPRESS'` or `'NEOVIA_TMS'`.
  - Store `external_shipment_id` and `synced_at`.

#### C. DealerBranch (`:DealerBranch`)
- **Constraints & Indexes:**
  - Constraint: `DealerBranch_dealer_id` unique on `dealer_id`.
- **Properties (from `docs/data/neo4j/import/nodes/dealers.cypher`):**
  - `dealer_id`: `DLR-001` through `DLR-182` (182 canonical European branches).
  - `dealer_name`, `address`, `city`, `country`, `state_province`, `sub_region`, `phone`, `email`, `website`, `product_categories`, `latitude`, `longitude`, `enquiry_link`, `region`.
  - `record_class`: `'REAL'`
  - `data_class`: `'OFFICIAL_SOURCE'`
  - `confidence`: `'HIGH'`
- **⚠️ CRITICAL REGRESSION TRAP on `DealerBranch` Provenance:**
  - `app/modules/intelligence/context.py` (lines 291–293) executes:
    ```python
    "real_dealer_nodes_with_synthetic_property_set": session.run(
        "MATCH (d:DealerBranch) WHERE d.synthetic IS NOT NULL RETURN count(d) AS c"
    ).single()["c"]
    ```
  - And `tests/test_operational_demo_data.py` (line 162) asserts:
    ```python
    assert stats["integrity_checks"]["real_dealer_nodes_with_synthetic_property_set"] == 0
    ```
  - If Phase 9 implementers blindly run Cypher to set `d.synthetic = false` across all existing `DealerBranch` nodes to "satisfy" requirement R3, **`test_operational_demo_data.py` will fail with count=182 instead of 0!**
  - **Resolution:** Leave canonical `DealerBranch` nodes with `synthetic` property unset (`NULL`), OR update the integrity check query in `context.py` to `WHERE d.synthetic = true` in coordination with tests.

#### D. ServiceJob (`:ServiceJob`)
- **Constraints & Indexes:**
  - Constraint: `ServiceJob_id` unique on `service_job_id`.
  - Indexes: `ServiceJob_orderId`, `ServiceJob_dealerId`, `ServiceJob_status`.
- **Current Properties (persisted at `service/service.py:94`):**
  - `service_job_id`: `SJ-<hex>`
  - `order_id`: string
  - `shipment_id`: string or null
  - `dealer_id`: string
  - `status`: "OPEN" | "PART_RECEIVED" | "IN_PROGRESS" | "PART_INSTALLED" | "COMPLETED" | "CANCELLED"
  - `service_type`: "PARTS_INSTALLATION"
  - `work_order_number`: `WO-EU-<hex>`
  - `notes`: string or null
  - `synthetic`: boolean (`true`)
  - `data_source`: `'SYNTHETIC_DEMO'`
  - `provenance`: `'INTERNAL_SERVICE_WORKFLOW'`
  - `createdAt`, `updatedAt`, `received_at`, `started_at`, `installed_at`, `completed_at`, `cancelled_at`
- **Relationships:**
  - `(:Order)-[:HAS_SERVICE_JOB]->(:ServiceJob)`
  - `(:Shipment)-[:HAS_SERVICE_JOB]->(:ServiceJob)`
  - `(:DealerBranch)-[:PERFORMS_SERVICE]->(:ServiceJob)`
  - `(:ServiceJob)-[:FOR_PART]->(:Part)`
  - `(:ServiceJob)-[:FOR_MACHINE]->(:Machine)`
  - `(:ServiceJob)-[:HAS_EVENT]->(:ServiceEvent)`
- **Requirements for Phase 9:**
  - Support `external_job_id` / `external_work_order_id` (from dealer DMS or ConSite).
  - Store `synced_at` datetime.
  - Tag real jobs with `synthetic: false`, `data_source: '<PROVIDER_NAME>'`.

---

## 5. Health Check Endpoints & `/api/v1/health/integrations`

### 5.1 Existing Endpoints
In `backend/app/api/v1/health.py`:
- `GET /api/v1/health/liveness`: Returns `{"status": "UP"}`. Used by container orchestrators.
- `GET /api/v1/health/readiness`: Queries Neo4j (`RETURN 1`) and calls `check_neo4j_health()`. Returns overall `status`, `database`, and `neo4j`.

### 5.2 Clean Integration Design for `/api/v1/health/integrations`
Add the endpoint directly to `backend/app/api/v1/health.py`:
```python
@router.get("/integrations")
def get_integrations_health(session=Depends(get_neo4j_session)):
    """
    Return authoritative connection and health status across all 9 operational domains.
    Strictly distinguishes CONNECTED (live API verified) vs SYNTHETIC_FALLBACK / NOT_CONNECTED.
    """
```
Because `health.py` is mounted in `main.py` with `prefix="/api/v1"`, this immediately resolves to `/api/v1/health/integrations`.

### 5.3 Proposed Integration Health Schema
```json
{
  "status": "UP",
  "environment": "development",
  "timestamp": "2026-09-23T11:00:00Z",
  "integrations": {
    "parts_master": {
      "domain": "Parts/Product Master",
      "provider": "Neo4j AuraDB Canonical Graph",
      "status": "CONNECTED",
      "data_source": "HCME_CANONICAL_IMPORT",
      "records_count": 84,
      "synthetic": false
    },
    "inventory": {
      "domain": "Inventory",
      "provider": "TestInventoryProvider",
      "status": "SYNTHETIC_FALLBACK",
      "data_source": "SYNTHETIC_DEMO",
      "synthetic": true,
      "details": "Authenticated dealer/depot DMS required"
    },
    "pricing": {
      "domain": "Pricing",
      "provider": "TestPricingProvider",
      "status": "NOT_CONNECTED",
      "data_source": "NONE",
      "synthetic": false,
      "details": "Pricing requires authenticated dealer account"
    },
    "order": {
      "domain": "Order / ERP",
      "provider": "TestOrderProvider",
      "status": "NOT_CONNECTED",
      "data_source": "INTERNAL_TEST_WORKFLOW",
      "synthetic": true,
      "details": "SAP/D365 ERP access required"
    },
    "routing": {
      "domain": "Allocation & Routing",
      "provider": "TestRoutingProvider",
      "status": "SYNTHETIC_FALLBACK",
      "data_source": "SYNTHETIC_DEMO",
      "synthetic": true
    },
    "shipping_rate": {
      "domain": "Shipping Rates",
      "provider": "TestShippingRateProvider",
      "status": "SYNTHETIC_FALLBACK",
      "data_source": "SYNTHETIC_DEMO",
      "synthetic": true
    },
    "shipment": {
      "domain": "Shipment / TMS",
      "provider": "NeoviaLogisticsAdapter | DHLExpressAdapter | TestShipmentProvider",
      "status": "CONNECTED",
      "data_source": "DHL_EXPRESS",
      "synthetic": false
    },
    "carrier_tracking": {
      "domain": "Carrier Tracking",
      "provider": "DHLExpressAdapter | TestTrackingProvider",
      "status": "CONNECTED",
      "data_source": "DHL_EXPRESS",
      "synthetic": false
    },
    "service": {
      "domain": "Dealer & Service",
      "provider": "TestServiceProvider | InternalServiceWorkflow",
      "status": "SYNTHETIC_FALLBACK",
      "data_source": "SYNTHETIC_DEMO",
      "synthetic": true,
      "details": "ConSite / Dealer DMS integration pending"
    }
  }
}
```

---

## 6. Gap Matrix & Actionable Roadmap for Phase 9 Implementers

| Domain | Provider Interface | Abstract File Exists? | Mock File Exists? | Real Adapter Exists? | Service Wiring Status | Phase 9 Implementation Required |
|---|---|---|---|---|---|---|
| **1. Parts Master** | N/A (Core Graph) | N/A | N/A | Yes (AuraDB) | Direct Cypher | Real canonical data already connected in Neo4j. Maintain European boundary. |
| **2. Inventory** | `InventoryProvider` | Yes (`contracts/inventory.py`) | Yes (`mocks/inventory_mock.py`) | No | Hardcoded `TestInventoryProvider()` | Create factory `get_inventory_provider()`. Preserve honest fallback. |
| **3. Pricing** | `PricingProvider` | Yes (`contracts/pricing.py`) | Yes (`mocks/pricing_mock.py`) | No | Hardcoded `TestPricingProvider()` | Create factory `get_pricing_provider()`. Preserve honest `NOT_AVAILABLE`. |
| **4. Order / ERP** | `OrderProvider` | Yes (`contracts/order.py`) | Yes (`mocks/order_mock.py`) | No | Hardcoded `TestOrderProvider()` | Create factory `get_order_provider()`. Add `external_order_id`, `synced_at` to Neo4j. |
| **5. Routing** | `RoutingProvider` | Yes (`contracts/routing.py`) | Yes (`mocks/routing_mock.py`) | No | Hardcoded `TestRoutingProvider()` | Create factory `get_routing_provider()`. |
| **6. Shipping Rate**| `ShippingRateProvider`| Yes (`contracts/shipping_rate.py`)| Yes (`mocks/shipping_rate_mock.py`)| No | Hardcoded `TestShippingRateProvider()` | Create factory `get_shipping_rate_provider()`. |
| **7. Shipment** | `ShipmentProvider` | Yes (`contracts/shipment.py`) | Yes (`mocks/shipment_mock.py`) | Yes (`DHL`, `Neovia` in adapters/) | Hardcoded `TestShipmentProvider()` | Align `DHLExpressAdapter`/`NeoviaLogisticsAdapter` with `ShipmentProvider`. Wire via factory. Add `external_shipment_id`, `synced_at`. |
| **8. Tracking** | `TrackingProvider` | Yes (`contracts/tracking.py`) | Yes (`mocks/tracking_mock.py`) | Yes (`DHL`, `Neovia` in adapters/) | Hardcoded `TestTrackingProvider()` | Align adapters with `TrackingProvider`. Wire via factory. Update tracking polling/sync into Neo4j. |
| **9. Service** | `ServiceProvider` | **No** (Needs `contracts/service.py`) | **No** (Needs `mocks/service_mock.py`) | No | Inline in `service/service.py` | Create `contracts/service.py`, `mocks/service_mock.py`. Wire into `service/service.py`. Add `external_job_id`, `synced_at`. |
| **10. Dealer** | `DealerProvider` | **No** (Needs `contracts/dealer.py`) | **No** (Needs `mocks/dealer_mock.py`) | No | Static Neo4j nodes | Create `contracts/dealer.py`, `mocks/dealer_mock.py`. Beware `context.py` dealer synthetic check! |

---

## 7. Concrete Recommendations for Phase 9 Implementation

1. **Create Provider Registry / Factory:**
   Create `backend/app/integrations/registry.py` (or `factory.py`) with factory functions for all 9 providers. Refactor `availability/service.py`, `order/service.py`, `fulfilment/service.py`, and `shipment/service.py` to obtain provider instances via these factory functions instead of direct mock instantiation.
2. **Standardize Carrier Adapters:**
   Refactor `DHLExpressAdapter` and `NeoviaLogisticsAdapter` to directly implement `ShipmentProvider` and `TrackingProvider` (or provide adapter wrappers), ensuring method signatures match `create_shipment` and `get_tracking`.
3. **Formalize ServiceProvider & DealerProvider Contracts:**
   Create `backend/app/integrations/contracts/service.py` and `backend/app/integrations/contracts/dealer.py`, along with corresponding mock implementations.
4. **Enrich AuraDB Cypher Queries:**
   - Update `app/modules/order/service.py` Cypher queries to store `external_order_id`, `synced_at`, `synthetic`, and `data_source`.
   - Update `app/modules/shipment/service.py` Cypher queries to store `external_shipment_id`, `synced_at`, and set `synthetic: false` when dispatched through real carrier adapters.
   - Update `app/modules/service/service.py` Cypher queries to store `external_job_id` and `synced_at`.
   - **Do not modify `synthetic` on canonical `DealerBranch` nodes** without updating `test_operational_demo_data.py:162` and `context.py:291`.
5. **Implement `/api/v1/health/integrations`:**
   Add the `@router.get("/integrations")` route in `backend/app/api/v1/health.py` returning the structured 9-domain health status.
