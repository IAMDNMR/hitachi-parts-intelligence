# Phase 12 — Data Provenance and Parts Intelligence KPI / Score Audit

**Audit only. No application code, Neo4j data, catalogue data, KPI, score, eligibility or UI was changed.** Every statement below was traced from the
code, the source CSV/registry files in `docs/data/neo4j/data/`, the seed/import scripts, and live queries against the running Aura graph and API
(2026-09-24). Where something is questionable it is recorded under *Findings / Limitations / Follow-up* (§10), not silently fixed.

Terminology (existing project terms): **REAL** · **SOURCE_DERIVED** · **DERIVED** · **SYNTHETIC_DEMO** · **TEST_DATA** · **INTERNAL_REFERENCE_ONLY** ·
**UNKNOWN** · **NOT_CONNECTED**. For scores/KPIs additionally: **HEURISTIC** · **HARDCODED** · **LLM_GENERATED**.

---

## Executive Table A — Data truth

| Data domain | Real / Source-derived | Synthetic demo | Derived | Not connected | Notes |
|---|---|---|---|---|---|
| Machines (77) | 77 (SRC-014 official HCME product pages) | 0 | machine type (12 `MachineType`, 77 `OF_TYPE`) | — | Specs: 1,635 published spec rows |
| Parts (60) | 20 orderable batteries (SRC-039, HIGH); 23 product-line families (official pages, no part number) | 0 | — | — | **17 are INTERNAL_REFERENCE_ONLY**: 10 internally generated (SRC-048, LOW) + 7 source-mismatch (SRC-042, LOW) — never verified |
| Machine → Part fitment (1,496) | 37 EXACT_MODEL (SRC-039); 28 MODEL_RANGE (SRC-042, official page but source mismatch) | — | 1,331 CATEGORY-level + 30 MODEL_RANGE "derived from official source"; 70 MODEL_RANGE internally generated (SRC-048) | — | **Only 2.5 % of fitments name an exact model** (see §10) |
| Dealers (182) | 182 (SRC-049 official dealer-locator feed, HIGH) | 0 | GPS: taken from the feed; 4 flagged (DQ-06) | — | 7 of the Netherlands "dealers" are account managers (no type field in source) |
| Suppliers | 1,720 (HCME SAP supplier master export: number, name, city, country) | 10 demo suppliers | City/Country links | **Supplier → Part (real)** | 73 `SUPPLIED_BY` links, all SYNTHETIC_DEMO |
| Depot (1) | Oosterhout facility facts (SRC-050 news article) | — | — | live stock at the depot | Node itself states it is not a stock feed |
| Assemblies / BOM / criticality | 0 | 1,206 assemblies, 1,496 `CONTAINS_PART`, criticality rules | — | HCME engineering BOM | Built from real fitment with invented quantities |
| Compliance | Regulation names (real EU instruments) | Assembly requirements (1,855), certificates (76) incl. expiry dates | — | HCME compliance evidence | 3 of 7 part-level compliance edges are not flagged synthetic (EU Battery Regulation, SRC-039) |
| Stock | — | 39 snapshots (37 of 60 parts) | — | live stock/WMS | |
| Prices | — | — | — | **NOT_CONNECTED** (`NOT_AVAILABLE`) | Order pricing provider never returns a number |
| Transport (options, cost, ETA) | — | deterministic rate card + distance bands | straight-line distance | carrier/TMS | |
| Orders / shipments / service | — | 3 seeded demo orders | — | SAP ERP, TMS, dealer DMS | + 3 orders created by Parts Store browser tests (`INTERNAL_TEST_WORKFLOW`) |
| Customers / installed base | — | — | — | **NOT_CONNECTED** | No demo customers exist any more |
| Question catalogue (34) | — | — | run-and-verified against the app | — | Templates stored in Aura, wired to real nodes |

## Executive Table B — Parts Intelligence numbers, KPIs and scores

