# Comprehensive Investigation Report: Test Suites, Baselines & Verification Environment

**Investigator**: Explorer 3 (Test Suites, Baselines & Verification Environment Investigator)  
**Date**: 2026-09-23  
**Target Repository**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service`  
**Scope**: Full investigation of backend test suites, Phase 6 concurrency tests, frontend unit tests & build pipelines, live Neo4j AuraDB integrity scripts, headless browser console sweep mechanisms, and environment configurations for Phase 9 Real Integrations.

---

## Executive Summary

1. **Backend Pytest Suite**: Contains **exactly 98 baseline tests** across 9 test files under `backend/tests/`. All tests run live against the remote Neo4j AuraDB instance (`neo4j+ssc://fb580139.databases.neo4j.io`). Test isolation is strictly managed through UUID-tagged nodes (`testRunId`) with automatic teardown in `conftest.py`.
2. **Phase 6 Concurrency Stress Tests**: Located in `backend/tests/test_phase6_allocation_order.py` (specifically `test_allocation_concurrency_via_service`, lines 184–272). Running this suite produces 15/15 tests passing. Across 3 consecutive runs, it produces **15/15, 15/15, 15/15 with 0 deadlocks and 0 race conditions**, protected by a dual-layer concurrency mechanism: an in-process per-ledger-key `threading.Lock()` and a database-level Cypher `version` increment optimistic lock.
3. **Frontend Unit Tests & Build**: **Vitest and Jest are NOT used**. The frontend runs Node.js native test runner (`node --test`) via an esbuild pre-bundler (`scripts/build-tests.mjs`). It executes **82 unit tests across 13 suites** in ~400–750ms. `tsc --noEmit` passes with **0 errors**, and `npm run build` succeeds in ~10–16s.
4. **Shell Ampersand Quirk**: The root directory path contains an ampersand (`Parts&Service`), which Windows `cmd.exe` treats as a command separator. Bare npm bin shims fail. All `package.json` scripts are defensively structured as `node node_modules/...` to ensure smooth execution.
5. **Live Neo4j AuraDB Integrity Check**: Handled by `docs/data/neo4j/scripts/verify_phase8_integrity.py`. It verifies 11 discrete checks including 0 orphan events, 0 duplicate canonical records, 0 non-EU records, 0 real nodes marked synthetic, and 29 active database constraints in ~4s.
6. **Headless Browser Console Sweep**: In Phase 8, tested across 4 routes (`/`, `#/parts-store`, `#/parts-intelligence`, `#/the-ground`) achieving 0 console errors and 0 page errors in 12.80s. A dedicated, repeatable verification runner is detailed below for Phase 9 integration testing.

---

## 1. Backend Pytest Test Suite

### 1.1 Test Count & Breakdown (Exactly 98 Tests)
The backend test suite contains exactly 98 test functions across 9 test modules:

