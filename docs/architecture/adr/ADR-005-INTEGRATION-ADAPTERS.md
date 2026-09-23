# ADR-005 — Integration Adapter Strategy

## Context

Every external HCME/dealer/logistics system the process might eventually need (inventory, pricing, order, routing, shipping rate, shipment, tracking, service, dealer master) is UNKNOWN or unconfirmed (Phase 1 `HCME_CONFIRMED_VS_UNKNOWN.md`). Principle 6 forbids the frontend calling external systems directly; principle 12 requires failure handling for every important external dependency; principle 14–16 forbid inventing systems, APIs, or integrations.

## Decision

Every external dependency is reached through a **named adapter interface** (`InventoryProvider`, `PricingProvider`, `OrderProvider`, `RoutingProvider`, `ShippingRateProvider`, `ShipmentProvider`, `TrackingProvider`, `ServiceProvider`, `DealerProvider` — `INTEGRATION_ARCHITECTURE.md`), owned exclusively by the Integrations backend module. No other module, and no frontend code, calls an external system directly. Until a real implementation is confirmed and approved, only a mock/test implementation is registered, and only in non-production environments.

## Reason

- This is the only way to satisfy "do not invent APIs/ERP/WMS/carrier integrations" while still designing a *complete* architecture: the adapter interface is the contract the business logic needs, independent of which (if any) real system eventually fulfils it.
- Centralizing every external call through one module makes principle 6 (never from the browser) and principle 12 (failure handling) enforceable in one place rather than scattered across ten business modules.
- Keeps a real integration, once approved, a configuration/implementation change rather than a business-logic or API-contract change (`INTEGRATION_ARCHITECTURE.md` §4).

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Business modules call external systems directly once confirmed | Violates principle 6/8 and makes failure handling inconsistent across modules; also makes it much harder to guarantee a mock is never mistaken for real data. |
| Assume a specific system now (e.g., "we will use SAP for pricing") to make the design concrete | Explicitly forbidden — no Phase 0/1 research confirms any such system for HCME; would be inventing an integration (principle 15/16). |
| Build the real integrations now, since Phase 2 could technically implement them | Out of scope by the brief ("do not connect external APIs" in Phase 2) and premature — there is nothing confirmed to integrate with yet. |

## Consequences

- Until HCME confirms real systems, the platform's live behaviour for every adapter-backed capability is "return UNKNOWN / fail cleanly" — this is by design (see `AVAILABILITY_ARCHITECTURE.md` §3), not a placeholder to be embarrassed about.
- Every new confirmed integration in the future is additive (a new adapter implementation + configuration), not a redesign.

## Status

Accepted.
