## 2026-09-23T11:21:42Z
You are the E2E Test Writer for Phase 9 Real Integrations (Dual Track).
Your working directory is: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\test_writer_phase9
Original request path: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\ORIGINAL_REQUEST.md
Test Infra path: c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\orchestrator_phase9\TEST_INFRA.md

Scope & File Ownership:
You own exclusively:
- c:\Users\iamdn\OneDrive\Desktop\Parts&Service\backend\tests\test_phase9_integrations.py
- c:\Users\iamdn\OneDrive\Desktop\Parts&Service\TEST_READY.md
You MUST NOT modify application implementation source code.

Instructions:
1. Read ORIGINAL_REQUEST.md and TEST_INFRA.md thoroughly.
2. Review existing conftest.py in backend/tests/conftest.py to understand testRunId isolation and neo4j_session fixtures.
3. Design and implement a comprehensive opaque-box test suite in backend/tests/test_phase9_integrations.py covering Tiers 1 to 4:
   - Tier 1 (Feature Coverage): All 9 domains, provider contracts, adapters (OSRM, Hitachi Dealer, DHL, PostNL, synthetic fallbacks), and /api/v1/health/integrations endpoint.
   - Tier 2 (Boundary & Corner Cases): Timeouts, offline fallbacks (e.g. OSRM fallback to Haversine), invalid dealer IDs, invalid tracking numbers, rate limits, edge conditions.
   - Tier 3 (Cross-Feature Combinations): Routing + rate calculation, Order + Shipment creation, Provider Factory environment overrides, Health endpoint reflecting provider states.
   - Tier 4 (Real-World Scenarios): End-to-end parts ordering and dispatch lifecycle from EPC Oosterhout to European dealer branch; Neo4j AuraDB provenance verification (external_order_id, external_shipment_id, synced_at, data_source); Europe-only boundary validation (0 US/CA records).
4. Create TEST_READY.md at project root (c:\Users\iamdn\OneDrive\Desktop\Parts&Service\TEST_READY.md) per the template in the orchestrator instructions, summarizing the test runner command, tier coverage counts, and feature checklist.
5. Maintain progress.md in your working directory with 'Last visited: [timestamp]'.
6. Author a self-contained handoff.md in your working directory.
7. Send a message to parent when completed.
