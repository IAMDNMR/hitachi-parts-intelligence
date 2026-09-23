# Phase 10 — Task List

Executed one at a time, in order. Each task is closed only after its check has actually run.

Target UI (from the uploaded screenshots, adapted to HCME Europe: vehicle → machine, connector → part):
Question box → Workflow Execution → match-result cards (ID, description, match %, 4 attribute tiles,
type tag, assessment, "View Full Details") → Graph Insights modal with exactly 4 tabs:
Impact · Compliance · Supplier Risk · Mitigation, plus "Analyze Disruption" and "Close".

| # | Task | Check | Status |
|---|------|-------|--------|
| 1 | Business entity model (Part, BOM, Customer, Supplier, Sales Order, Purchase Order) mapped to live graph | Doc written, counts from live Neo4j | DONE |
| 2 | Live data audit script: classification, provenance, orphans, duplicates, test leakage, currency | Produces DATA_QUALITY_ISSUES.json with real counts/IDs | DONE |
| 3 | Screen field inventory: every field on the 5 target screens → source → status → action | Table in audit doc | DONE |
| 4 | Transport/fulfilment truth: trace Normal/Express price + transit, fix or relabel, no USD | Audit re-run shows 0 unsupported | DONE |
| 4b | Inventory truth: replace hardcoded mock stock (fake 'HCME_ERP_SAP', invented Amsterdam/Japan depots) with SYNTHETIC_DEMO stock seeded in Neo4j at the real Oosterhout depot | Audit DQ-11 = 0; 43 backend tests pass | DONE |
| 5 | Remove / classify test-data leakage (orphan Orders, FulfilmentRequests, QA Customer) | Audit re-run shows 0 leaked | DONE |
| 6 | Seed BOM (Machine → Assembly → Part, quantity) as labelled SYNTHETIC_DEMO | Integrity check | DONE |
| 7 | Seed Part → Supplier (share, tier, region, dual-source) as SYNTHETIC_DEMO | Integrity check | DONE |
| 8 | Compliance: assembly-level requirements, part certifications, gap derivation | Integrity check | DONE |
| 9 | Customer / Sales Order / Purchase Order minimal seed and links | Integrity check | DEFERRED (user re-prioritised Parts Intelligence) |
| 10 | Backend: Graph Insights endpoints reshaped to the 4 target tabs | pytest | DONE |
| 11 | Backend: match results in card shape (match %, 4 attributes, assessment, specs) | pytest | DONE |
| 12 | Backend: NL assistant: dealers (country/city/nearest + ask for location), order, shipment, service, multi-hop, provenance line | pytest | DONE |
| 13 | Frontend: Parts Intelligence screen = question box + workflow + result cards only | typecheck + browser | DONE |
| 14 | Frontend: Graph Insights modal = 4 tabs + Analyze Disruption + Close | typecheck + browser | DONE |
| 15 | Frontend: natural-language answer panel (dealer/order answers, provenance) | browser | DONE |
| 16 | Waterfall: Part → … → Close, selected fulfilment option carried through | API + browser test | PARTIAL — backend suite only |
| 17 | NL test matrix: 30+ questions executed live | Results doc | DONE |
| 18 | Full validation: pytest, npm test, typecheck, build, integrity, concurrency ×3, console sweep | All executed | DONE (except concurrency ×3) |
| 19 | PHASE_10_FINAL_CLOSURE_REPORT.md with real counts | Written | DONE |
