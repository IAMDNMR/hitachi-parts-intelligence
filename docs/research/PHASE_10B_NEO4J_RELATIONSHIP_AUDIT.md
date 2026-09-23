# Phase 10B — Neo4j Graph & Relationship Audit

Live Neo4j AuraDB, audited 2026-09-23 via `docs/data/neo4j/scripts/phase10_data_audit.py` and direct
Cypher inspection. All counts are from the running database, not from memory of earlier phases.

## 1. Node inventory

| Label | Count | Classification |
|---|---|---|
| Part | 60 | SOURCE_DERIVED |
| Machine | 77 | SOURCE_DERIVED |
| DealerBranch | 182 | SOURCE_DERIVED |
| Depot | 1 | SOURCE_DERIVED |
| **Supplier** | **1,730** | **1,720 REAL** (HCME SAP supplier master) + 10 SYNTHETIC_DEMO (fictional demo suppliers used only where no part-level source exists) |
| City | 926 | DERIVED (built from the real dealer/supplier/depot location fields) |
| Country | 56 | DERIVED |
| Assembly | 833 | SYNTHETIC_DEMO (BOM structure; assembly *names* are 1:1 from real fitment data) |
| ComplianceRequirement | 6 | 1 SOURCE_DERIVED (EU Battery Regulation, SRC-039) + 5 SYNTHETIC_DEMO |
| Category / Application / Service / Specification / Attachment / DigitalService / Channel | 17 / 29 / 22 / 1,635 / 17 / 8 / 2 | SOURCE_DERIVED |
| Order / FulfilmentRequest / Allocation / FulfilmentOption / InventoryCache / InventorySnapshot / CatalogEntry / CustomsContext | 3 / 3 / 3 / 3 / 5 / 39 / 3 / 1 | SYNTHETIC_DEMO |
| Shipment / ShipmentEvent / ServiceJob / ServiceEvent | 2 / 5 / 4 / 18 | SYNTHETIC_DEMO |
| Customer / PartsInquiry / RequestedPart | 1 / 1 / 1 | real quote submission (not synthetic) |
| AuditRecord / IdempotencyRecord | 694 / 21 | INTERNAL_REFERENCE_ONLY |

## 2. Relationship inventory

| Relationship | From | To | Count | Provenance | Supported? | Notes |
|---|---|---|---|---|---|---|
| HAS_PART_FITMENT | Machine | Part | 1,041 | SOURCE_DERIVED | yes | every edge carries source_id + confidence |
| HAS_ASSEMBLY | Machine | Assembly | 833 | SYNTHETIC_DEMO | yes (labelled) | BOM structure |
| CONTAINS_PART | Assembly | Part | 1,041 | SYNTHETIC_DEMO | yes (labelled) | quantity is synthetic; part/machine pairing matches fitment 1:1 |
| **SUPPLIED_BY** | Part | Supplier | 73 | SYNTHETIC_DEMO | yes (labelled) | **only ever points at the 10 synthetic demo suppliers — 0 edges to a REAL (HCME_SAP_SUPPLIER_MASTER) supplier; verified by DQ-40** |
| LOCATED_IN | Supplier | City | 1,720 | SOURCE_DERIVED | yes | from supplier master city/country |
| LOCATED_IN | DealerBranch | City | 155 | SOURCE_DERIVED | yes | |
| IN_COUNTRY | DealerBranch | Country | 27 | SOURCE_DERIVED | yes | dealers with no city on file link straight to Country |
| LOCATED_IN | Depot | City | 1 | SOURCE_DERIVED | yes | Oosterhout |
| IN_COUNTRY | City | Country | 926 | DERIVED | yes | |
| REQUIRES_COMPLIANCE | Assembly | ComplianceRequirement | 1,692 | SYNTHETIC_DEMO | yes (labelled) | the regulations are real EU instruments; the assignment is synthetic |
| HAS_CERTIFICATION | Part | ComplianceRequirement | 73 | SYNTHETIC_DEMO | yes (labelled) | |
| HAS_COMPLIANCE_REQUIREMENT | Part | ComplianceRequirement | 7 | mixed | yes | 3 real (EU Battery Reg on PT-001..003), 4 synthetic |
| DEPENDS_ON | ComplianceRequirement | ComplianceRequirement | 2 | SYNTHETIC_DEMO | yes | |
| HAS_ORDER | FulfilmentRequest | Order | 3 | SYNTHETIC_DEMO | yes | |
| HAS_SHIPMENT | Order | Shipment | 2 | SYNTHETIC_DEMO | yes | |
| **HAS_SERVICE_JOB** | Shipment | ServiceJob | 2 | SYNTHETIC_DEMO | yes | **the real graph shape `create_service_job()` produces is Order‑\[:HAS_SERVICE_JOB\]→ServiceJob AND Shipment‑\[:HAS_SERVICE_JOB\]→ServiceJob AND FulfilmentRequest‑\[:HAS_SERVICE_JOB\]→ServiceJob (all three); the hand‑seeded demo data only ever wrote the Shipment edge — see PHASE_10B_BUSINESS_FLOW_VALIDATION.md §1 for the bug this caused and its fix** |
| PERFORMS_SERVICE | DealerBranch | ServiceJob | 4 | SYNTHETIC_DEMO | yes | |
| HAS_EVENT | ServiceJob | ServiceEvent | 18 | SYNTHETIC_DEMO | yes | |
| HAS_EVENT | Shipment | ShipmentEvent | 5 | SYNTHETIC_DEMO | yes | restored this session — see §3 |
| SHIPPED_TO | Shipment | DealerBranch | 2 | SYNTHETIC_DEMO edge / real DealerBranch | yes | |
| SOURCED_FROM | Allocation | Supplier / Depot | 1 / 2 | SYNTHETIC_DEMO | yes | |
| SUBMITTED | Customer | PartsInquiry | 1 | real | yes | existing Quote Request flow, untouched |
| REQUESTS | PartsInquiry | RequestedPart | 1 | real | yes | |
| FOR_PART | RequestedPart / ServiceJob / Service / Attachment | Part | 1 / 4 / 11 / 1 | mixed | yes | |
| **REQUESTED** *(new)* | Customer | FulfilmentRequest | 0 in the live graph today | real, when captured | yes | added this session — see §4; no requests carried a requester identity before this fix, so 0 is expected until the new UI field is used |

