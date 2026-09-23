# Neo4j-Only Backend Architecture Consolidation

## Summary
The HCME OEM After-Sales backend has been consolidated to **Neo4j as the sole database and single source of truth**. All relational database dependencies (PostgreSQL, SQLite, SQLAlchemy, psycopg) have been completely removed.

---

## Target Architecture

```
React + TypeScript + Vite (Frontend)
             ↓
    Python + FastAPI (Backend)
             ↓
    Neo4j AuraDB (Single DB & Source of Truth)
```

---

## Entity & Schema Mapping (SQL → Neo4j)

| Relational Table (Old) | Neo4j Node Label / Relation | Key Constraints & Properties |
|---|---|---|
| `fulfilment_requests` | `(:FulfilmentRequest)` | `id` (UNIQUE), `partNumber`, `quantity`, `destinationBranchId`, `customerId`, `machineContext`, `status`, `selectedOptionId`, `createdAt`, `updatedAt` |
| `fulfilment_options` | `(:FulfilmentOption)` | `id` (UNIQUE), `fulfilmentRequestId`, `sourceId`, `sourceType`, `destinationBranchId`, `transportMode`, `carrierCode`, `serviceLevel`, `transitDays`, `eta`, `transportCost`, `currency`, `confidence`, `isSelected`, `isSplit`, `detailsJson`, `createdAt` |
| `inventory_caches` | `(:InventoryCache)` | `id` (UNIQUE), `partNumber`, `sourceId`, `locationId`, `onHandQty`, `reservedQty`, `allocatedQty`, `availableQty`, `status`, `inventoryTimestamp` |
| `committed_inventory_ledgers` | `(:InventoryLedger)` | `id` (UNIQUE, composite `partNumber:sourceId`), `partNumber`, `sourceId`, `totalAvailableQty`, `totalAllocatedQty`, `version`, `updatedAt` |
| `allocations` | `(:Allocation)` | `id` (UNIQUE), `fulfilmentRequestId`, `partNumber`, `sourceId`, `quantity`, `status`, `reservedAt`, `expiryAt`, `idempotencyKey` |
| `audit_records` | `(:AuditRecord)` | `id` (UNIQUE), `actorId`, `actorRole`, `action`, `entityType`, `entityId`, `previousState`, `newState`, `source`, `requestId`, `correlationId`, `detailsJson`, `createdAt` |
| `idempotency_records` | `(:IdempotencyRecord)` | `idempotencyKey + endpoint` (NODE KEY), `requestHash`, `responseStatus`, `responseBodyJson`, `createdAt`, `expiresAt` |
| `parts_inquiries` | `(:PartsInquiry)` | `id` (UNIQUE), `note`, `itemsJson`, `customerName`, `customerEmail`, `customerPhone`, `createdAt` |
| `customers` | `(:Customer)` | `email` (UNIQUE), `name`, `phone`, `createdAt`, `updatedAt` |

---

## Concurrency & Optimistic Locking in Neo4j

The allocation concurrency guarantee (10 concurrent requests for 1 available item -> 1 SUCCESS, 9 CONFLICTS) is preserved using Neo4j ACID transaction semantics with optimistic version checking:

```cypher
MATCH (l:InventoryLedger {id: $ledger_id})
WHERE l.version = $version
SET l.totalAllocatedQty = $new_allocated,
    l.version           = $new_version,
    l.updatedAt         = datetime()
RETURN l.version AS newVersion
```

If multiple transactions race to allocate the same inventory unit, only the transaction with the matching version commits; subsequent transactions fail the `WHERE` condition and are rejected with `CONCURRENCY_VERSION_MISMATCH` (HTTP 409 Conflict).

---

## Verification Results

| Suite / Command | Status | Result |
|---|---|---|
| `python -m pytest backend/tests/ -v` | **PASS** | 18/18 tests passed (0 failures) |
| `npm run typecheck` (frontend) | **PASS** | 0 TypeScript errors |
| `npm run test` (frontend) | **PASS** | 75/75 tests passed (11 suites) |
| `npm run build` (frontend) | **PASS** | Vite production build successful |
| `npm run check` (frontend) | **PASS** | typecheck + test + build all green |