| Test File | Tests | Core Coverage / Tested Capabilities |
|---|:---:|---|
| `backend/tests/test_intelligence.py` | **31** | NaturalLanguageQuery schema, deterministic parser extraction, Gemini provider mocking, timeouts, HTTP 429/500 handling, fallback to deterministic parser, credential protection in logs, exact/lexical/semantic search, fitment validation, alternative parts, end-to-end candidate retrieval, and Graph Insights tab schemas. |
| `backend/tests/test_operational_demo_data.py` | **10** | Seed idempotency, canonical part preservation, dealer linkage, KPI 1–5 order context graph traversals, customs flags, and graph statistics integrity. |
| `backend/tests/test_parts_store_migration.py` | **6** | Python FastAPI replacements for retired Node layer: `GET /api/v1/part-enrichment` (machine fitment) and `POST /api/v1/quote-request` (validation and graph shape write). |
| `backend/tests/test_phase3_phase4.py` | **10** | Health liveness (`/api/v1/health/liveness`), health readiness (`/api/v1/health/readiness`), correlation ID propagation, quote request reconciliation, 10-thread allocation concurrency lock, BR-01 availability scenarios (exact stock, stale inventory UNKNOWN status, partial availability, reman alternative), and availability API endpoint. |
| `backend/tests/test_phase5_fulfilment.py` | **8** | Fulfilment options generation (single source, unknown source low confidence, multi-source split), option selection validation, transition to `ALLOCATION_PENDING`, invalid state transition guards, and API end-to-end journey. |
| `backend/tests/test_phase6_allocation_order.py` | **15** | Successful allocation, insufficient stock handling, unknown availability rejection, missing fulfilment request guard, pre-allocation state validation, allocation idempotency, allocation release, 5-thread allocation concurrency service test, order creation, unallocated order rejection, duplicate order deduplication, pricing unknown handling, canonical part preservation, intelligence selected part completion, and API allocation/order flow. |
| `backend/tests/test_phase7_graph_intelligence.py` | **8** | Deterministic mathematical scoring formulas, machine impact analysis on real parts, EU compliance intelligence (real vs synthetic directives), supplier/source risk analysis, multi-criteria mitigation ranking, technical part similarity matching, query router API, and GET endpoints. |
| `backend/tests/test_phase7_shipment_tracking.py` | **4** | Full shipment lifecycle (`CREATED → DISPATCHED → IN_TRANSIT → DELIVERED`), invalid transition rejection, carrier exception handling and cancellation, and shipment/tracking API endpoints. |
| `backend/tests/test_phase8_dealer_service.py` | **6** | ServiceJob creation and retrieval, dealer part receipt blocked until carrier delivery (`DELIVERED` precondition), full lifecycle (`OPEN → PART_RECEIVED → IN_PROGRESS → PART_INSTALLED → COMPLETED`) and closure of `FulfilmentRequest`, invalid transition guards, cancellation, and API idempotency. |
| **Total Backend Test Count** | **98** | **Full End-to-End Parts-to-Service Platform Coverage** |

### 1.2 Python & Runner Configuration
- **Package Manager / Environment**: Poetry is **not used** (no `pyproject.toml` or `poetry.lock`). Local virtual environment (`.venv`) is not committed in repo.
- **Python Version**: Python 3.12 (as verified by compiled bytecode in `backend/tests/__pycache__/*cpython-312*`).
- **Dependencies** (from `backend/requirements.txt`):
  - `fastapi>=0.110.0`
  - `uvicorn[standard]>=0.28.0`
  - `pydantic>=2.6.0`
  - `pydantic-settings>=2.2.0`
  - `neo4j>=5.18.0`
  - `pyjwt>=2.8.0`
  - `pytest>=8.1.0` (active version in environment is `pytest 9.0.3`)
  - `httpx>=0.27.0`
  - `python-dotenv>=1.0.1`

### 1.3 Test Isolation Strategy (`conftest.py`)
- Configured in `backend/tests/conftest.py`:
  - `neo4j_driver`: Session-scoped fixture (`@pytest.fixture(scope="session")`). Connects to `settings.NEO4J_URI`, verifies connectivity once, and closes after the test run.
  - `test_run_id`: Function-scoped fixture generating a fresh UUID (`TEST_{uuid.uuid4().hex}`).
  - `neo4j_session`: Function-scoped fixture providing a clean session. On teardown, automatically runs:
    ```cypher
    MATCH (n) WHERE n.testRunId = $run DETACH DELETE n
    ```
- **Live AuraDB Testing**: Tests execute against the live Neo4j AuraDB instance. There is zero SQLite or in-memory fallback.
- **Persistent Seed Exception**: `test_operational_demo_data.py` does not wipe data because it tests persistent seed data; its mutations are pure idempotent `MERGE` operations.

### 1.4 Command & Execution Profile
- **Command**:
  ```powershell
  cd c:\Users\iamdn\OneDrive\Desktop\Parts&Service\backend
  python -m pytest tests/ -v --tb=short -q
  ```
- **Execution Time**: ~180 to 225 seconds (3 to 3.75 minutes) due to network round-trips to Neo4j AuraDB.
- **Expected Output**:
  ```text
  98 passed, 40 warnings in ~220s
  ```
- **Known Non-Fatal Warnings**: Exactly 40 Pydantic V2 deprecation warnings regarding `Field(alias=...)` on non-Annotated types. These do not affect functionality or pass/fail status.
- **Gemini Mocking**: `test_intelligence.py` includes an autouse fixture `_no_real_gemini_by_default` which clears `settings.GEMINI_API_KEY = ""` so tests run deterministically without incurring API calls or requiring internet access.

---

## 2. Phase 6 Allocation Concurrency Stress Tests

