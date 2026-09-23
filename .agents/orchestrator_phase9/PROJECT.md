# Project: HCME Europe OEM Parts & Services Platform — Phase 9: Real Integrations

## Architecture
- **Runtime Core**: Python FastAPI backend (`backend/app`), React + TypeScript + Vite frontend (`frontend/`), Neo4j AuraDB as sole single source of runtime truth.
- **Provider Architecture**:
  - `backend/app/integrations/contracts/`: 9 abstract provider contracts (`InventoryProvider`, `PricingProvider`, `OrderProvider`, `RoutingProvider`, `ShippingRateProvider`, `ShipmentProvider`, `TrackingProvider`, `ServiceProvider`, `DealerProvider`).
  - `backend/app/integrations/factory.py`: Provider factory resolving concrete adapters vs synthetic test fallbacks based on environment configuration.
  - `backend/app/integrations/adapters/`: Concrete adapters (`HitachiDealerFeedAdapter`, `OSRMRouteAdapter`, `DHLExpressAdapter`, `PostNLAdapter`).
  - `backend/app/integrations/mocks/`: Synthetic fallback adapters (`TestInventoryProvider`, `TestPricingProvider`, `TestOrderProvider`, `TestRoutingProvider`, `TestShippingRateProvider`, `TestShipmentProvider`, `TestTrackingProvider`, `TestServiceProvider`, `TestDealerProvider`).
- **Graph Provenance & Invariants**:
  - Neo4j AuraDB stores `external_order_id`, `external_shipment_id`, `external_job_id`, `synced_at`, `data_source` on `Order`, `Shipment`, and `ServiceJob`.
  - Canonical `DealerBranch` nodes (182 branches across 30 European countries) retain `synthetic = NULL` to satisfy `test_operational_demo_data.py:162`.
  - Zero non-EU records (0 US/CA records).
- **Health & Monitoring**:
  - `/api/v1/health/integrations` reporting operational statuses across all 9 domains.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Integration Discovery & Audit | Comprehensive inventory covering all 9 operational domains | M1 | ORIGINAL_REQUEST §R1 |
| F2 | Authoritative Classifications | Strict 8-tier status classification (No CONNECTED without live proof) | M1 | ORIGINAL_REQUEST §R1 |
| F3 | Provider Contracts Completion | Define ServiceProvider and DealerProvider contracts in backend | M2 | ORIGINAL_REQUEST §R2 |
| F4 | Provider Factory & Registry | Central factory resolving adapters with environment fallback | M2 | ORIGINAL_REQUEST §R2 |
| F5 | Concrete European Adapters | OSRM road routing, Hitachi dealer locator, DHL Express & PostNL | M2 | ORIGINAL_REQUEST §R2 |
| F6 | Synthetic Fallback Preservation | Preserve TestProviders for gated domains without false claims | M2 | ORIGINAL_REQUEST §R2 |
| F7 | AuraDB Provenance Sync | External IDs, synced_at, data_source on Order, Shipment, ServiceJob | M3 | ORIGINAL_REQUEST §R2, §R3 |
| F8 | Integration Health Endpoint | /api/v1/health/integrations endpoint reporting all 9 domains | M3 | ORIGINAL_REQUEST §R4 |
| F9 | E2E Testing Suite (Tiers 1-4) | Opaque-box requirements-driven test suite with TEST_READY.md | M4 | Project Pattern Dual Track |
| F10 | Full Non-Regression Verification | 98 backend tests + Phase 9, 15/15x3 concurrency, 82 frontend tests, tsc, vite, AuraDB integrity, browser sweep | M5 | ORIGINAL_REQUEST §R4 |
| F11 | Adversarial Hardening (Tier 5) | White-box stress testing and gap elimination | M5 | Project Pattern Final Milestone |
| F12 | Phase 9 Closure Documentation | PHASE_9_INTEGRATION_INVENTORY.md, PHASE_9_IMPLEMENTATION_REPORT.md, PHASE_9_FINAL_CLOSURE_REPORT.md | M6 | ORIGINAL_REQUEST §R1, §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Integration Inventory Documentation | Author `docs/research/PHASE_9_INTEGRATION_INVENTORY.md` covering all 9 domains | Survey | DONE |
| M2 | Provider Contracts & Adapters | Implement missing contracts (`ServiceProvider`, `DealerProvider`), `factory.py`, concrete adapters (`OSRMRouteAdapter`, `HitachiDealerFeedAdapter`, `DHLExpressAdapter`, `PostNLAdapter`), and wire into domain services | M1 | PLANNED |
| M3 | AuraDB Provenance & Health API | Enrich Neo4j queries for external IDs, timestamps, and implement `/api/v1/health/integrations` | M2 | PLANNED |
| M4 | E2E Test Suite (Dual Track) | Implement requirements-driven test suite (Tiers 1-4) and publish `TEST_READY.md` | M1 | PLANNED |
| M5 | Verification & Non-Regression | Run full verification suite (baseline 98 + Phase 9 backend tests, Phase 6 concurrency 15/15 x 3, 82 frontend tests, tsc, vite build, live AuraDB graph integrity, headless browser sweep) + Adversarial hardening | M3, M4 | PLANNED |
| M6 | Final Closure & Sentinel Report | Author `PHASE_9_IMPLEMENTATION_REPORT.md`, `PHASE_9_FINAL_CLOSURE_REPORT.md`, and notify Sentinel | M5 | PLANNED |