| KPI / score | Current value example | Source | Calculation | Range | Deterministic? | Synthetic inputs? | Flag |
|---|---|---|---|---|---|---|---|
| Card **match %** (chat part cards) | Batteries: PT-020 100 %, PT-014 100 %, PT-001 100 % | `part_finder.find_parts` over `MATCH (p:Part)` | term coverage × field weight (§6.1) | 0–100 (results < 50 hidden) | Yes | No | **HEURISTIC** (all 10 batteries score 100 %) |
| Card **Fits N machines** | PT-020: 11, PT-031: 67 | count of `HAS_PART_FITMENT` | `len(models)` | 0–77 | Yes | No, but **89 % of edges are category-level** | SOURCE_DERIVED / DERIVED |
| **Similarity %** in Graph Insights › Mitigation and in chat "alternatives" | PT-007 → PT-015: 74 % | `scoring.calculate_compatibility_score` | fixed-weight sum (§6.2) | 0–100 | Yes | No | **HARDCODED weights, HEURISTIC** |
| **Text similarity %** in Similar Parts tab | PT-007 → PT-015: 95 % | `similarity.similar_parts` | cosine of local hashed-text embeddings | 0–100 | Yes | No | **HEURISTIC — different formula, same word** (§10 F-1) |
| **Mitigation score** (Graph Insights) | PT-015: 60 | `scoring.calculate_mitigation_score` | 0.40 compat + 0.30 availability + 0.20 compliance + 0.10 source risk | 0–100 | Yes | **Yes** (stock, certificates) | **HARDCODED, SYNTHETIC_DEMO inputs** |
| **Affected machines** | PT-007: 4; PT-031: 67 | `_IMPACT_Q` (fitment via BOM) | distinct machines | 0–77 | Yes | Assembly link is synthetic | DERIVED |
| **Total BOM qty** | PT-007: 7 | `CONTAINS_PART.quantity` | sum | ≥ 0 | Yes | **Yes** | **SYNTHETIC_DEMO** |
| **Critical paths** | PT-007: none | `Assembly.criticality = 'high'` | filter | count | Yes | **Yes** | **SYNTHETIC_DEMO** |
| **Compliance status** | PT-007: GAPS_FOUND | `_COMPLIANCE_Q` | requirement without `HAS_CERTIFICATION` edge = gap | 3 states | Yes | **Yes** (except battery regulation) | SYNTHETIC_DEMO |
| **Supplier risk** | NOT_CONNECTED | `_VERIFIED_PART_SUPPLIERS_Q` | real SAP links only → none exist | 2 states | Yes | No | NOT_CONNECTED (correct) |
| **KPI: order traceability** | 2 of 2 (100 %), 3 test orders excluded | `kpis.order_traceability` | seeded demo orders (browser-test orders excluded) with request+allocation+part+shipment+dealer+service link | 0–100 % | Yes | Yes (demo/test orders) | SYNTHETIC_DEMO / TEST_DATA |
| **KPI: master-data consistency** | 2,313 of 2,341 (98.8 %) | `kpis.master_data_consistency` | 7 completeness checks summed | 0–100 % | Yes | No | DERIVED (dominated by 1,720 suppliers) |
| **KPI: supplier-to-part coverage** | 0 of 60 real (0 %); demo links 60 of 60 shown separately | `kpis.supplier_part_coverage` | parts with a link to a real SAP supplier | 0–100 % | Yes | No | REAL (correctly 0) |
| **KPI: stock-out exposure** (DEMO) | 6 of 37 (16.2 %) | `kpis.stock_out_exposure` | orderable parts (product-line families excluded) with no/zero demo snapshot | 0–100 % | Yes | **Yes** | **SYNTHETIC_DEMO — reflects the seed** |
| **"Workflow Execution · 3.71s"** | 0.19–9 s | `pipeline.timings_ms` | wall-clock `perf_counter` | ≥ 0 | No (measured) | No | REAL (latency) |
| **"answer by Gemini / graph rules"** | "answer by Gemini from graph evidence" | `pipeline.answer` | which writer produced the wording | 2 values | — | — | LLM_GENERATED **text only** (§6.6) |

---

## 1. Data provenance table (all major data)

Source registry: `docs/data/neo4j/data/provenance.csv` (SRC-001 … SRC-050, "Official Source" column). "Official = Yes" means the page is published by HCME; it does **not**
by itself mean every derived record is verified.