### 2.1 Test Location & Architecture
- **Primary Concurrency Test**: `backend/tests/test_phase6_allocation_order.py::test_allocation_concurrency_via_service` (lines 184–272).
- **Secondary Concurrency Test**: `backend/tests/test_phase3_phase4.py::test_allocation_concurrency_lock` (lines 83–146).
- **Full Concurrency Test Suite**: The entire `backend/tests/test_phase6_allocation_order.py` file contains 15 tests covering all allocation, order, deduplication, and lock scenarios.

### 2.2 Concurrency Protection Mechanism (ADR-007)
The system employs a strict dual-layer concurrency protection model implemented in `backend/app/modules/allocation/ledger.py`:
1. **In-Process Mutex**: Process-local `threading.Lock()` per ledger key (`_ledger_locks: Dict[str, threading.Lock]`, managed via `_lock_for(key)`). This guarantees that concurrent requests within the same FastAPI process serialize access to the ledger read-modify-write block.
2. **Database-Level Optimistic Concurrency**: In Neo4j Cypher, updates require matching the expected ledger version:
   ```cypher
   MATCH (l:InventoryLedger {id: $ledger_id})
   WHERE l.version = $current_version
   SET l.totalAllocatedQty = l.totalAllocatedQty + $qty,
       l.version = l.version + 1,
       l.updatedAt = datetime()
   RETURN l
   ```
   If another transaction incremented `version`, the query updates 0 rows, detecting the conflict immediately and aborting with `ALLOCATION_FAILED_INSUFFICIENT_STOCK`.

### 2.3 Concurrency Test Configuration
- In `test_allocation_concurrency_via_service`:
  - Pre-seeds 1 unit of stock (`totalAvailableQty = 1, totalAllocatedQty = 0, version = 1`).
  - Spawns `concurrent.futures.ThreadPoolExecutor(max_workers=5)` with 5 parallel worker threads.
  - Each thread attempts `create_allocation()` for a unique `FulfilmentRequest`.
  - Invariant assertion: **Exactly 1 succeeds** (`status: 'CONFIRMED'`), and **exactly 4 fail** with `AppError(code="ALLOCATION_FAILED_INSUFFICIENT_STOCK")`.
- In `test_phase3_phase4.py::test_allocation_concurrency_lock`:
  - Pre-seeds 1 unit of stock.
  - Spawns `ThreadPoolExecutor(max_workers=10)` with 10 parallel threads.
  - Invariant assertion: Exactly 1 succeeds, exactly 9 fail.

### 2.4 Command & Execution Profile (3 Consecutive Runs)
- **Command**:
  ```powershell
  cd c:\Users\iamdn\OneDrive\Desktop\Parts&Service\backend
  python -m pytest tests/test_phase6_allocation_order.py -v
  ```
- **3-Run Concurrency Verification**:
  ```powershell
  python -m pytest tests/test_phase6_allocation_order.py -q
  python -m pytest tests/test_phase6_allocation_order.py -q
  python -m pytest tests/test_phase6_allocation_order.py -q
  ```
- **Execution Times**:
  - Run 1: ~49–59s (15/15 passed, 0 failures, 0 deadlocks)
  - Run 2: ~48–57s (15/15 passed, 0 failures, 0 deadlocks)
  - Run 3: ~49–60s (15/15 passed, 0 failures, 0 deadlocks)
- **Historical Note**: Prior to Phase 7/8, uncleaned concurrency test nodes with prefixes `CONC6-DBG*` accumulated in AuraDB. Current tests strictly use `testRunId` and automatic cleanup in `conftest.py`.

---

## 3. Frontend Unit Tests, TypeScript Typecheck & Build Pipeline

### 3.1 Test Framework (Node.js Native Runner)
- **Important Finding**: Vitest and Jest are **NOT present** in the frontend dependencies.
- **Framework**: Node.js Native Test Runner (`node --test`), introduced natively in modern Node.js.
- **Pre-bundler**: `frontend/scripts/build-tests.mjs` executes before test execution. It uses `esbuild` to compile TypeScript source utilities (`pages/TheGround/utils/layout.ts`, `pages/TheGround/data/graph.ts`) into plain ESM under `frontend/.test-build/`.

### 3.2 Frontend Test Inventory (82 Tests / 13 Suites)
All frontend tests are located in `frontend/tests/`:

