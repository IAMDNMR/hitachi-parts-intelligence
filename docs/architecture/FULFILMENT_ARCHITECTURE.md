# Fulfilment Engine Architecture

Implements Phase 1 `FULFILMENT_PROCESS.md`. Input/output and provider abstractions, kept conceptual.

## 1. Input / Output

| | |
|---|---|
| Input | Part, quantity, destination, required-by date, priority (capability only — no policy invented, per BR-07). |
| Output (per candidate option) | Source, available quantity, location, transport mode, provider, processing time, transit time, ETA, transport cost, total cost, currency, constraints. |

## 2. Provider abstractions

| Interface | Responsibility | Confirmed real implementation? |
|---|---|---|
| `RoutingProvider` | Given a source and destination, determine feasible transport modes/routes and estimated transit time. | None — UNKNOWN/no carrier confirmed (`HCME_CONFIRMED_VS_UNKNOWN.md`). |
| `ShippingRateProvider` | Given a route/mode/provider and package details, return a cost estimate. | None — UNKNOWN. |
| `FulfilmentProvider` | A higher-level composite that some carriers/3PLs expose (route + rate + booking in one call) — modelled as an alternative to calling `RoutingProvider`+`ShippingRateProvider` separately, so the architecture is not locked to assuming they are always separate services. | None — UNKNOWN; not assumed to exist. |

**None of DHL, FedEx, UPS, or any other named carrier is hardcoded or assumed as a mandatory dependency anywhere in this architecture.** Every one of the interfaces above is an adapter contract; a real implementation is registered per `INTEGRATION_ARCHITECTURE.md`, and until one is confirmed, only a mock/test implementation exists, clearly separated from production data paths.

## 3. Process flow

```mermaid
flowchart TD
    A[Availability Results] --> B{For each result with status != UNKNOWN-only}
    B --> C[Call RoutingProvider: feasible routes/modes?]
    C --> D{Route(s) found?}
    D -- No --> E[Option marked: no transport data available]
    D -- Yes --> F[Call ShippingRateProvider or FulfilmentProvider: cost + time]
    F --> G{Rate available?}
    G -- No --> H[Option marked incomplete/estimated — never fabricated]
    G -- Yes --> I[Option fully populated: cost, time, ETA]
    E --> J[Attach option, confidence = low]
    H --> J
    I --> J
    J --> K{All results processed?}
    K -- No --> B
    K -- Yes --> L[Return full option set — no auto-selection, BR-03]
```

## 4. Split/multi-source options

Where Availability returned partial quantities across multiple sources, the Fulfilment Engine may compose a multi-leg option (see Phase 1 `FULFILMENT_PROCESS.md` §1 "Multi-source (split) fulfilment"). This is a capability the engine supports; whether it is offered by default remains a Phase 1 TO-BE business decision (`HCME_BUSINESS_QUESTIONS.md` Q7) — the architecture does not decide this policy.

## 5. What this engine does not do

- It does not select a winning option (BR-03) — see `API_ARCHITECTURE.md` §3 for where selection happens.
- It does not reserve stock — that only happens at Allocation (`ALLOCATION_ARCHITECTURE.md`).
- It does not resolve final pricing — transport cost here is an input to, not the same as, the Order's total (`ORDER_ARCHITECTURE.md`).
