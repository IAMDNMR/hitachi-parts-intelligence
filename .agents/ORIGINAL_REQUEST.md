# Original User Request

## 2026-09-23T10:59:36Z

HCME Europe OEM Parts & Services Platform — Phase 9: Real Integrations. Replace prototype NOT_CONNECTED and test-provider boundaries with verified real European integrations where accessible, while preserving the existing Neo4j AuraDB runtime graph core and Phase 0–8 verified state.

Working directory: c:\Users\iamdn\OneDrive\Desktop\Parts&Service
Integrity mode: development

## Requirements

### R1. Integration Discovery & Inventory
Audit existing HCME Europe documentation, partner interfaces, and external European logistics/telematics/carrier services. Create docs/research/PHASE_9_INTEGRATION_INVENTORY.md classifying all 9 operational domains (Parts/Product Master, Inventory, Pricing, Dealer, Order/ERP, Allocation, Shipment/TMS, Carrier Tracking, Service) with authoritative classifications: CONNECTED, ACCESS AVAILABLE — READY TO CONNECT, AUTHENTICATED / DEALER ACCESS REQUIRED, PARTNER / COMMERCIAL ACCESS REQUIRED, API NOT PUBLICLY DOCUMENTED, NOT FOUND, NOT APPLICABLE, or SYNTHETIC FALLBACK.

### R2. Adapter Implementation Behind Provider Contracts
Implement concrete adapters behind existing provider contracts (InventoryProvider, PricingProvider, OrderProvider, RoutingProvider, ShippingRateProvider, ShipmentProvider, TrackingProvider, ServiceProvider, DealerProvider). Connect verified, accessible real European APIs/sandboxes with typed request/response models, secure authentication, timeouts, structured logging without credential leakage, external ID mapping, and synchronization timestamps into Neo4j AuraDB.

### R3. Strict Architecture & Europe-Only Boundary Protection
Preserve the protected architecture: React + TypeScript + Vite frontend, Python FastAPI backend, and Neo4j AuraDB as the sole single source of runtime truth (zero PostgreSQL, SQLite, or in-memory runtime databases). Enforce European scope (0 US dealer/carrier/operational records). Maintain explicit synthetic = true and data_source = 'SYNTHETIC_DEMO' boundary tagging on demo fallback records, with synthetic = false on all real canonical nodes.

### R4. Verification, Health Status & Full Non-Regression
Implement an API-backed integration health and status endpoint (/api/v1/health/integrations). Ensure 100% test pass rate across the full test suite (baseline 98 backend tests + Phase 9 integration tests, Phase 6 allocation concurrency x 3 runs, 82 frontend unit tests, TypeScript typecheck, production build, live AuraDB graph integrity, and headless browser console sweep). Document findings in docs/research/PHASE_9_IMPLEMENTATION_REPORT.md and docs/research/PHASE_9_FINAL_CLOSURE_REPORT.md.

## Acceptance Criteria

### Integration Discovery & Inventory
- [ ] docs/research/PHASE_9_INTEGRATION_INVENTORY.md created covering all 9 integration domains with official ownership, endpoints, authentication requirements, and status classifications.
- [ ] Strict distinction maintained: No integration marked CONNECTED without an actual verified live request execution or approved sandbox response.

### Provider Adapters & AuraDB Synchronization
- [ ] Real adapters implemented behind abstract provider contracts without leaking vendor-specific logic into domain services.
- [ ] External IDs, synchronization timestamps, and source system provenance stored on Neo4j AuraDB nodes (Order, Shipment, DealerBranch, ServiceJob).
- [ ] TestProvider synthetic fallbacks preserved for authenticated/dealer-gated domains without fabricating live connections.

### Non-Regression & Quality Assurance
- [ ] Full backend pytest suite passes with zero regressions (>= 98 tests passing).
- [ ] Phase 6 allocation concurrency stress tests pass (15/15 x 3 runs with 0 deadlocks).
- [ ] Frontend unit tests pass (82/82) and TypeScript compilation (tsc --noEmit) passes with 0 errors.
- [ ] Vite production build succeeds (npm run build).
- [ ] Live Neo4j AuraDB integrity check script passes with 0 orphan events, 0 duplicate canonical records, 0 non-EU records, and 0 real nodes marked synthetic.
- [ ] Headless browser console sweep passes with 0 console errors and 0 page errors.
- [ ] Complete implementation and final closure reports written to docs/research/.
