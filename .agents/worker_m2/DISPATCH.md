## 2026-09-23T11:21:25Z
You are Worker M2: Provider Contracts, Adapters, Factory & Health API Implementer for Phase 9 Real Integrations.
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\worker_m2
Original request path: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & File Ownership:
You own implementation across:
- backend/app/integrations/contracts/ (service.py, dealer.py)
- backend/app/integrations/mocks/ (service_mock.py, dealer_mock.py)
- backend/app/integrations/adapters/ (osrm_adapter.py, hitachi_dealer_adapter.py, dhl_adapter.py, postnl_adapter.py)
- backend/app/integrations/factory.py
- backend/app/api/v1/health.py (implement /api/v1/health/integrations)
- backend/app/modules/ (wire factory into availability/service.py, order/service.py, fulfilment/service.py, shipment/service.py, service/service.py)

Detailed Technical Instructions:
1. Read ORIGINAL_REQUEST.md and docs/research/PHASE_9_INTEGRATION_INVENTORY.md.
2. Read Explorer 1's architectural analysis in c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_survey_1\analysis.md.
3. Contracts & Mocks:
   - Create backend/app/integrations/contracts/service.py (ServiceProvider ABC with schedule_service and get_service_status).
   - Create backend/app/integrations/contracts/dealer.py (DealerProvider ABC with fetch_dealer_network and get_dealer_by_id).
   - Create backend/app/integrations/mocks/service_mock.py (TestServiceProvider) and dealer_mock.py (TestDealerProvider).
4. Concrete Adapters:
   - Implement backend/app/integrations/adapters/osrm_adapter.py (OSRMRouteAdapter implementing RoutingProvider; uses http://router.project-osrm.org/route/v1/driving/ with 2s timeout and Haversine fallback; never crashes offline).
   - Implement backend/app/integrations/adapters/hitachi_dealer_adapter.py (HitachiDealerFeedAdapter implementing DealerProvider; loads public feed SRC-049 or queries AuraDB DealerBranch cache).
   - Update backend/app/integrations/adapters/dhl_adapter.py (DHLExpressAdapter implementing ShipmentProvider.create_shipment and TrackingProvider.get_tracking).
   - Implement backend/app/integrations/adapters/postnl_adapter.py (PostNLAdapter implementing ShipmentProvider and TrackingProvider).
5. Provider Factory:
   - Create backend/app/integrations/factory.py exposing get_inventory_provider(), get_pricing_provider(), get_order_provider(), get_routing_provider(), get_shipping_rate_provider(), get_shipment_provider(), get_tracking_provider(), get_service_provider(), get_dealer_provider(). Resolve based on environment variables with clean fallback to TestProvider mocks.
6. Domain Service Wiring:
   - Wire availability/service.py, order/service.py, fulfilment/service.py, shipment/service.py, service/service.py to obtain providers from factory.
7. Neo4j AuraDB Provenance Synchronization:
   - Ensure Order creation/queries store external_order_id, synced_at, data_source.
   - Ensure Shipment creation/queries store external_shipment_id, synced_at, data_source.
   - Ensure ServiceJob creation/queries store external_job_id, synced_at, data_source.
   - CRUCIAL INVARIANT: Keep DealerBranch.synthetic as NULL on canonical nodes so test_operational_demo_data.py:162 (asserting count(d:DealerBranch WHERE d.synthetic IS NOT NULL) == 0) continues to pass!
8. Health Endpoint:
   - Implement GET /api/v1/health/integrations in backend/app/api/v1/health.py returning health status, latency, provider class, and classification across all 9 domains per Section 7 of PHASE_9_INTEGRATION_INVENTORY.md.
9. Verification:
   - Run python -m pytest tests/ to ensure ALL 98 baseline tests pass with zero regressions.
   - Run python -m pytest tests/test_phase6_allocation_order.py to ensure concurrency tests pass.
10. Maintain progress.md in your working directory with 'Last visited: [timestamp]'.
11. Write self-contained handoff.md in c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\worker_m2\handoff.md documenting all modified files, test outputs, and verification methods.
12. Send a message to parent when completed.