| Area | Data / Entity | Example | Source | Data classification | Real / Synthetic | Used where | Provenance / notes |
|---|---|---|---|---|---|---|---|
| Master | Machine | MC-033 ZX210LC-7 | `machines.csv` ← official product pages (SRC-014); 77 nodes, all `OFFICIAL WEBSITE DATA` | SOURCE_DERIVED | Real | Fitment, Parts Store machine filter, PI | Built from `HITACHI_AFTERSALES_ECOM_GRAPH_MASTER.xlsx` (sheet 1_MACHINE_MASTER) via `scripts/gen-machine-catalogue.py`; manually researched web capture dated 2026-09-10 |
| Master | Machine specifications | weight, power | `specifications.csv` (1,635 rows) → `HAS_SPECIFICATION` | SOURCE_DERIVED | Real | Machine info answers | Published spec rows |
| Master | Machine images | 339 official images | `MACHINE_IMAGE_MANIFEST.xlsx` | SOURCE_DERIVED | Real | Parts Store / site | Official HCME imagery |
| Master | Part (orderable OEM battery) | PT-001, 4663907 | `parts.csv` SRC-039 battery compliance page, confidence HIGH, `ORDERABLE_OEM_PART` | SOURCE_DERIVED | Real | Store checkout ("Ready for fulfilment"), PI | 20 parts |
| Master | Part (product-line family) | PT-029 Genuine Engine Oil DH-2 | `parts.csv` SRC-016/027/030–038, HIGH, `PRODUCT_LINE_PART_FAMILY` | SOURCE_DERIVED | Real | Store (family), PI | 23 records, **no part number** — not orderable SKUs |
| Master | Part (internally generated) | PT-044..PT-053 (e.g. 4621008) | `parts.csv` SRC-048 "Internally generated / AI-illustrated — not an HCME publication", LOW | INTERNAL_REFERENCE_ONLY | Not verified | Store (demo order only), PI | 10 records; numbers unverified |
| Master | Part (source mismatch) | PT-054..PT-060 (e.g. 12345678) | `parts.csv` SRC-042 (dealer-network page, not a parts catalogue), LOW, `UNVERIFIED - SOURCE MISMATCH` | INTERNAL_REFERENCE_ONLY | Not verified | Store (demo order only), PI | 7 records |
| Master | Part number / description | 4663907 | same rows as above | as per row | as per row | Everywhere | Do not treat "Hitachi" in a name as verification |
| Master | Part categories / sub-categories | Electrical / Battery | `parts.csv` columns | SOURCE_DERIVED | Real | Search, gate | Sub-category is coarse; `interchangeability.type_key` refines Filter/Battery from the name (DERIVED) |
| Master | Machine → Part fitment | ZX10U-6 → PT-001 | `machine_part_fitment.csv` (1,071 rows) + `phase10f_fill_fitment_gaps.py` (+455) | SOURCE_DERIVED / DERIVED | Real / derived | Impact, "Fits N", gate, KPIs | 37 EXACT_MODEL (SRC-039), 128 MODEL_RANGE, **1,331 CATEGORY-level**; the 455 added in Phase 10F are CATEGORY-level derived from each part's own "stated applicability" text |
| Master | Dealer branch (name, address, phone, e-mail) | DLR-122 Pellen Machines Veldhoven BV | `dealers.csv` ← SRC-049 dealer-locator JSON feed (public request made by the official page), HIGH, accessed 2026-09-23 | SOURCE_DERIVED | Real | Dealer answers, nearest dealer, checkout dealer list | `import_dealers.py`; 182 nodes; account managers appear as entries (no type field) |
| Master | Dealer GPS | 57.4909091, −4.227441 | Same feed (Latitude/Longitude columns) | SOURCE_DERIVED | Real | Distance ranking | 181 usable; DLR-043 has no latitude; DLR-066/116/130 are overseas territories (audit DQ-06) |
| Master | Dealer location link | Dealer → City → Country | `import_dealers.py` / `import_sap_suppliers.py` | DERIVED | Derived from address fields | Geographic answers | 926 `City`, 53 `Country` nodes |
| Master | Supplier (SAP master) | 0000100026 THORBURN GEIGER SA, Lausanne, CH | `20260609_Source data for Supplier.xlsx` (SAP S/4HANA migration template, "General Data"); `import_sap_suppliers.py`; `data_source = HCME_SAP_SUPPLIER_MASTER`, `synthetic=false` | REAL | Real | Supplier answers, supplier tab counts | Number, name, city, country only; city/country normalised (raw kept); 22 duplicate-name pairs flagged |
| Master | Supplier location | Supplier → City → Country | derived from the file's city/country | DERIVED (geographic) | Derived | "Suppliers in Germany", co-location | Not a supply relationship |
| Master | Oosterhout depot | Hitachi European Parts Centre | SRC-050 news article ("A future-proof parts warehouse…"), `OFFICIAL WEBSITE DATA` | SOURCE_DERIVED | Real (facility facts only) | Fulfilment source, KPIs (customs origin) | Node note: not a live inventory feed |
| Master | Part images (Parts Store) | `battery-4663907.webp` | `frontend/data/partsStoreCatalogue.ts` `imageSource` strings | mixed | see notes | Store cards | 12 items say "Internally sourced image — not official Hitachi/HCME publication photography"; others cite HCME pages/studio cuts (not independently verified in this audit) |
| Master | Store catalogue (57 items) | id `battery-4663907` | `frontend/data/partsStoreCatalogue.ts` — "GENERATED FILE", `scripts/gen-parts-store-catalogue.py` (header text says 45 items; the file holds 57) | SOURCE_DERIVED / INTERNAL_REFERENCE_ONLY per item | mixed | Parts Store | `provenanceStatus` marks 12 unverified items; `source` per item names the page or SRC-048 |
| Master | Machine type / part type | MachineType "Medium Excavators" | `load_question_catalog.py` (`OF_TYPE`, 137 edges) | DERIVED | Derived | Catalogue wiring | Derived from existing categories |
| Derived | Part embeddings (256-d) | `Part.embedding` | `similarity.write_embeddings` (local hashed text) | DERIVED | Derived | Similar/hybrid search | Not a neural model |
| Derived | Question templates | 34 `QuestionTemplate` | `catalog_spec.py` → CSV → Aura | DERIVED | Verified by running the app | Question catalogue | Wired to real nodes (`ABOUT_*`) |
| Synthetic | Assemblies, BOM, criticality | `ASM-MC-023-fuel-system`, high | `seed_phase10_demo_data.py --step bom` | SYNTHETIC_DEMO | Synthetic | Impact tab, disruption | Name and machine from real fitment; quantity and criticality invented by rules |
| Synthetic | Demo suppliers and `SUPPLIED_BY` | Demo Battery Supplier → 20 parts | `seed_phase10_demo_data.py --step suppliers` | SYNTHETIC_DEMO | Synthetic | Supply-chain answer, disruption | 73 links, 10 suppliers |
| Synthetic | Compliance requirements/certificates | `COMP-DEMO-STAGE-V` | `seed_phase10_demo_data.py --step compliance`; `valid_until` from `phase11_seed_pavan_gaps.py` | SYNTHETIC_DEMO | Synthetic (regulation names real) | Compliance tab, verdicts | 1,855 assembly requirements, 76 certificates |
| Synthetic | Stock snapshots | `INV-DEMO-001` 17 units | `seed_phase10_demo_data.py --step inventory` | SYNTHETIC_DEMO | Synthetic | Availability, supply chain, KPIs | 39 snapshots |
| Test | Orders | `order-demo-001`, `order-<uuid>` | `seed_operational_demo_data.py` (3, `SYNTHETIC_DEMO_KPI_WORKFLOW`) and Parts Store browser tests (3, `INTERNAL_TEST_WORKFLOW`) | SYNTHETIC_DEMO / TEST_DATA | Synthetic | Order answers, KPIs | |
| Not connected | Prices, live stock, carrier, ERP, DMS, supplier→part, customers | — | — | NOT_CONNECTED | — | Labelled in UI | `PRICING_PROVIDER=test` returns `NOT_AVAILABLE` |

---

## 2. Parts Store data — original / source-derived

