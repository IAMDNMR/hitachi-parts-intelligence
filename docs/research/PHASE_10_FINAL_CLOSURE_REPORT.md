# Phase 10 — Final Closure Report (Parts Intelligence priority)

Date: 2026-09-23 · Live Neo4j AuraDB · all counts are from executed runs.
Task tracker: `PHASE_10_TASKS.md` · Audit: `PHASE_10_DATA_QUALITY_AUDIT.md` + `data-quality/DATA_QUALITY_ISSUES.json` ·
Business model: `PHASE_10_BUSINESS_ENTITY_MODEL.md` · NL results: `PHASE_10_NL_TEST_MATRIX.md`

## 1. Data audit and fixes

| | Before | After |
|---|---|---|
| Failing quality checks | 19 / 29 | **2 / 31** |
| Offending records | 1,826 | 12 |

Remaining: DQ-06 dealer coordinates (DLR-043 "Hitachi CM Nederland — Regio Utrecht" has no latitude in the
source, so it is excluded from distance ranking and nothing is invented; DLR-116 French Guiana and DLR-130
Réunion are French overseas territories listed by HCME) and DQ-25 (8 generic fluids/paint with no fitment,
which is acceptable).

## 2. Records removed / converted / labelled

| Action | Count |
|---|---|
| Test orders deleted (`INTERNAL_TEST_WORKFLOW`, test part numbers / invented destinations) | 184 |
| Test shipments + events, allocations, fulfilment options/requests, ledger rows | 15, 79, 77 + 72 EXPRESS, 148, 75 |
| Test inquiries/requested parts, orphan requested parts, test customer, test audit records | 28, 56, 1, 21 |
| Mock inventory snapshots with invented depots (`REGIONAL-DEPOT-AMS/-DEFAULT`, fake `HCME_ERP_SAP`) | 148 |
| Fulfilment options set to transport **NOT_CONNECTED** (price/carrier/transit/ETA nulled) | 77 |
| Broken ID fixed (`SJ-DEMO-00x.order_id`) | 2 |
| **Retained**: SOURCE_DERIVED Parts 60, Machines 77, fitments 1,041, DealerBranch 182, Depot 1; SYNTHETIC_DEMO order-demo chain; 1 real quote customer | |

## 3. SYNTHETIC_DEMO data added (seed script `seed_phase10_demo_data.py`, all `synthetic=true`)

| Step | Records |
|---|---|
| inventory — demo stock at the real Oosterhout depot | 36 |
| bom — Assembly + CONTAINS_PART{quantity} built 1:1 on the real fitments | 833 assemblies, 1,041 lines |
| suppliers — 8 fictional European demo suppliers + SUPPLIED_BY{share} | 73 links |
| compliance — real EU regulations, synthetic assignment/certificates | 1,692 requirements, 77 certificates, 2 dependencies |

## 4. Transportation correction

The €35 / €65 / 1-day values were hardcoded in `integrations/mocks/shipping_rate_mock.py` and
`routing_mock.py`, and stored as `CONFIRMED`. The fulfilment service now honours the providers'
`is_confirmed` flag, so unconfirmed transport is stored as null / NOT_CONNECTED and the UI shows
"Not connected". No USD value appears anywhere: DQ-08 non-EUR currency = 0.

## 5. Parts Intelligence (priority)

**UI** (`frontend/pages/PartsStore/PartsIntelligence.tsx`, `GraphInsights.tsx`, `PartsIntelligence.css`):
the screen now has only the question box, Workflow Execution (real timings and the graph path), an
answer panel, dealer cards and part result cards. Each result card shows ID, match %, 4 tiles (part
number, category, assembly, fits), a type tag, an assessment and View Full Details (specs + description).
The Graph Insights modal has exactly 4 tabs (Impact, Compliance, Supplier Risk, Mitigation) plus Analyse
Disruption and Close, all from one API call. Removed: the 6 extra tabs, the stats bar, the hero pills,
the example chips and 110 orphaned CSS rules.

**API**:
- `GET /api/v1/intelligence/parts/{id}/graph-insights` returns the 4 tabs in one response (~0.6–0.9s warm).
- `POST /api/v1/intelligence/query` pipeline: question → understanding → Neo4j resolution → per-intent
  multi-hop traversal → evidence + provenance → answer.
  - Understanding: deterministic parsing with typo correction for clear questions; Gemini for fuzzy phrasing.
  - Answer: Gemini, which writes only from the evidence.
- 18 intents cover parts, machines, impact, compliance, supplier risk, mitigation, alternatives, supply
  chain, fulfilment, part→dealer (derived), dealer lists, nearest dealer, dealer contact, order,
  shipment, service and unsupported questions.
- Nearest dealer: the place or postcode is geocoded with OpenStreetMap Nominatim, then dealers are ranked
  by great-circle distance in Neo4j. If no location is given, the assistant asks for a city or postcode.
