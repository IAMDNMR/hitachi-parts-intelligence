# Testing Architecture

Testing strategy defined before implementation, per the brief. The existing repository already has a test convention (`frontend/tests`, `node --test`, `npm run check` running typecheck + test + build) — this phase extends that convention rather than introducing a new test runner or framework without justification.

## 1. Test categories

| Category | Scope | Priority |
|---|---|---|
| Unit tests | Individual business module logic — e.g., the Availability status-derivation logic (`ON_HAND/RESERVED/ALLOCATED/AVAILABLE/UNKNOWN`), Fulfilment Option construction, Order total calculation. | High — fast feedback, run on every change. |
| API tests | Each `/api/v1/...` endpoint's contract (`API_ARCHITECTURE.md`): request validation, response shape, status codes, auth enforcement. | High. |
| Integration tests | Backend modules against real Neo4j AuraDB instance using test-scoped isolation (`testRunId` tagging and automatic teardown) — verifying the actual database interactions. | High. |
| Database tests | Schema-level invariants once Phase 3 defines the schema (e.g., constraints that prevent an Allocation quantity from going negative) — placeholder scope in Phase 2; real tests follow the schema. | Medium (grows with Phase 3). |
| Allocation concurrency tests | **The most important test in the whole suite**: simulate two simultaneous allocation attempts against one remaining unit and assert exactly one succeeds (`ALLOCATION_ARCHITECTURE.md` §1) — repeated under load to catch race conditions the locking design is meant to prevent. | Critical. |
| Contract tests for providers | Each Integration Adapter interface (`InventoryProvider`, `PricingProvider`, etc.) has a contract test suite that any implementation (mock or real) must pass — guaranteeing a swapped-in real provider behaves as the business modules expect (timeout, `UNKNOWN` handling, provenance fields present). | High — this is what makes "providers can be replaced" (validation item 6) actually verifiable, not just asserted. |
| End-to-end tests | The full Select Part → Close journey through the API (frontend E2E is out of scope until the UI is built — Phase 3+), using mock providers registered per `ENVIRONMENT_CONFIGURATION.md`. | High for the core flow; grows as stages are implemented. |
| Failure-path tests | One test per row in Phase 1 `FAILURE_AND_EXCEPTION_CASES.md` and `RESILIENCE_ARCHITECTURE.md` — asserting the documented user-visible behaviour, state, and audit outcome actually occur. | High — this is where "production-ready from the beginning" is verified, not just declared. |
| Security tests | Authorization boundary tests (a dealer cannot access another dealer's data — `SECURITY_ARCHITECTURE.md` §3), input validation/injection tests, and a check that no response ever includes a credential or internal database identifier that should not be exposed. | High. |

## 2. What must have automated coverage before Phase 3 implementation is considered complete for a given stage

Per the brief ("the most important business flows must eventually have automated tests"), the following are the non-negotiable minimum, mapped to Phase 1 stages:

1. Select Part validation (part not found, not orderable, fitment uncertain).
2. Availability — sources queried, `UNKNOWN` never becomes `0` (a dedicated regression test for BR-01).
3. Fulfilment Options — no auto-selection occurs (a dedicated regression test for BR-03).
4. **Allocation concurrency** (§1, Critical).
5. Order creation — fails cleanly when pricing cannot be resolved (BR-04); idempotent on retry.
6. Shipment state transitions match `STATE_TRANSITION_ARCHITECTURE.md` §C exactly (no illegal transition accepted).
7. Service Job → Close — the exact BR-11 condition (both Shipment `DELIVERED` and Service Job `COMPLETED`) is enforced, including negative tests (one condition met, the other not — Fulfilment Request must not close).

## 3. Tooling

As planned in Phase 2, the frontend kept its existing test runner (`node --test`) and typecheck/build gate (`npm run check`) — those still cover `frontend/tests`.

As actually implemented, the Phase 3/4 **backend** modules and API handlers did not follow the `frontend/tests`/`node --test` convention: the backend became Python + FastAPI, so its tests are `pytest` under `backend/tests/`, run via `python -m pytest backend/tests/`. An earlier Node/TypeScript implementation of the same backend logic did use `frontend/tests` + `node --test` (following the original plan below) but was removed once the Python backend superseded it, along with its dedicated test files.

## 4. What is not designed here

Load/performance testing, chaos/fault-injection testing beyond the specific failure-path tests in §1, and UI/visual regression testing (no UI exists yet) — none of these are demonstrated needs at this phase; they are not ruled out for later, just not speculative Phase 2 scope.