| Dataset | Exact source | Real vs source-derived | How obtained | Confidence / provenance in data |
|---|---|---|---|---|
| Parts (60) | `docs/data/neo4j/data/parts.csv` → Aura `Part`; front-end copy `frontend/data/partsStoreCatalogue.ts` (57 store items) | 43 SOURCE_DERIVED (20 + 23), 17 INTERNAL_REFERENCE_ONLY | Manually researched capture of official HCME pages on 2026-09-10 (SRC-016…SRC-039); 17 added later internally (SRC-048/SRC-042) | `Confidence` HIGH (43) / LOW (17), `Data Class`, `Source ID`, `record_class` |
| Part numbers | `parts.csv` "Part Number" | Real for 20 batteries (printed on the official battery compliance page, SRC-039); unverified for 17; absent for 23 families | Web capture | as above |
| Descriptions | `parts.csv` "Description" | SOURCE_DERIVED (composed from the page text: "Battery published on the HCME battery compliance page… Fitted model groups as printed…") | Web capture, wording edited | HIGH/LOW per row |
| Machine models (77) | `machines.csv` | SOURCE_DERIVED | official product pages SRC-014 | `OFFICIAL WEBSITE DATA` |
| Fitments (1,496) | `machine_part_fitment.csv` + Phase 10F script | see §1 | evidence column: `EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY` | `Data Class` per edge |
| Dealers (182) | `dealers.csv` | SOURCE_DERIVED | public JSON feed behind the official dealer locator (SRC-049), 2026-09-23 | HIGH |
| Dealer coordinates | same file | SOURCE_DERIVED | supplied by the feed | 4 anomalies audited |
| Suppliers (1,720) | Excel export, `import_sap_suppliers.py` | REAL (given to the project) | SAP supplier master extract dated 2026-06-09 | `HCME_SAP_SUPPLIER_MASTER` |
| Depot | SRC-050 | SOURCE_DERIVED (facility facts) | official news article | — |
| Images | `frontend/assets/parts/**`, `imageSource` field | mixed; see §1 | some official, 12 internal | `imageSource` string only (no per-image hash/licence record) |
| Categories | `categories.csv` (17) + `parts.csv` | SOURCE_DERIVED | official pages | — |
| OEM references / provenance | `provenance.csv` (50 sources) | REAL registry | manually maintained | "Official Source" Yes/No |

Manually researched: all `OFFICIAL WEBSITE DATA` rows (web capture, 2026-09-10 / 2026-09-23). Internally derived: `INTERNALLY GENERATED DATA` (SRC-048), fitment
`CATEGORY`/`DERIVED FROM OFFICIAL SOURCE` rows, `type_key`, embeddings, machine/part types, question catalogue.

## 3. Parts Store synthetic (operational demo) data

**Master data** = catalogue facts (machines, parts, fitment, dealers, suppliers). **Operational demo data** = anything that would come from live commercial
systems (stock, price, orders, shipments, service). Operational data below is SYNTHETIC_DEMO / DEMO / SIMULATED.

| Data | Example | Where generated | Classification | Why synthetic | Used in demo |
|---|---|---|---|---|---|
| Inventory / stock | 17 units of PT-001 at Oosterhout | `seed_phase10_demo_data.py` → `InventorySnapshot`; read by `synthetic_inventory_adapter.py` | SYNTHETIC_DEMO | No stock feed exists | Availability (Stage 4), supply chain, stock-out KPI |
| Availability response | `overall_status: AVAILABLE`, sources with provenance | `availability` module + `synthetic_inventory_adapter` (test scenarios for numbers outside the graph) | SYNTHETIC_DEMO | Reads demo snapshots; `TestInventoryProvider` for other numbers | Stage 4 |
| Transport options, cost, transit time, ETA | Road/Rail/Air EUR options | `modules/transport/rate_card.py` + `engine.py` ("Deterministic European Rate Card", `data_class="SYNTHETIC_DEMO"`) | SYNTHETIC_DEMO | Rates and speeds are configured constants; distance is straight-line (haversine) from real coordinates | Stage 5 |
| Pricing | `pricingStatus: NOT_AVAILABLE`, no unit price | `integrations/mocks/pricing_mock.py` | NOT_CONNECTED | Never fabricates a number | Order review |
| Demo orders / allocation | `order-…`, `alloc-…` | `order`/`allocation` services with `TestOrderProvider` (`data_source='SYNTHETIC_DEMO'`, `synthetic=true`) | SYNTHETIC_DEMO | ERP not connected | Stage 6–7 |
| Shipment / tracking | `DEMO-TRK-…`, carrier "Demo European Logistics Partner" | `shipment` module, `shipment_mock.py`, `tracking_mock.py` | SYNTHETIC_DEMO | TMS/carrier not connected | Stage 7 |
| Customs context | `CustomsContext` on the GB shipment | `seed_operational_demo_data.py` | SYNTHETIC_DEMO | Rule-based demo | Customs rule check |
| Dealer service events / work orders / installation milestones | `WO-EU-…`, `[SIMULATED] Installation Milestone Recorded` | `service` module + `service_mock.py`; UI wording via `simulatedEvents.ts` | SYNTHETIC_DEMO | Dealer DMS not connected; stored text says "physically installed" — never shown | Stage 7 |
| Demo part references | `DEMO-WHEEL-LOADER-BUCKET` | UI `eligibility.demoPartReferenceFor`; backend `is_demo_part_number` | SYNTHETIC_DEMO | Store items with no verified number run the lifecycle with a labelled reference | Store → demo order |
| Supplier links, BOM, certificates | see §1 | seed scripts | SYNTHETIC_DEMO | | PI |

## 4. Parts Intelligence data (what the query layer actually uses)

