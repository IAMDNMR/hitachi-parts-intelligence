# E2E Test Infra: HCME After-Sales Data Foundation

## Test Philosophy
- **Opaque-box, requirement-driven**: All test assertions derive strictly from `ORIGINAL_REQUEST.md` and user-facing specifications, never from implementation design or internal script internals.
- **Strict Neo4j Isolation Assertion**: Every test run asserts zero outbound network sockets to Neo4j Aura (port 7687) and zero database credentials or drivers loaded.
- **Methodology**: 4-Tier Opaque-Box Testing:
  1. Tier 1: Feature Coverage (≥5 test cases per feature covering equivalence class representatives)
  2. Tier 2: Boundary Value Analysis & Corner Cases (limits, empty inputs, sentinel values, extreme sizes)
  3. Tier 3: Cross-Feature Combinations & Referential Graph (pairwise interactions, foreign key graph)
  4. Tier 4: Real-World Workload Scenarios (end-to-end extraction, multi-sheet reconciliation, double-run determinism)

## Feature Inventory & Test Coverage
| # | Feature | Source Requirement | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|--------------------|:------:|:------:|:------:|:------:|
| 1 | 21-Sheet Source Audit | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ | ✓ |
| 2 | Source Workbook Immutability | ORIGINAL_REQUEST R1, R5 | 5 | 5 | ✓ | ✓ |
| 3 | Duplicate ID & Row Detection | ORIGINAL_REQUEST R1, R4 | 5 | 5 | ✓ | ✓ |
| 4 | URL & Noise Flagging | ORIGINAL_REQUEST R1, R2 | 5 | 5 | ✓ | ✓ |
| 5 | Category Hierarchy Normalization | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 6 | Machine Catalogue Disambiguation | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 7 | Specification Technical Filtering | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 8 | Sentinel Null Sanitization | ORIGINAL_REQUEST R2, R5 | 5 | 5 | ✓ | ✓ |
| 9 | Application Canonicalization | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 10 | Attachment Hygiene & Types | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 11 | Parts Master Segregation | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 12 | Controlled Fitment Vocabulary | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 13 | Fitment Conflict Isolation | ORIGINAL_REQUEST R2, R4 | 5 | 5 | ✓ | ✓ |
| 14 | Service Capabilities & Location | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 15 | Machine Service Matrix | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 16 | Maintenance Schedule Intervals | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 17 | Service Part Requirements | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 18 | Digital Services Telematics | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 19 | Relationship Classification | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ | ✓ |
| 20 | Provenance URL Isolation | ORIGINAL_REQUEST R2, R5 | 5 | 5 | ✓ | ✓ |
| 21 | Master Excel Generation (17 sheets) | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ | ✓ |
| 22 | 14 Relational CSV Export | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ | ✓ |
| 23 | Data Quality Report Generation | ORIGINAL_REQUEST R4 | 5 | 5 | ✓ | ✓ |
| 24 | Cleanup Audit Log Generation | ORIGINAL_REQUEST R4 | 5 | 5 | ✓ | ✓ |
| 25 | Schema Candidates Report | ORIGINAL_REQUEST R4 | 5 | 5 | ✓ | ✓ |
| 26 | Referential Integrity FK Graph | ORIGINAL_REQUEST R5 | 5 | 5 | ✓ | ✓ |
| 27 | Deterministic Sort Enforcement | ORIGINAL_REQUEST R5 | 5 | 5 | ✓ | ✓ |
| 28 | Zero URL Leakage in Core CSVs | ORIGINAL_REQUEST R5 | 5 | 5 | ✓ | ✓ |
| 29 | Double-Run Byte Determinism | ORIGINAL_REQUEST R5 | 5 | 5 | ✓ | ✓ |
| 30 | Strict Neo4j Isolation Guardrail | ORIGINAL_REQUEST R6 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Runner**: `tests/test_e2e_harness.py`
- **Invocation**: `python tests/test_e2e_harness.py [--tier 1|2|3|4|all] [--verbose]`
- **Pass/Fail Semantics**: Returns exit code 0 if 100% of tests in requested tier pass; non-zero if any failure occurs.
- **Verification mechanism**:
  - Validates outputs on disk (`.xlsx`, `.csv`, `.md`).
  - Reads outputs using openpyxl, standard library `csv`, and hashlib.
  - Zero external mock libraries or intrusive monkey patching.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Pre-Cleaning Audit Workflow | F1, F2, F3, F4, F30 | High |
| 2 | End-to-End Extraction & Referential Validation | F5-F22, F26, F27, F28 | Very High |
| 3 | Full Data Reconciliation & Reporting Integrity | F23, F24, F25, F13 | High |
| 4 | Consecutive Pipeline Runs Determinism Validation | F2, F27, F29 | High |
| 5 | Network & Driver Isolation Audit | F30 | Medium |

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (30 features × 5 = 150 tests)
- Tier 2: ≥5 test cases per feature boundary (30 features × 5 = 150 tests)
- Tier 3: Major pairwise foreign key interactions (≥30 combination tests)
- Tier 4: ≥5 end-to-end application workload scenarios
- **Total Minimum Threshold**: ~335 test cases
