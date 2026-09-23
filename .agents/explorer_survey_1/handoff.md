# Explorer 1 Handoff Report: Architecture & Existing Provider Contracts

**Agent:** Explorer 1 (Architecture & Existing Provider Contracts Investigator)  
**Parent Agent:** `64b2e471-00ec-4dd4-bc98-bd3df8f8b6e3` (parent)  
**Working Directory:** `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_1`  
**Date:** 2026-09-23  

---

## 1. Observation

### 1.1 Provider Contracts & File Structure
- Abstract contracts defined in `backend/app/integrations/contracts/`:
  - `inventory.py`: `InventoryProvider(ABC)` with `get_availability(query: SourceAvailabilityQuery) -> List[SourceInventoryItem]`
  - `pricing.py`: `PricingProvider(ABC)` with `get_price(query: PricingQuery) -> PriceQuote`
  - `order.py`: `OrderProvider(ABC)` with `submit_order(submission: OrderSubmission) -> OrderSubmissionResult`
  - `routing.py`: `RoutingProvider(ABC)` with `find_routes(query: RouteQuery) -> List[RouteOption]`
  - `shipping_rate.py`: `ShippingRateProvider(ABC)` with `get_rate(query: ShippingRateQuery) -> Optional[ShippingRate]`
  - `shipment.py`: `ShipmentProvider(ABC)` with `create_shipment(request: ShipmentCreationRequest) -> ShipmentCreationResult`
  - `tracking.py`: `TrackingProvider(ABC)` with `get_tracking(query: TrackingQuery) -> TrackingResult`
- Grep search for `ServiceProvider` and `DealerProvider` in `backend/` returned **0 results**. Neither interface exists as code in `backend/app/integrations/contracts/`, despite being listed in `docs/architecture/INTEGRATION_ARCHITECTURE.md` and `ORIGINAL_REQUEST.md`.

### 1.2 Mocks & Existing Adapters
- Seven test provider mocks exist in `backend/app/integrations/mocks/`:
  `inventory_mock.py` (`TestInventoryProvider`), `pricing_mock.py` (`TestPricingProvider`), `order_mock.py` (`TestOrderProvider`), `routing_mock.py` (`TestRoutingProvider`), `shipping_rate_mock.py` (`TestShippingRateProvider`), `shipment_mock.py` (`TestShipmentProvider`), and `tracking_mock.py` (`TestTrackingProvider`).
- Two adapter files exist in `backend/app/integrations/adapters/`:
  `dhl_adapter.py` (`DHLExpressAdapter`) and `neovia_adapter.py` (`NeoviaLogisticsAdapter`). Both inherit from `CarrierAdapter` in `carrier_base.py`.
- `CarrierAdapter` defines `dispatch_shipment()` and `track_shipment()`, which differs from `ShipmentProvider.create_shipment()` and `TrackingProvider.get_tracking()`.
- Neither adapter is imported or wired into `backend/app/modules/shipment/service.py`.

### 1.3 Service Hardcoding & Absence of Dependency Injection
- `backend/app/modules/availability/service.py:90`:
  `provider = TestInventoryProvider()`
- `backend/app/modules/order/service.py:40-41`:
  `order_provider = TestOrderProvider()`
  `pricing_provider = TestPricingProvider()`
- `backend/app/modules/fulfilment/service.py:34-35`:
  `routing_provider = TestRoutingProvider()`
  `rate_provider = TestShippingRateProvider()`
- `backend/app/modules/shipment/service.py:33-34`:
  `shipment_provider = TestShipmentProvider()`
  `tracking_provider = TestTrackingProvider()`
- There is no central provider factory or dependency injection mechanism in place for external service integrations.

### 1.4 Neo4j AuraDB Data Model & Provenance
- `schema.py` establishes constraints on all core nodes (`FulfilmentRequest`, `FulfilmentOption`, `InventoryCache`, `InventoryLedger`, `Allocation`, `Order`, `AuditRecord`, `IdempotencyRecord`, `PartsInquiry`, `Customer`, `Depot`, `Supplier`, `CatalogEntry`, `InventorySnapshot`, `Shipment`, `CustomsContext`, `DealerBranch`, `ServiceJob`, `ServiceEvent`, `ComplianceRequirement`).
- `Order` node creation (`backend/app/modules/order/service.py:105-120`) currently writes: `id`, `fulfilmentRequestId`, `partNumber`, `quantity`, `sourceId`, `destinationBranchId`, `unitPrice`, `currency`, `pricingStatus`, `status`, `provenance: 'INTERNAL_TEST_WORKFLOW'`, `createdAt`, `updatedAt`. It does NOT store `external_order_id`, `synced_at`, `synthetic`, or `data_source`.
- `Shipment` node creation (`backend/app/modules/shipment/service.py:116-133`) currently writes `synthetic: true`, `data_source: 'SYNTHETIC_DEMO'`, `provenance: 'INTERNAL_TEST_WORKFLOW'`. It does NOT store `external_shipment_id` or `synced_at`.
- `DealerBranch` nodes (182 canonical European branches) were imported from `docs/data/neo4j/import/nodes/dealers.cypher`. In `backend/app/modules/intelligence/context.py:291-293`, the integrity check query is:
  `"MATCH (d:DealerBranch) WHERE d.synthetic IS NOT NULL RETURN count(d) AS c"`
  and `tests/test_operational_demo_data.py:162` asserts this count is strictly `0`.