| Entity | Example | Neo4j label | Source | Classification | Relationship | Used for |
|---|---|---|---|---|---|---|
| Part | PT-045 | `Part` (60) | `parts.csv` | SOURCE_DERIVED / INTERNAL_REFERENCE_ONLY | — | search, cards, gate |
| Machine | ZX210LC-7 | `Machine` (77) | `machines.csv` | SOURCE_DERIVED | `(Machine)-[:HAS_PART_FITMENT]->(Part)` — **ACTUAL** (source-derived) | "Which machines use…", "Fits N" |
| Machine spec | operating weight | `Specification` (1,635) | `specifications.csv` | SOURCE_DERIVED | `(Machine)-[:HAS_SPECIFICATION]->` — ACTUAL | machine info |
| Machine type | Medium Excavators | `MachineType` (12) | derived | DERIVED | `(Machine)-[:OF_TYPE]->` — DERIVED | catalogue wiring |
| DealerBranch | Pellen Machines | `DealerBranch` (182) | SRC-049 | SOURCE_DERIVED | `-[:LOCATED_IN]->(City)` — DERIVED from address | dealer answers |
| Supplier | 0000100026 | `Supplier` (1,730) | SAP master (1,720) + demo (10) | REAL / SYNTHETIC_DEMO | `-[:LOCATED_IN]->(City)` — DERIVED from file | supplier answers |
| Depot | Oosterhout | `Depot` (1) | SRC-050 | SOURCE_DERIVED | `-[:LOCATED_IN]->(City)` — DERIVED | depot co-location, fulfilment |
| City / Country | Veldhoven / NL | `City` (926), `Country` (53) | derived from dealer + supplier addresses | DERIVED | `(City)-[:IN_COUNTRY]->(Country)` — DERIVED | geographic joins |
| Dealer ↔ Supplier | "same city as Pellen" | — | — | **DERIVED GEOGRAPHIC only** | `DealerBranch -[:LOCATED_IN]-> City <-[:LOCATED_IN]- Supplier` | "SAME CITY — DERIVED; no commercial relationship implied" (stated in every answer) |
| Supplier → Part | Demo Battery Supplier → PT-001 | `SUPPLIED_BY` (73) | seed script | **SYNTHETIC_DEMO — not a real relationship** | ACTUAL edge, but synthetic | supply-chain answer, disruption only; **the Supplier Risk tab ignores it** |
| Supplier → Dealer / Depot | — | none exists | — | **NOT_CONNECTED** | none | never claimed |
| Assembly / BOM | `ASM-…` | `Assembly` (1,206), `HAS_ASSEMBLY`, `CONTAINS_PART` | seed | SYNTHETIC_DEMO | ACTUAL edges, synthetic | impact, compliance inheritance |
| Compliance | Stage V | `ComplianceRequirement` (6), `REQUIRES_COMPLIANCE` (1,855), `HAS_CERTIFICATION` (76), `HAS_COMPLIANCE_REQUIREMENT` (7) | seed / SRC-039 | SYNTHETIC_DEMO (battery regulation real) | ACTUAL edges | compliance tab, verdicts |
| Stock | INV-DEMO-001 | `InventorySnapshot` (39), `HAS_SYNTHETIC_INVENTORY` | seed | SYNTHETIC_DEMO | ACTUAL, synthetic | supply chain, KPIs |
| Orders/Shipments/Service | order-demo-001 | `Order`, `FulfilmentRequest`, `Allocation`, `Shipment`, `ServiceJob` … | services/seeds | SYNTHETIC_DEMO / TEST_DATA | `HAS_ORDER`, `FOR_PART`, `HAS_SHIPMENT`, `SHIPPED_TO`, `HAS_SERVICE_JOB` | order answers, traceability |
| Question catalogue | P07 | `QuestionTemplate` (34), `Intent`, `RelationshipType` | `catalog_spec.py` | DERIVED | `ABOUT_*` to real nodes | sidebar catalogue |

---

## 5. KPI audit (what the UI can show)

> **Update:** the panel now shows three headline KPIs (order traceability, master-data consistency, supplier-to-part coverage) plus one DEMO-only KPI (stock-out). "Share of orders with a known status" (always 100 %) and "Customs flag detection" (1 of 1) were removed as uninformative; test-session orders are excluded from traceability; stock-out excludes product-line family records; supplier coverage shows the real 0 % and the demo link coverage on a separate line.

The KPI panel is the only place labelled "KPI". Frontend: `frontend/pages/PartsStore/PartsAnalysis.tsx` (`KpiPanel`) → `GET /api/v1/intelligence/kpis` →
`backend/app/modules/intelligence/kpis.py::all_kpis`. All are deterministic Cypher + Python counts; **no weights; no LLM**.

| KPI | What it represents | Source | API | Calculation | Formula / logic | Weight | Range | Data type |
|---|---|---|---|---|---|---|---|---|
| Order traceability rate | Share of non-cancelled orders with a full chain | `_CHAIN_Q` (Order, FulfilmentRequest, Allocation, Part, Shipment, DealerBranch, ServiceJob) | `/kpis` | `numerator / denominator` | full = all six links present; cancelled excluded | none | 0–100 % | SYNTHETIC_DEMO / TEST_DATA |
| Master-data consistency | Completeness of catalogue, dealer, supplier, machine links | `_MASTER_Q` | `/kpis` | `Σ passing / Σ total` over 7 checks | parts with name+category+source; parts with fitment; parts typed; dealers with coordinates; dealers linked to City/Country; SAP suppliers linked; machines typed | equal per record (so suppliers, 1,720 of 2,341, dominate) | 0–100 % | DERIVED |
| Supplier-to-part coverage | Parts with a real supplier link | `_SUPPLIER_COVERAGE_Q` | `/kpis` | `with_real / parts` | `SUPPLIED_BY` to a `HCME_SAP_SUPPLIER_MASTER` supplier | none | 0–100 % | REAL (0 %) |
| Stock-out exposure (DEMO) | Parts with no/zero stock | `_STOCK_Q` | `/kpis` | `no-stock / parts` | sum of snapshot quantities; parts with no snapshot count as no stock | none | 0–100 % | SYNTHETIC_DEMO |

