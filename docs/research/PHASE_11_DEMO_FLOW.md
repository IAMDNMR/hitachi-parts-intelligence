# Phase 11 — Stakeholder demo flow (HCME-supported data only)

Open **Parts Intelligence**. The header legend explains the three data states used everywhere:
**REAL** (HCME/source), **SYNTHETIC_DEMO** (illustration), **NOT_CONNECTED** (no data). Use the catalogue questions on the left
(each was run and verified) or type them. Answer wording may vary when Gemini is on; the cards and data are authoritative.

| # | Step | Ask / click | What to point out | Data state |
|---|---|---|---|---|
| 1 | Find parts for a machine | "What hydraulic parts fit ZX210LC-7?" | Ranked parts from real fitment | REAL |
| 2 | Find machines using a part | "Which machines use PT-045?" | 7 machine models, graph view | REAL |
| 3 | Candidate parts | "Are there alternatives for PT-007?" then "…for PT-045?" | PT-015 is a *Candidate for Engineering Review* (same type + shared machines); PT-045 has none, and the answer says so. Oil filter is never offered for a fuel filter | REAL inputs; no HCME interchangeability data (NOT_CONNECTED) |
| 4 | Impact | Graph Insights on PT-007 › **Impact** | Machines (real) vs assemblies/BOM/criticality (demo chips) | REAL + SYNTHETIC_DEMO |
| 5 | Compliance | Graph Insights › **Compliance** | Real EU regulation names; assignment and certificates are demo, so the result is never "PASS" | SYNTHETIC_DEMO |
| 6 | Supplier risk | Graph Insights › **Supplier Risk** | "SUPPLIER RISK DATA NOT CONNECTED": 1,720 real suppliers, no supplier→part link | NOT_CONNECTED |
| 7 | Disruption | Graph Insights › **Disruption**, or ask "What happens if PT-007 becomes unavailable?" | Affected machines/assemblies/orders, candidate marked *Not Suitable* with the reason; provenance chips; no severity score | REAL + SYNTHETIC_DEMO |
| 8 | RFQ | "Need 20 units of a 24V starter motor for ZX210LC-7" | Parsed quantity/spec/machine; stock, price, lead time show *not connected* | REAL + NOT_CONNECTED |
| 9 | KPIs | KPI button in the sidebar | Master-data consistency, supplier coverage (0%), order traceability; stock-out marked DEMO; customs under "rule checks" | mixed, labelled |
| 10 | Lifecycle | Parts Store › cart › Check stock & fulfil › Stage 7 | Every event is marked DEMO/SIMULATED; nothing implies a real order, shipment or service | SYNTHETIC_DEMO |

Close with `PHASE_11_HCME_DATA_GAP_AND_PILOT_REQUIREMENTS.md`: the real data needed to turn each demo step into a production capability.

Before a demo: clear test sessions from the graph (3 abandoned requests and their mock fulfilment options from manual testing show up in the data audit).
