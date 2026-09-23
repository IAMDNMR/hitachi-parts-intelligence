# ADR-004 — Modular Monolith vs Microservices

## Context

Phase 1 identifies ten-plus business domains (Parts, Availability, Fulfilment, Allocation, Orders, Shipments, Dealers, Service, Integrations, Audit, Authentication). Architectural principle 4 explicitly warns against introducing microservices without a demonstrated need; principle 5 asks for a modular architecture that *can* evolve if scale requires it.

## Decision

Each business domain is a **module within one deployable codebase** (a modular monolith), not a separate microservice — module boundaries, dependencies, and ownership rules are fixed in `BACKEND_ARCHITECTURE.md`.

## Reason

- No domain today has an independent scaling, deployment cadence, or team-ownership need that would justify the operational overhead of microservices (separate deployments, network calls between domains, distributed transaction handling for what are today in-process calls).
- A modular monolith gets the maintainability benefit microservices are often reached for (clear boundaries, no tangled dependencies) without the distributed-systems cost, matching "as simple as possible while still production-grade" (principle 2).
- Module boundaries are enforced the same way regardless of deployment shape (`BACKEND_ARCHITECTURE.md` §2's "allowed communication" rules) — extraction into a separate service later, if a genuine need arises, is a deployment change, not a business-logic rewrite.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Microservices per domain (10+ services) | No demonstrated need (principle 4); would require inter-service communication/consistency handling for what is currently a single coherent business process with a linear state machine — directly working against Phase 1's design, which assumes one coherent Fulfilment Request trace. |
| A single undifferentiated codebase with no module boundaries | Would make it hard to enforce "only Integrations may call external systems" (principle 6) and "each module owns its own data" (principle 11's spirit applied to modules) — the maintainability risk the brief explicitly warns against ("do not build a throwaway prototype"). |
| Splitting only the highest-risk domain (Allocation) into its own service now | Premature — Allocation's concurrency requirement (`ALLOCATION_ARCHITECTURE.md`) is satisfied by a single-database transaction; there is no scale evidence yet that it needs isolation from the rest of the backend. |

## Consequences

- Module boundaries must be genuinely enforced in code structure (not just documentation) from the first line of Phase 3 implementation, or the "can evolve later" property is lost.
- A future split, if ever needed, is guided by which module first demonstrates an independent scaling or ownership need — not decided speculatively now.

## Status

Accepted.