Removed earlier and **not** computed: order-status resolution time, cross-catalog matching accuracy.

## 6. Score calculations — every score traced

### 6.1 Card match % (chat part cards) — `part_finder.find_parts`
Raw data: all 60 `Part` nodes + fitted model list (`_CATALOGUE_Q`, one Cypher round trip). Python:
- Exact part number / `PT-xxx` in query → **100**.
- Otherwise tokens (stop-words removed, typo-tolerant `_hit`) are matched per field with weights **part_name 3, part_subcategory 3, part_category 2, component_assembly 2, description 1**;
  `matched = terms hit`, `best = highest field weight per term`, `pct = round(100 × (0.7 × matched/terms + 0.3 × Σbest/(3 × terms)))`.
- If no term hits a field of weight ≥ 2 → `pct = min(pct, 45)`. If the query names only a machine (no part terms) → **90** for every part fitted to it.
- Results below **50** are dropped; ordering: pct, fits count, part id.
- `assessment()` text thresholds: ≥100 "Exact match.", ≥90 "Very strong match.", ≥75 "Strong match.", ≥60 "Good match with minor trade-offs.", else "Partial match".
Display: `PartCard.match_pct` in `PartsIntelligence.tsx`. Deterministic, HARDCODED weights, HEURISTIC; not a probability. Synthetic inputs: none.

### 6.2 Similarity % (Graph Insights › Mitigation; chat "alternatives") — `scoring.calculate_compatibility_score`
Fixed points: category equal **0.25**; sub-category equal **0.15**; assembly context exact **0.15** / shared word **0.10**; fitted-machine overlap **Jaccard × 0.35**; both genuine **0.10** (candidate only 0.05).
Candidates first pass `interchangeability.gate` (orderable part, same specific type, ≥ 1 shared machine) and must score ≥ 0.50. Example PT-007 vs PT-015: 0.25 + 0.15 + 0.15 + 0.0875 (1 shared of 4 machines, Jaccard 0.25) + 0.10 = **0.738 → 74 %**.
Deterministic, HARDCODED, HEURISTIC.

### 6.3 Mitigation score — `scoring.calculate_mitigation_score` (called from `graph_insights._mitigation`)
`score = 0.40 × compatibility + 0.30 × availability + 0.20 × compliance + 0.10 × source-risk/confidence`, with multipliers:
availability CONFIRMED/AVAILABLE 1.0, STALE/REGIONAL 0.60, UNKNOWN 0.30, otherwise 0.0; compliance COMPLIANT 1.0, UNKNOWN 0.50, else 0.0;
risk/confidence LOW risk **or HIGH confidence** 1.0, MEDIUM 0.70, HIGH risk/LOW confidence 0.20, else 0.50.
Inputs in `_mitigation`: availability from the **synthetic** depot snapshot sum (`>0` AVAILABLE, `0` OUT_OF_STOCK, none UNKNOWN); compliance `COMPLIANT` if the candidate has a certificate edge for every requirement (synthetic edges, expiry ignored) else `UNKNOWN`; supplier risk `LOW` (≥ 2 real suppliers) / `HIGH` / **`UNKNOWN` always today** (only non-synthetic suppliers are counted, none exist).
Live example, PT-007 → candidate PT-015: compatibility `0.738 × 0.40 = 0.295`; availability `OUT_OF_STOCK` (depot snapshot sum 0) → multiplier 0.0 → `0.000`; compliance `COMPLIANT` (no missing certificate edges) → `0.20`; source risk `UNKNOWN` but candidate confidence `HIGH` → multiplier 1.0 → `0.10`. Total `0.595` → **60** (matches the API value `mitigation_score: 60`).
Deterministic, HARDCODED weights (never validated by HCME), SYNTHETIC_DEMO inputs (stock, certificates).

