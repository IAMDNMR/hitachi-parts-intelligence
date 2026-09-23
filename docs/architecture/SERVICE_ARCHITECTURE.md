# Service Architecture

```
Order → Dealer → Service Job → Part Installed → Completed
```

Implements Phase 1 `DEALER_SERVICE_PROCESS.md` §2. **Scope discipline restated:** this is not a service-management platform — only what the Parts-to-Service process needs (create a job, track its four working states, record who did what and when, confirm completion) is designed here.

## 1. Service Job — conceptual shape

| Field | Notes |
|---|---|
| Machine | Reference; may be enriched via Neo4j fitment/context data where available (`NEO4J_ARCHITECTURE.md`), never required for the job to exist. |
| Dealer (Branch) | The performing party — first-class reference, not a text field. |
| Order | The order this job fulfils. |
| Technician | Reference — a minimal identifier tied to the Dealer Branch (`DATA_OWNERSHIP.md`: UNKNOWN/TO-BE source). |
| Status | `OPEN / PART_RECEIVED / IN_PROGRESS / PART_INSTALLED / COMPLETED / CANCELLED` (Phase 1 `PROCESS_STATES.md` §D). |
| Start time / completion time | Recorded at the relevant transitions. |
| Installed parts | One or more Service Part records (`POSTGRESQL_DATA_ARCHITECTURE.md`). |

## 2. Lifecycle and ownership

Owned entirely by the Service module (`BACKEND_ARCHITECTURE.md`), in PostgreSQL, per `STATE_TRANSITION_ARCHITECTURE.md` §D. It is created once an Order is accepted (held until the Dealer confirms receipt — Phase 1 Stage 8) and advances only through the API endpoints defined in `API_ARCHITECTURE.md` §8.

## 3. What is deliberately excluded

Per the brief's scope discipline, this architecture does not include, because Phase 1 does not require them for this process:

- Technician scheduling/dispatch optimisation.
- Warranty claims processing.
- Parts-return/RMA workflows.
- Service history reporting or analytics beyond the audit trail already required (`AUDIT_ARCHITECTURE.md`).
- Any telemetry-driven service triggering (explicitly fenced off — BR-08, BR-09).

If any of these are wanted later, they are new business-process scope (a Phase 1 addendum), not an architectural gap in this design.

## 4. Relationship to Close

A Service Job reaching `COMPLETED` is one of the two conditions for the parent Fulfilment Request to close (the other being Shipment `DELIVERED` — Phase 1 BR-11, `STATE_TRANSITION_ARCHITECTURE.md` §A). The `.../complete` API call (`API_ARCHITECTURE.md` §8) checks this condition and closes the Fulfilment Request in the same operation when both are met, so "the job is done" and "the whole journey is closed" cannot drift out of sync.
