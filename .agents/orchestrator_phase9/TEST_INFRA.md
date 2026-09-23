# E2E Test Infra: HCME Europe OEM Parts & Services Platform — Phase 9

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Integration Inventory | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | Provider Contracts & Factory | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 3 | Concrete European Adapters | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 4 | Synthetic Fallback Preservation | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 5 | AuraDB Provenance Synchronization | ORIGINAL_REQUEST §R2, §R3 | 5 | 5 | ✓ |
| 6 | Europe-Only Boundary Protection | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 7 | Integration Health Endpoint | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 8 | Backend Non-Regression | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 9 | Concurrency & Integrity | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |

## Test Architecture
- Test runner: Python pytest (`backend/tests/`) + Node test runner (`frontend/tests/`)
- Verification scripts: `docs/data/neo4j/scripts/verify_phase8_integrity.py`
- Test case format: Automated pytest test cases with testRunId isolation against Neo4j AuraDB

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Order to Tracking Lifecycle with Provenance | F2, F3, F4, F5, F7 | High |
| 2 | OSRM Driving Route Calculation with Central EPC Origin | F3, F5, F6 | Medium |
| 3 | Multi-Domain Health & Status Inspection | F1, F7, F8 | Medium |
| 4 | Concurrency Stress & Optimistic Lock Invariance | F6, F9 | High |
| 5 | Live AuraDB Graph Integrity Sweep Across European Boundaries | F5, F6, F9 | High |

## Coverage Thresholds
- Tier 1: >=5 per feature (>= 45 tests)
- Tier 2: >=5 per feature where boundaries exist (>= 45 tests)
- Tier 3: pairwise coverage of major feature interactions (>= 9 tests)
- Tier 4: >=5 realistic application scenarios