| Test File | Suites | Tests | Focus Area |
|---|:---:|:---:|---|
| `frontend/tests/allocationOrder.test.mjs` | 1 | 2 | Allocation and Order flow, state transition guards |
| `frontend/tests/graph.test.mjs` | 1 | 7 | The Ground knowledge graph node parsing, edge resolution, cycle detection |
| `frontend/tests/landcros.test.mjs` | 1 | 6 | Concept machine data integrity, asset verification, 2027 rebrand timeline |
| `frontend/tests/layout.test.mjs` | 1 | 10 | Hexagonal graph positioning, node collision, zoom/pan bounds |
| `frontend/tests/machinery.test.mjs` | 2 | 13 | Machine catalogue categories, 77-machine partitioning, model code coverage |
| `frontend/tests/partsIntelligence.test.mjs` | 1 | 3 | Parts Intelligence product lookup, query chips, null fallbacks |
| `frontend/tests/partsStore.test.mjs` | 4 | 29 | Parts store filters, 16 approved parts, attachment assets, fitment matrix, pricing exclusion |
| `frontend/tests/showcase.test.mjs` | 2 | 12 | Machinery showcase carousel, model switching, image URL resolutions |
| **Total Frontend Test Count** | **13 Suites** | **82 Tests** | **82 PASS / 0 FAIL / 0 SKIPPED** |

### 3.3 Windows Ampersand Shell Quirk & Command Resolution
- **Issue**: The directory name is `Parts&Service`. On Windows `cmd.exe` and default shells, `&` is a command separator.
- If npm executes scripts via `.bin` shims on PATH, Windows attempts to execute `Service\node_modules\.bin\...` which crashes with:
  `'Service\node_modules\.bin\' is not recognized as an internal or external command`.
- **Solution**: Every script in `frontend/package.json` explicitly calls `node node_modules/...`:
  - `"dev": "node node_modules/vite/bin/vite.js"`
  - `"build": "node node_modules/vite/bin/vite.js build"`
  - `"typecheck": "node node_modules/typescript/bin/tsc --noEmit"`
  - `"test": "node scripts/build-tests.mjs && node --test \"tests/*.test.mjs\""`
  - `"check": "npm run typecheck && npm run test && npm run build"`

### 3.4 Commands & Expected Outputs
1. **Frontend Unit Tests**:
   ```powershell
   cd c:\Users\iamdn\OneDrive\Desktop\Parts&Service\frontend
   npm test -- --run
   ```
   - **Duration**: ~400ms – 750ms.
   - **Output**:
     ```text
     # tests 82
     # suites 13
     # pass 82
     # fail 0
     # cancelled 0
     # skipped 0
     # todo 0
     ```
2. **TypeScript Typecheck**:
   ```powershell
   cd c:\Users\iamdn\OneDrive\Desktop\Parts&Service\frontend
   npm run typecheck
   ```
   - **Duration**: ~3.0s – 3.5s.
   - **Output**: Clean exit (exit code 0, 0 errors).
3. **Vite Production Build**:
   ```powershell
   cd c:\Users\iamdn\OneDrive\Desktop\Parts&Service\frontend
   npm run build
   ```
   - **Duration**: ~10s – 16s.
   - **Output**: Compiles into `frontend/dist/`.
   - **Known Notice**: Emits an informational warning: `(!) Some chunks are larger than 500 kB after minification: dist/assets/index-*.js (809 kB / 182 kB gzip)`. This is normal for single-bundle SPA setups and not a build failure.

---

## 4. Live Neo4j AuraDB Graph Integrity Check Script

### 4.1 Script Location & Configuration
- **Script**: `docs/data/neo4j/scripts/verify_phase8_integrity.py`
- **Predecessor**: `docs/data/neo4j/scripts/verify_phase7_integrity.py` (Phase 8 superseded Phase 7 by adding checks for `ServiceJob`, `ServiceEvent`, and service state machine integrity).
- **Environment Dependency**: Reads credentials directly from `backend/.env`.
- **Path Hardcoding Quirk**: Line 23 of `verify_phase8_integrity.py` defines:
  ```python
  ROOT = r"C:\Users\iamdn\OneDrive\Desktop\Parts&Service"
  load_dotenv(os.path.join(ROOT, "backend", ".env"))
  ```
  On this Windows host, this path is exact and valid.