### 6.4 Text similarity % (Similar Parts tab) — `similarity.similar_parts`
Raw data: `Part.name/category/sub-category/assembly/description` + `tech_voltage_v/current_a` where a real name states them. Embedding = 256-bucket hashed vector of word uni/bi-grams and character tri-grams with a small synonym list (`embeddings.py`), L2-normalised; `text similarity = cosine × 100`. Candidates come only from the gate (same type, shared fitment, not a family record); ordering: machine coverage, then similarity. Reported as **"supporting signal only"**. Example PT-007 → PT-015: cosine 0.95 → **95 %**; machine coverage 25 % (1 of PT-007's 4 machines). Deterministic, HEURISTIC, no LLM, no synthetic input.

### 6.5 Impact / compliance / supplier-risk figures (Graph Insights) — `graph_insights.get_part_graph_insights`
- **Affected machines** = distinct machines in `MATCH (p)<-[:CONTAINS_PART]-(a)<-[:HAS_ASSEMBLY]-(m)`; **Total BOM qty** = Σ `CONTAINS_PART.quantity`; **Critical paths** = assemblies with `criticality='high'`. Machines are real fitment; assembly link, quantity and criticality are SYNTHETIC_DEMO (rule: engine/hydraulic/drivetrain/fuel/cooling/control = high; undercarriage/electrical/etc. = medium; lights/attachments = low — `seed_phase10_demo_data.py`).
- **Compliance**: requirements inherited via `Assembly -REQUIRES_COMPLIANCE->`; a requirement is a **gap** if the part has no `HAS_CERTIFICATION|HAS_COMPLIANCE_REQUIREMENT` edge; status `GAPS_FOUND` / `COMPLIANT` / `NO_REQUIREMENTS_RECORDED`. Synthetic except the battery regulation.
- **Supplier risk**: state A (real links) never occurs; state B returns `NOT_CONNECTED` with supplier master count (1,720) and top-5 countries by supplier count.

### 6.6 Where an LLM is involved
- **Extraction** (`assistant._extract`, Gemini model chain `gemini-flash-lite-latest, gemini-3.1-flash-lite, gemini-3.8-flash`, temperature 0): only **fills gaps** in entities the deterministic parser (`_extract_deterministic`) already found. It does not compute any number.
- **Answer wording** (`assistant._answer`, `_ANSWER_SYSTEM`): rewrites the evidence JSON into prose. **Every score, percentage, count and card is computed in Python/Cypher before the LLM sees it**; the LLM never determines a score. With Gemini unavailable the deterministic `fallback` text is used (`pipeline.answer = deterministic`).
- **Risk:** the prose can restate a number loosely (observed: "the alternative candidate for PT-015 has a 74% similarity percentage to part PT-007"). The cards/data are authoritative; the label "answer by Gemini from graph evidence" marks this.

## 7. KPI-by-KPI trace (UI cards and numbers)

| Number | 1. Where from | 2. Records | 3. Fields | 4. Formula | 5. Deterministic | 6. LLM | 7. Synthetic | 8. Changes with graph? | 9. Up/down when | 10. Range |
|---|---|---|---|---|---|---|---|---|---|---|
| Match % | Python over one Cypher | all `Part` | name, sub-cat, category, assembly, description, number/id | §6.1 | Yes | No | No | Yes | catalogue text/number edits | 0–100 |
| Fits N | `len(models)` | `HAS_PART_FITMENT` | edges | count | Yes | No | No (but category-level) | Yes | fitment added/removed (Phase 10F added 455) | 0–77 |
| Similarity % (compat) | `scoring.py` | two `Part`, fitment sets | category, sub-cat, assembly, genuine flag, machine ids | §6.2 | Yes | No | No | Yes | shared machines, same assembly text | 0–100 |
| Text similarity % | `similarity.py` | all `Part` | text + `tech_*` | cosine | Yes | No | No | Yes | wording of part text | 0–100 |
| Mitigation score | `scoring.py` | candidate + snapshots + certs | stock qty, cert edges, confidence | §6.3 | Yes | No | **Yes** | Yes | stock added, certificates added | 0–100 |
| Affected machines / BOM qty / critical paths | `_IMPACT_Q` | `Assembly`, `CONTAINS_PART`, `HAS_ASSEMBLY` | quantity, criticality | §6.5 | Yes | No | **Yes** | Yes | reseeding BOM | ≥ 0 |
| Compliance gaps | `_COMPLIANCE_Q` | requirements + certificate edges | `held` | §6.5 | Yes | No | **Yes** | Yes | certificates added | count |
| Supplier master 1,720 / top countries | `_REAL_SUPPLIER_*` | `Supplier` with `HCME_SAP_SUPPLIER_MASTER` | country | count | Yes | No | No | Yes | new SAP import | ≥ 0 |
| KPI panel | `kpis.py` | see §5 | | | Yes | No | mostly | Yes | any test/browser order changes traceability | 0–100 % |
| Disruption counts | `disruption.py` | fitment, BOM, orders | | counts | Yes | No | assemblies/orders synthetic | Yes | | ≥ 0 |
| Timings | `perf_counter` | — | — | ms | No | No | No | — | load | ≥ 0 |

## 8. Real traced examples (deterministic provider, live graph, 2026-09-24)

| # | Input | Entities | Neo4j traversal | Raw result | Number | Final answer |
|---|---|---|---|---|---|---|
| 1 | "Find battery parts" | `part_category=Electrical` | `MATCH (p:Part)` + fitted models | 10 batteries match the token | cards PT-020 100 % (fits 11), PT-014 100 % (9), PT-011 100 % (7), PT-013 100 % (7), PT-012 100 % (5), PT-001 100 % (4) | "Found 10 matching part(s)… Best match: PT-020 … (100%)" — §6.1 |
| 2 | "What hydraulic parts fit ZX210LC-7?" | `machine_ref=ZX210LC-7`, `part_category=Hydraulics` | `Part` filtered by `(Machine {model})-[:HAS_PART_FITMENT]->` | 5 parts | PT-031 100 % (fits 67), PT-032 100 % (67), PT-045 100 % (7), PT-052 100 % (7), PT-044 90 % (7) | "Found 5 matching part(s)… Best match: PT-031" |
| 3 | "Which machines use PT-001?" | `part_ref=PT-001` | `(Machine)-[:HAS_PART_FITMENT]->(Part {PT-001})` | 4 machines | 4 | "PT-001 … fits 4 machine model(s) … ZX10U-6, ZX17U-6 / ZX19U-6, ZX19-6, ZX26U-6" |
| 4 | "Which suppliers are in Germany?" | `country=DE`, `requested_entity=supplier` | `(Supplier)-[:LOCATED_IN]->(City)-[:IN_COUNTRY]->(Country {DE})` | 117 suppliers (30 returned in the card list) | 117 | "The HCME supplier master lists 117 supplier(s) for DE." — SOURCE_DERIVED, geographic only |
| 5 | "Are there alternatives for PT-007?" | `part_ref=PT-007` | fitment sets + `gate` + `calculate_compatibility_score` | candidate PT-015 (fits 1 shared of 4) | compat 0.738 → **74 %**; Similar tab text similarity **95 %**, coverage **25 %**; mitigation score **60** (stock 0 → OUT_OF_STOCK, certificates present) | "Candidate for Engineering Review… (text similarity 74%, a supporting signal only)… not an approved replacement" |
| 6 | "Show me the supply chain for PT-001." | `part_ref=PT-001` | `Part -[:HAS_SYNTHETIC_INVENTORY]->InventorySnapshot`, `Part -[:SUPPLIED_BY]->Supplier` | demo stock 17 at Oosterhout; supplier link "Demo Battery Supplier" | 17 | answer states "synthetic demo data — no live HCME stock feed is connected" |
| 7 | "What happens if PT-007 becomes unavailable?" | `part_ref=PT-007`, intent `disruption` | fitment → BOM → orders; `similar_parts` → compliance verdict | 4 machine models, 1 assembly (demo), 0 open orders; PT-015 **Not Suitable** (EU Battery Regulation certificate expired 2026-03-01 — synthetic evidence) | counts 4 / 1 / 0 | "PT-007 unavailable affects 4 machine models (source-derived fitment), 1 assemblies (demo BOM), 0 open orders. No suitable candidate…" |

## 9. Misleading-KPI flags

| Item | Looks like | Actually | Flag |
|---|---|---|---|
| Card match % | probability/quality of match | term-coverage heuristic; 10 batteries all "100 %" | HEURISTIC |
| Similarity % (Mitigation) vs Text similarity % (Similar tab) | one "similarity" | two formulas: 74 % vs 95 % for the same pair | HEURISTIC / inconsistent naming |
| Mitigation score 60 | a business ranking | fixed weights invented by the project; synthetic stock/cert inputs | HARDCODED + SYNTHETIC_DEMO |
| Mitigation compliance input | "COMPLIANT" | true when certificate *edges* exist (synthetic), expiry ignored — the Disruption tab says Not Suitable for the same part | SYNTHETIC_DEMO / inconsistent |
| Mitigation supplier risk | risk level | always UNKNOWN today (no real links) so it contributes the same 0.10 to every candidate | NOT_CONNECTED input |
| Total BOM qty, Critical paths | engineering BOM / criticality | invented quantities and rule-based criticality | SYNTHETIC_DEMO |
| Compliance "GAPS_FOUND / COMPLIANT" | audit result | derived from synthetic assignments/certificates | SYNTHETIC_DEMO |
| Fits N machines (fluids, families) | verified per-model fit | category-level: applies to every machine of a category | DERIVED (weak evidence) |
| KPI order traceability 2/5 | operational KPI | counts demo + browser-test orders | SYNTHETIC_DEMO / TEST_DATA |
| KPI master-data consistency 98.8 % | data quality | unweighted sum, dominated by supplier rows | DERIVED |
| KPI stock-out 48.3 % | stock risk | which parts got a demo snapshot | SYNTHETIC_DEMO (labelled DEMO) |
| Answer text "by Gemini" | authoritative wording | LLM rewrite of evidence; may paraphrase numbers loosely | LLM_GENERATED (text only) |

## 10. Findings / Limitations / Follow-up (nothing was changed)

- **F-1 Two "similarity" figures.** Chat answer and Graph Insights › Mitigation use `scoring.py` (74 %); the Similar Parts tab uses cosine (95 %). Follow-up: use distinct names or one basis.
- **F-2 Mitigation vs Disruption disagree** for the same candidate (score 60 with "compliance OK" vs Not Suitable). Cause: `graph_insights._mitigation` predates `disruption.compliance_verdict` and ignores certificate expiry and evidence basis. Follow-up: align or hide the older score.
- **F-3 Supplier Risk tab vs Disruption supplier dependency.** The tab counts only real SAP links (none) → NOT_CONNECTED; Disruption/supply-chain answers use the 73 demo links (labelled). Both are correct to their rules but look contradictory.
- **F-4 Fitment evidence is thin.** 1,331 of 1,496 fitments are category-level and 70 are internally generated; only 37 name an exact model. "Fits N machines" for fluids/families means "machine category", not a per-model verified fit. Phase 10F added 455 category-level edges tagged with the part's own source id.
- **F-5 17 of 60 parts have unverified numbers.** They are usable only through the demo order path, but they appear in Parts Intelligence like any other part.
- **F-6 Store catalogue header stale** ("45 products"; file has 57), and 12 store images are explicitly not official photography.
- **F-7 Account managers counted as dealers** (e.g. 7 of 19 Netherlands entries); no type field in SRC-049.
- **F-8 Traceability KPI moves with testing.** Every browser test order lowers it (now 2 of 5).
- **F-9 Master-data consistency** weights records, not checks; a supplier defect would move it far more than a part defect.
- **F-10 Country count** is 53 in the graph (earlier reports said 56).
- **F-11 Hard-coded values** worth knowing: match-score weights (§6.1), compatibility and mitigation weights (§6.2–6.3), criticality rules, transport rate card, EU27 list in `kpis.py`, `MIN_RELEVANCE 0.30` / `RELATIVE_FLOOR 0.70` in `similarity.py`, expiry warning window 90 days in `disruption.py`.

## Answers to the two questions

- **"Where did this number come from?"** Every number above is computed by deterministic Python/Cypher from Neo4j (no LLM), with the formulas and weights in §6. The LLM only words the answer.
- **"Is it actual/source-derived HCME data or synthetic demo data?"** Machines, catalogue parts (except 17 unverified), dealers, dealer GPS, the depot facts and the 1,720 supplier records are source-derived/real. Assemblies, BOM quantities, criticality, supplier→part links, compliance assignment/certificates, stock, orders, shipments, transport costs/ETAs and service events are SYNTHETIC_DEMO; prices, live stock, carrier, ERP, dealer DMS, supplier→part (real) and customers are NOT_CONNECTED.
