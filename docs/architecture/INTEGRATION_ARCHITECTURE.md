# Integration Architecture

**Pattern:** every external dependency is reached through a named adapter interface, registered once, never called directly from a business module (principle 6, `BACKEND_ARCHITECTURE.md` §2). This document is the single index of every adapter interface in the system and its current classification.

## 1. Provider classification

| Interface | Purpose | Classification | Notes |
|---|---|---|---|
| `InventoryProvider` | Query available quantity at a source (`AVAILABILITY_ARCHITECTURE.md`) | UNKNOWN / Mock-test only | No real HCME inventory source confirmed. |
| `PricingProvider` | Resolve price for a (customer, part, quantity, dealer) (`ORDER_ARCHITECTURE.md` §5) | UNKNOWN / Mock-test only | Confirmed only that pricing is dealer/account-dependent industry-wide (Phase 0); no system named. |
| `OrderProvider` | Optional future adapter to an external order-management system of record, if one is confirmed | UNKNOWN / Future | Not assumed to exist; the platform is authoritative for its own Order record until/unless this changes (`DATA_OWNERSHIP.md`). |
| `RoutingProvider` | Feasible transport routes/modes (`FULFILMENT_ARCHITECTURE.md`) | UNKNOWN / Mock-test only | No carrier confirmed. |
| `ShippingRateProvider` | Transport cost estimate (`FULFILMENT_ARCHITECTURE.md`) | UNKNOWN / Mock-test only | Same. |
| `ShipmentProvider` | Create a shipment with a carrier (`SHIPMENT_ARCHITECTURE.md`) | UNKNOWN / Mock-test only | Same. |
| `TrackingProvider` | Shipment events (`SHIPMENT_ARCHITECTURE.md`) | UNKNOWN / Mock-test only | Same. |
| `ServiceProvider` | Optional future adapter to an external service-job system, if one is confirmed beyond ConSite | UNKNOWN / Future | ConSite is confirmed to exist as a telematics/alerts tool, not a confirmed service-job system of record (Phase 1 `HCME_CONFIRMED_VS_UNKNOWN.md`). |
| `DealerProvider` | Source of Dealer/Dealer Branch/Territory/Capability data (`DEALER_ARCHITECTURE.md`) | UNKNOWN / Future | No dealer master system confirmed. |
| Neo4j (fitment/context read) | Relationship/context queries (`NEO4J_ARCHITECTURE.md`) | **Confirmed HCME-adjacent source** | Already integrated, live, confirmed. Not adapter-wrapped the same way as the above (it is an internal platform data store, not an external business system), but is still accessed only through its own module boundary (`BACKEND_ARCHITECTURE.md`), and its failure is handled the same way (see `RESILIENCE_ARCHITECTURE.md`). |
| Telematics API (ISO 15143-3 / AEMP 2.0) | Future upstream trigger only | **Confirmed to exist externally; explicitly excluded from this phase** | Not integrated, not adapter-registered, per Phase 1 §Future Inputs and BR-08. |

## 2. The mock/test rule

> A mock/test provider may exist for development and testing, but it must **never** be presented as real HCME data.

Enforced architecturally by:

1. **Explicit environment gating** — a mock implementation is only registered in `development`/`test` environments (`ENVIRONMENT_CONFIGURATION.md`); production configuration has no mock registered for any UNKNOWN-classified interface above, meaning a production Availability query genuinely returns `UNKNOWN` for every source until a real provider is confirmed and registered (see `AVAILABILITY_ARCHITECTURE.md` §3) — it does not silently fall back to mock data.
2. **Response tagging** — every provider response, mock or real, carries its provider identity in the provenance recorded for audit (`AUDIT_ARCHITECTURE.md`), so a mock-originated result is always traceable as such even inside non-production environments.

## 3. Adapter contract shape (conceptual, shared across all providers)

Every adapter interface above shares the same conceptual contract, so the resilience treatment in `RESILIENCE_ARCHITECTURE.md` applies uniformly:

- A bounded input (never the whole business context — only what that specific call needs).
- A bounded timeout.
- A result that is either a well-formed success or an explicit "could not determine" outcome — never a thrown exception that the calling business module has to interpret ad hoc.
- Provenance metadata (provider identity, timestamp, raw-response reference where feasible) attached to every result, success or not.

## 4. Registration

Adapters are registered once, at startup/deploy configuration time, per environment (`ENVIRONMENT_CONFIGURATION.md`) — which concrete implementation backs each interface is configuration, not code that business modules branch on. This is what "replaceable" means architecturally: adding a real carrier later is a new implementation of `ShipmentProvider`/`TrackingProvider` plus a configuration change, not a change to the Shipments module or the API contract.