## Interface Contracts
### `ServiceProvider` (`backend/app/integrations/contracts/service.py`)
- `schedule_service(request: ServiceJobRequest) -> ServiceJobResult`
- `get_service_status(external_job_id: str) -> ServiceStatusResult`

### `DealerProvider` (`backend/app/integrations/contracts/dealer.py`)
- `fetch_dealer_network() -> List[DealerBranchDTO]`
- `get_dealer_by_id(dealer_id: str) -> Optional[DealerBranchDTO]`

### `ProviderFactory` (`backend/app/integrations/factory.py`)
- `get_inventory_provider() -> InventoryProvider`
- `get_pricing_provider() -> PricingProvider`
- `get_order_provider() -> OrderProvider`
- `get_routing_provider() -> RoutingProvider`
- `get_shipping_rate_provider() -> ShippingRateProvider`
- `get_shipment_provider() -> ShipmentProvider`
- `get_tracking_provider() -> TrackingProvider`
- `get_service_provider() -> ServiceProvider`
- `get_dealer_provider() -> DealerProvider`

### `HealthEndpoint` (`/api/v1/health/integrations`)
- Output Schema:
  ```json
  {
    "status": "HEALTHY",
    "timestamp": "ISO-8601",
    "domains": {
      "parts_master": { "classification": "...", "provider": "...", "status": "..." },
      "inventory": { "classification": "...", "provider": "...", "status": "..." },
      "pricing": { "classification": "...", "provider": "...", "status": "..." },
      "dealer": { "classification": "...", "provider": "...", "status": "..." },
      "order_erp": { "classification": "...", "provider": "...", "status": "..." },
      "allocation": { "classification": "...", "provider": "...", "status": "..." },
      "shipment_tms": { "classification": "...", "provider": "...", "status": "..." },
      "carrier_tracking": { "classification": "...", "provider": "...", "status": "..." },
      "service": { "classification": "...", "provider": "...", "status": "..." }
    }
  }
  ```

## Code Layout
- `backend/app/integrations/contracts/`: Abstract provider interfaces
- `backend/app/integrations/adapters/`: Concrete external adapters
- `backend/app/integrations/mocks/`: Synthetic demo fallbacks
- `backend/app/integrations/factory.py`: Central dependency factory
- `backend/app/api/v1/health.py`: Integration health endpoint
- `backend/app/modules/`: Domain services (availability, order, fulfilment, shipment, service, dealer)
- `backend/tests/`: Pytest suite
- `frontend/src/`: React frontend source
- `frontend/tests/`: Frontend native test suite
- `docs/research/`: Research & closure reports
- `docs/data/neo4j/scripts/`: Live graph verification scripts
