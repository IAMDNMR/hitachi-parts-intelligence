# Data Quality Report

| Dataset | Source rows | Clean rows | Duplicates merged |
|---|---|---|---|
| categories | 17 | 17 | 0 |
| machines | 77 | 77 | 0 |
| specifications | 1635 | 1635 | 0 |
| applications | 328 | 328 | 0 |
| attachments | 17 | 17 | 0 |
| parts | 43 | 43 | 0 |
| machine_part_fitment | 944 | 944 | 0 |
| services | 22 | 22 | 0 |
| machine_service | 1694 | 1694 | 0 |
| maintenance | 10 | 10 | 0 |
| service_part_requirements | 11 | 11 | 0 |
| digital_services | 616 | 616 | 0 |
| relationships | 3283 | 3283 | 0 |
| provenance | 47 | 47 | 0 |
| data_quality | 40 | 40 | 0 |

Fitment conflicts requiring review: 0
Machine-service conflicts requiring review: 0
Dangling foreign keys found: 0
Scope-descriptor values (not real IDs, not counted as dangling): 12

## Fitment evidence breakdown
- EXACT_MODEL: 37
- MODEL_RANGE: 31
- CATEGORY: 876

## Relationship classification (13_AFTER_SALES_RELATIONSHIPS)
- CORE: 169
- DERIVED: 3097
- INVALID: 17

## Scope-descriptor values (source states a scope in prose instead of an ID — not a data defect)
- machine_part_fitment / FIT-0032: Machine ID='NOT IN CURRENT CATALOGUE'
- service_part_requirements / SPR-001: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-002: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-003: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-004: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-005: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-006: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-007: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-008: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-009: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-010: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'
- service_part_requirements / SPR-011: Machine ID='ALL machines in the service scope - see 09_MACHINE_SERVICE_MATRIX'