- `ServiceJob` nodes (`backend/app/modules/service/service.py:94-110`) write `synthetic: true`, `data_source: 'SYNTHETIC_DEMO'`, `provenance: 'INTERNAL_SERVICE_WORKFLOW'`. It does NOT store `external_job_id` or `synced_at`.

### 1.5 Health Endpoints
- `backend/app/api/v1/health.py` defines `router = APIRouter(prefix="/health", tags=["Health"])` with `/liveness` and `/readiness`.
- `backend/app/main.py:72` mounts `app.include_router(health_router, prefix="/api/v1")`.

---

## 2. Logic Chain

1. **Contract Completeness:**
   From Observation 1.1, 7 of the 9 required Phase 9 provider contracts exist in `backend/app/integrations/contracts/`. `ServiceProvider` and `DealerProvider` are completely absent in code. Therefore, before Phase 9 adapters can be implemented for Service and Dealer, formal abstract contracts (`contracts/service.py` and `contracts/dealer.py`) must be created.
2. **Adapter Usability:**
   From Observation 1.2, although `DHLExpressAdapter` and `NeoviaLogisticsAdapter` exist, their method signatures (`dispatch_shipment`, `track_shipment`) do not match the `ShipmentProvider` (`create_shipment`) and `TrackingProvider` (`get_tracking`) abstract interfaces, and they are not imported anywhere in the service layer. Therefore, adapter standardization and signature alignment are required before live shipments can be routed through them.
3. **Dependency Injection Architecture:**
   From Observation 1.3, domain services currently hardcode instantiations of mock providers. Direct instantiation prevents runtime switching between live European APIs and test fallbacks. To achieve swappability without rewriting domain services, a factory/registry pattern (modeled after `app/modules/intelligence/providers.py:222-230`) must be introduced.
4. **Provenance & Graph Integrity Protection:**
   From Observation 1.4, Phase 9 requires external IDs, sync timestamps, and source system provenance (`synthetic = false` on canonical nodes, `synthetic = true` on demo fallbacks). However, because `test_operational_demo_data.py:162` strictly asserts that `count(d:DealerBranch WHERE d.synthetic IS NOT NULL) == 0`, implementers must **not** set `synthetic = false` on existing canonical `DealerBranch` nodes without updating the test and `context.py`.
5. **Health Routing Integration:**
   From Observation 1.5, `health.py` is mounted at prefix `/health` within `/api/v1`. Adding `@router.get("/integrations")` inside `health.py` immediately exposes `/api/v1/health/integrations` with zero URL route configuration overhead.

---

## 3. Caveats

1. **Read-Only Scope:** No backend source code, schema migrations, or test files were modified during this investigation.
2. **Live AuraDB Verification:** Terminal command execution of `pytest` was not run due to read-only tool boundaries; test counts and assertions were verified directly via static code analysis of `backend/tests/` (98 tests across 9 test files).
3. **External API Verification:** Live third-party credentials (e.g. `DHL_API_KEY`, `NEOVIA_API_KEY`) were not tested against live carrier networks during this architectural survey; credential availability is evaluated by Explorer 2 / integration inventory.

---

## 4. Conclusion

The backend codebase is in a stable, well-structured state following Phase 8, but possesses clear architectural gaps that Phase 9 must resolve:
1. **Define Missing Contracts:** Create `contracts/service.py` (`ServiceProvider`) and `contracts/dealer.py` (`DealerProvider`) with matching test mocks.
2. **Introduce Provider Factory:** Create `backend/app/integrations/factory.py` (or `registry.py`) providing swappable resolution of all 9 providers based on environment/credentials with graceful fallback to `TestProvider`.
3. **Align Carrier Adapters:** Normalize `DHLExpressAdapter` and `NeoviaLogisticsAdapter` to implement `ShipmentProvider` and `TrackingProvider`.
4. **Enrich AuraDB Cypher Queries:** Add `external_order_id`, `external_shipment_id`, `external_job_id`, `synced_at`, and `data_source` to `Order`, `Shipment`, and `ServiceJob`. Keep `DealerBranch.synthetic` NULL to preserve `test_operational_demo_data.py:162`.
5. **Implement `/api/v1/health/integrations`:** Mount `@router.get("/integrations")` in `backend/app/api/v1/health.py` reporting domain statuses across all 9 domains.

---

## 5. Verification Method

To verify these findings independently:
1. **Contract Existence Inspection:**
   Inspect files in `backend/app/integrations/contracts/` using `find_by_name` or `list_dir`. Confirm 7 contracts present, `service.py` and `dealer.py` absent.
2. **Service Instantiation Inspection:**
   Run `grep_search` on `backend/app/modules/` for `Test.*Provider` to confirm hardcoded mock instantiations in `availability/service.py:90`, `order/service.py:40`, `fulfilment/service.py:34`, and `shipment/service.py:33`.
3. **Adapter Signature Inspection:**
   View `backend/app/integrations/adapters/carrier_base.py` and compare against `backend/app/integrations/contracts/shipment.py`. Confirm method name mismatch (`dispatch_shipment` vs `create_shipment`).
4. **DealerBranch Test Verification:**
   View `backend/app/modules/intelligence/context.py:291-293` and `backend/tests/test_operational_demo_data.py:156-163` to confirm the constraint `d.synthetic IS NOT NULL == 0`.
5. **Health Router Path Verification:**
   View `backend/app/api/v1/health.py` and `backend/app/main.py:72` to confirm path resolution to `/api/v1/health/integrations`.