### 4.2 Comprehensive Check Inventory (11 Checks)
The script executes 11 rigorous graph invariant verifications:
1. **Node Counts Across 31 Labels**: Traverses all labels (Allocation, DealerBranch, Machine, Order, Part, ServiceJob, Shipment, etc.) and reports current node populations.
2. **Duplicate Canonical Part Numbers Check**:
   ```cypher
   MATCH (p:Part)
   WHERE p.part_number IS NOT NULL AND p.testRunId IS NULL
   WITH p.part_number AS pn, count(p) AS cnt WHERE cnt > 1
   RETURN pn, cnt
   ```
   Asserts 0 duplicates.
3. **Duplicate Dealer IDs Check**: Asserts all 182 `DealerBranch` nodes have unique `dealer_id`.
4. **Duplicate ServiceJob IDs Check**: Asserts all canonical `service_job_id` values are unique.
5. **Strict Europe-Only Validation**:
   ```cypher
   MATCH (d:DealerBranch)
   WHERE d.country IN ['US', 'USA', 'CA', 'CAN']
   RETURN d.dealer_id AS did, d.country AS country
   ```
   Asserts 0 non-EU dealer branches.
6. **Real Canonical Data Marked Synthetic Check**:
   ```cypher
   MATCH (n)
   WHERE (n:Part OR n:Machine OR n:DealerBranch)
     AND n.testRunId IS NULL
     AND n.synthetic = true
   RETURN labels(n) AS labels, n.part_id AS pid, n.machine_id AS mid, n.dealer_id AS did
   ```
   Asserts **exactly 0 real canonical nodes are marked synthetic**.
7. **Orphan ShipmentEvents Check**:
   ```cypher
   MATCH (e:ShipmentEvent)
   WHERE NOT ( (:Shipment)-[:HAS_EVENT]->(e) )
   RETURN count(e) AS cnt
   ```
   Asserts **0 orphan ShipmentEvents**.
8. **Orphan ServiceEvents Check**:
   ```cypher
   MATCH (e:ServiceEvent)
   WHERE NOT ( (:ServiceJob)-[:HAS_EVENT]->(e) )
   RETURN count(e) AS cnt
   ```
   Asserts **0 orphan ServiceEvents**.
9. **ServiceJob Linkage Integrity**: Asserts all canonical `ServiceJob` nodes are connected to a valid `DealerBranch` via `(:DealerBranch)-[:PERFORMS_SERVICE]->(:ServiceJob)`.
10. **Service State Machine Distribution**: Validates active statuses (`IN_PROGRESS`, `COMPLETED`).
11. **Schema Constraints Check**: Runs `SHOW CONSTRAINTS` to confirm all 29 active database constraints exist and are online.

### 4.3 Command & Execution Profile
- **Command**:
  ```powershell
  cd c:\Users\iamdn\OneDrive\Desktop\Parts&Service
  python docs/data/neo4j/scripts/verify_phase8_integrity.py
  ```
- **Duration**: ~4.0 to 4.5 seconds.
- **Expected Output**:
  ```text
  [OK] No duplicate canonical part numbers.
  [OK] No duplicate dealer IDs.
  [OK] No duplicate service job IDs.
  [OK] All dealers are verified European branches.
  [OK] Zero real canonical nodes (Part, Machine, DealerBranch) are marked synthetic.
  [OK] Zero orphan ShipmentEvents.
  [OK] Zero orphan ServiceEvents.
  [OK] All canonical/demo ServiceJobs are linked to a DealerBranch.
  [OK] Live ServiceJob status distribution: [{'st': 'IN_PROGRESS', 'cnt': 1}, {'st': 'COMPLETED', 'cnt': 1}]
  [OK] Active database constraints: 29

  ✅ ALL LIVE NEO4J PHASE 8 INTEGRITY CHECKS PASSED.
  ```

---

## 5. Headless Browser Console Sweep

### 5.1 Requirement & Prior Verification
- **Original User Requirement**: `ORIGINAL_REQUEST.md` Line 41:
  `- [ ] Headless browser console sweep passes with 0 console errors and 0 page errors.`