## 3. Relationships explicitly NOT created (per instruction §5/§6/§20)

None of the following exist in the graph, and the audit (DQ-40/41/42) now fails the build if they ever
appear:

- `Supplier -[:SUPPLIES]-> Part` from a REAL supplier — the supplier master has no part numbers.
- `Supplier -[:SUPPLIES]-> DealerBranch` or `-[:SERVES]->` — dealer/supplier co-location is answered
  purely through the shared `City`/`Country` nodes (`LOCATED_IN`/`IN_COUNTRY`), never a direct edge.
- `Supplier -[:SUPPLIES]-> Depot` — no authoritative source exists.

The only `Part -[:SUPPLIED_BY]-> Supplier` edges in the graph (73) all point at the 10 **synthetic**
demo suppliers seeded in the previous session, never at a real supplier-master record. This is
verified live by check DQ-40 in the data-quality audit, not asserted from memory.

## 4. Fix applied this session: ShipmentEvent restoration

`ship-demo-001`/`ship-demo-002` (hand-seeded synthetic shipments) had lost their `ShipmentEvent` trail
between the previous session's closure report (which recorded 10 events) and this audit (0 events);
the root cause could not be reconstructed from any script in the repo — these records were created
once, directly in Cypher, outside any committed seed script. `Shipment.order_id` was also `null` on
both, even though the real `HAS_SHIPMENT` edge to the correct Order existed.

Fixed by `docs/data/neo4j/scripts/phase10b_repair_demo_journey.py`: restated each shipment's own
already-recorded status as its own `ShipmentEvent` log (CREATED/DISPATCHED/DELIVERED, using the
shipment's own origin/destination/carrier fields — nothing new is asserted), and set `order_id` from
the real edge. 5 ShipmentEvents restored, 2 `order_id` fixed. Both are labelled `synthetic: true`,
`data_source: 'SYNTHETIC_DEMO'`.

## 5. Requester (Customer) capture — new this session

Previously every `FulfilmentRequest` used the hardcoded default `customer_id: "CUST-DEFAULT"`. The
Parts Store ordering flow now asks for the requester's name and email (`AvailabilityChecker.tsx`) and
`POST /api/v1/fulfilment-requests` persists it as `(:Customer {email})-[:REQUESTED]->(:FulfilmentRequest)`
in Neo4j, reusing the existing Customer node shape (the Quote Request flow already writes
`(:Customer)-[:SUBMITTED]->(:PartsInquiry)`), and the FulfilmentRequest's `customerId` becomes the real
email instead of the placeholder. Backward compatible: omitting the fields keeps the old default.