- New `GET /api/v1/dealers?country=&city=` serves the 182 real dealers. It also replaces the invented
  "Amsterdam Main Hub BR-101" destinations in the Parts Store.

**Understanding any question**: typo-tolerant parsing ("dearler", "netehrlands", "hydralics"); a
`general_question` intent that answers general machinery questions, labelled "General information (not
HCME data)", when Gemini is available; the related part cards are always shown.

**Gemini** (free tier, 15 requests/minute): minimal thinking; an automatic free-model chain
(`gemini-flash-lite-latest` → `gemini-3.1-flash-lite` → `gemini-3.8-flash`), each with its own request
budget and a cooldown on 429/503; hard timeouts (3s understanding, 4.5s answer); and a deterministic
fallback, so every question still gets a graph-grounded answer.

## 6. Validation executed

| Check | Result |
|---|---|
| Backend `python -m pytest` (full suite) | **111 passed, 0 failed** |
| Phase 10 PI tests after the final edits (graph insights, assistant, phase 7 router) | **18 passed** |
| Frontend `npm test` | **82 / 82 pass** |
| `npm run typecheck` | pass |
| `npm run build` | pass |
| Data-quality audit | 2 / 31 failing (both explained above) |
| NL test matrix, 35 live questions | run 1 **31 / 35**, run 2 **32 / 35**. The 3 run-2 failures (typo corrector turned "supplies" into "supplier"; a failed geocode was cached) were fixed and verified individually; not re-run as a full matrix |
| Browser | PI screen, result cards, 4-tab modal and dealer answer verified in the running app |

## 7. Not done / remaining limitations

- **Task 9** (Customer / Sales Order / Purchase Order seed) was deferred when the user re-prioritised Parts Intelligence.
- **Task 16 (done after user feedback)**: the stock → fulfilment → allocation → order → shipment → service
  → close flow now starts from the **quote cart** ("Check stock & fulfil" on each cart line), not from
  the part details page. Verified end to end in the browser for 4663907 → DLR-122 Pellen Machines, all
  10 steps through CLOSE. Fixed along the way: the service job showed "Hitachi Authorised Dealer" (it read
  `d.name`, but the field is `dealer_name`); the delivery event said "Destination Dealer Branch" (it now
  records the real receiving dealer); a delivered shipment still showed a future ETA (it now shows the
  delivery date); and the developer "Phase 4/5/7/8" labels were replaced with user-facing ones.
- The order status stays `CREATED` for the whole journey (the backend never advances it). This remains open.
- Concurrency ×3 was not run separately.
- API-level tests still create Orders without `testRunId`, so they leak into the live DB on each run
  (root cause found; cleanup is `phase10_fix_data.py --step testdata`).
- Gemini free-tier latency and rate limits vary (1.5s to over 10s). While rate-limited, answers use the
  deterministic phrasing.
- No live HCME ERP, stock, pricing or carrier data is connected. All such data is labelled SYNTHETIC_DEMO or
  NOT_CONNECTED.

## 8. HCME supplier master (client data, added 2026-09-23)

Source: `20260609_Source data for Supplier.xlsx`, SAP S/4HANA migration template, sheet *General Data*.
Only LIFNR (supplier number), NAME_FIRST/NAME_LAST (name), CITY1 (city) and COUNTRY were used.
Script: `docs/data/neo4j/scripts/import_sap_suppliers.py` (dry run by default).

| Item | Count |
|---|---|
| Suppliers loaded (`data_source='HCME_SAP_SUPPLIER_MASTER'`, classified REAL) | 1,720 |
| Countries / cleaned cities | 53 / 824 |
| City spellings corrected (ALL-CAPS, Dutch variants such as 's-Hertogenbosch and Den Haag; raw value kept in `city_raw`) | 359 |
| Names truncated at SAP's 40-character field, joined with Name 2 (raw kept) | 20 |
| Same name under different supplier numbers (kept, flagged `possible_duplicate_of`) | 22 |
| Suppliers outside Europe (kept, `region='Rest of world'`) | 67 |

Graph: `(:Supplier)-[:LOCATED_IN]->(:City)-[:IN_COUNTRY]->(:Country)`. The 182 dealers and the Oosterhout depot
are linked to the same City/Country nodes. 36 cities hold both a dealer and suppliers (38 dealers, 223
suppliers), and 34 suppliers are in Oosterhout, the depot's city. Parts Intelligence answers supplier-by-number,
name, city or country, and "suppliers in the same city as dealer X / the depot". Audit after the import:
2 / 31 failing (unchanged).

**Not in the file: which parts each supplier supplies.** No `Part-[:SUPPLIED_BY]->Supplier` link was created
from it. The Supplier Risk tab still uses the labelled demo suppliers until a part-to-supplier source is
provided (for example SAP purchasing info records or a source list).