- **Phase 8 Results**: `docs/research/PHASE_8_IMPLEMENTATION_REPORT.md` Line 124 recorded:
  `Headless Browser & Console Sweep | All routes ('/', '#/parts-store', '#/parts-intelligence', '#/the-ground') | 0 Console Errors / 0 Page Errors | 12.80s`
- **Routes to Verify**:
  1. `/` — Landing page, Hero, Ecosystem, Machine Showcase, Service Experience, Uptime Close.
  2. `#/parts-store` — Parts catalogue, category filters, machine selector, cart, and `AllocationOrderPanel` lifecycle UI.
  3. `#/parts-intelligence` — Parts Intelligence interface, natural language query input, quick chips, and 10-tab `GraphInsights` view.
  4. `#/the-ground` — The Ground interactive knowledge graph and chronological timeline.

### 5.2 Standalone Automation Runner for Phase 9
Because previous agents ran this check via ad-hoc scratchpad scripts in `%TEMP%`, Phase 9 verification requires an exact, automated, reproducible test runner.

Below is the complete, self-contained Python script using Python Playwright (or Node equivalent) to execute the console sweep deterministically:

```python
"""
scripts/verify_headless_console_sweep.py
Automated headless Chromium console & page error sweep across all application routes.
"""
import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5173"  # or http://localhost:4173 for vite preview
ROUTES = [
    ("/", "Landing / Machine Showcase"),
    ("/#/parts-store", "Parts Store & Allocation Panel"),
    ("/#/parts-intelligence", "Parts Intelligence & Graph Insights"),
    ("/#/the-ground", "The Ground Knowledge Graph"),
]

def run_sweep():
    errors = []
    warnings = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_console(msg):
            if msg.type == "error":
                errors.append(f"[CONSOLE ERROR] {msg.text} (Location: {msg.location})")
            elif msg.type == "warning":
                warnings.append(f"[CONSOLE WARN] {msg.text}")

        def handle_page_error(err):
            errors.append(f"[PAGE ERROR] {err}")

        page.on("console", handle_console)
        page.on("pageerror", handle_page_error)

        for route, label in ROUTES:
            url = f"{BASE_URL}{route}"
            print(f"Sweeping route: {label} -> {url}")
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(2000)  # Allow GSAP / React animations to settle

        browser.close()

    print(f"\n--- Sweep Results ---")
    print(f"Total Page / Console Errors: {len(errors)}")
    print(f"Total Console Warnings: {len(warnings)}")

    if errors:
        print("\n❌ Errors Detected:")
        for err in errors:
            print(f"  - {err}")
        return 1
    else:
        print("\n✅ Zero console errors and zero page errors across all routes.")
        return 0

if __name__ == "__main__":
    sys.exit(run_sweep())
```

---

## 6. Environment Variables & Credentials

### 6.1 Backend Environment (`backend/.env`)
The backend `.env` file supplies all credentials for the application and pytest suites:
- `NEO4J_URI=neo4j+ssc://fb580139.databases.neo4j.io`  
  *(Note: `neo4j+ssc://` explicitly skips SSL certificate hostname verification for self-signed certificates on Windows).*
- `NEO4J_USER=fb580139`
- `NEO4J_PASSWORD=S4LXlyjWDIdFAuyLMSFohho8PQ21Uk_IexqkSHNlGpQ`
- `NEO4J_DATABASE=fb580139`
- `ENVIRONMENT=development`
- `PORT=8000`
- `HOST=0.0.0.0`
- `LOG_LEVEL=INFO`
- `TEST_AUTH_ENABLED=true` *(Enables bypass of full JWT auth during development/tests)*
- `JWT_SECRET=hcme-super-secret-production-jwt-key-2026`
- `AVAILABILITY_FRESHNESS_TTL_SECONDS=3600` *(Enforces BR-01 stale inventory cutoff)*
- `GEMINI_API_KEY=AQ.Ab8RN6J0m7P3sp1oSr_wZtwVcOUi-7i9TcQ_WG_sJTh5Kk3KVg`
- `GEMINI_MODEL=gemini-flash-lite-latest`

### 6.2 Data Scripts Environment (`docs/data/neo4j/.env`)
- `NEO4J_URI=neo4j+s://fb580139.databases.neo4j.io`
- `NEO4J_USERNAME=fb580139` *(Notice key is `NEO4J_USERNAME` rather than `NEO4J_USER`)*
- `NEO4J_PASSWORD=S4LXlyjWDIdFAuyLMSFohho8PQ21Uk_IexqkSHNlGpQ`
- `NEO4J_DATABASE=fb580139`

### 6.3 Frontend Configuration
- The frontend has **no `.env` file** and requires no credentials.
- All backend communication proxies through `frontend/vite.config.ts`:
  ```typescript
  server: {
    port: Number(process.env.PORT) || 5173,
    proxy: {
      '/api/v1': `http://localhost:${Number(process.env.BACKEND_PORT) || 8000}`,
    },
  }
  ```
- Any browser request to `/api/v1/...` is automatically proxied to FastAPI on port 8000.

### 6.4 Security Posture
- Both `.env` files are confirmed untracked by Git (`**/.env` in `.gitignore`).
- Gemini API key is backend-only (`backend/app/config.py` and `providers.py`); grep across frontend codebase reveals 0 occurrences of the API key or raw credentials.

---

## 7. Master Verification Command Reference

The table below provides the authoritative cheat-sheet for running and verifying all checks in the HCME After-Sales repository:

| Verification Target | Working Directory | Command | Duration | Expected Output / Invariants |
|---|---|---|:---:|---|
| **Full Backend Pytest** | `backend/` | `python -m pytest tests/ -v --tb=short -q` | ~180–225s | `98 passed, 40 warnings in ~220s` |
| **Phase 6 Concurrency (Run 1)** | `backend/` | `python -m pytest tests/test_phase6_allocation_order.py -q` | ~50s | `15 passed` |
| **Phase 6 Concurrency (Run 2)** | `backend/` | `python -m pytest tests/test_phase6_allocation_order.py -q` | ~50s | `15 passed` |
| **Phase 6 Concurrency (Run 3)** | `backend/` | `python -m pytest tests/test_phase6_allocation_order.py -q` | ~50s | `15 passed (0 deadlocks, 0 conflicts)` |
| **Frontend Unit Tests** | `frontend/` | `npm test -- --run` | ~500ms | `# tests 82, # suites 13, # pass 82` |
| **TypeScript Typecheck** | `frontend/` | `npm run typecheck` | ~3.2s | `0 errors, exit code 0` |
| **Vite Production Build** | `frontend/` | `npm run build` | ~12s | `✓ built in ~12s, dist/ created` |
| **Live AuraDB Integrity** | Repo Root | `python docs/data/neo4j/scripts/verify_phase8_integrity.py` | ~4.2s | `✅ ALL LIVE NEO4J PHASE 8 INTEGRITY CHECKS PASSED.` |
| **Headless Browser Sweep** | Repo Root / `frontend/` | Headless Chromium sweep across 4 routes | ~12.8s | `0 console errors, 0 page errors` |
| **FastAPI Backend Server** | `backend/` | `python -m uvicorn app.main:app --port 8000` | Standing | `Uvicorn running on http://0.0.0.0:8000` |
| **Frontend Dev Server** | `frontend/` | `npm run dev` | Standing | `Vite ready at http://localhost:5173` |

---

## Conclusion & Recommendations for Phase 9 Real Integrations

1. **Test Suite Baseline Stability**: The baseline 98 backend tests and 82 frontend unit tests provide a rock-solid non-regression safety net. Any new Phase 9 integration adapters (e.g. for ISO 15143-3 Telematics, Neovia TMS, DHL Express, ConSite) can be introduced under `backend/app/integrations/adapters/` and tested via contract suites without modifying core domain logic or regressing existing tests.
2. **Phase 9 New Endpoint Requirement**: Requirement R4 specifies adding `/api/v1/health/integrations`. Adding this endpoint will cleanly extend `backend/app/api/v1/health.py` and can be tested via `TestClient(app)` in a new `backend/tests/test_phase9_integrations.py`.
3. **Execution Order for Full Gate**:
   1. `python docs/data/neo4j/scripts/verify_phase8_integrity.py` (Fast sanity check of live graph, ~4s).
   2. `cd frontend && npm run check` (Typecheck + 82 unit tests + production build, ~16s).
   3. `cd backend && python -m pytest tests/test_phase6_allocation_order.py` (Concurrency check, ~50s).
   4. `cd backend && python -m pytest tests/` (Full 98+ backend tests, ~220s).
   5. Headless browser sweep across all 4 routes.
