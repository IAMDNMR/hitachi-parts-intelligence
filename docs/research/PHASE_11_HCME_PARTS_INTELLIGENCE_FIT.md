# Phase 11 — Pavan's concept, mapped to HCME Parts Intelligence

Pavan's demo is an automotive-connector concept on fabricated data. It is used here only as a reference for the
*approach* (similarity + knowledge graph + impact + compliance + supplier risk + explained mitigation). Every capability
was mapped to an HCME requirement, kept only if HCME has the data, and otherwise recorded as a future gap.

Method per capability: **Pavan → HCME equivalent → relevant? → data? → decision.**

## Implemented

| Pavan capability | HCME equivalent | Why HCME needs it | HCME data behind it | Question it answers |
|---|---|---|---|---|
| Vector search over specs | **Local semantic + hybrid search** over catalogue text (`embeddings.py`, `similarity.py`, `/search/semantic`, `/search/hybrid`) | Dealers describe parts loosely ("accumulator", typos); exact-only search misses them | 60 real parts: name, number, category, sub-category, assembly, description, fitment. Electrical values (24V, 100A) only where the real name states them (PT-054/055/056) | "24V alternator with 100A", "hydralic pmp", "4658321" |
| Ranked similar parts + score | **Similar parts** (`/parts/{id}/similar`, Graph Insights › Similar Parts) | Substitute parts when one is unavailable | Hard filters (orderable part, same specific type, shared fitment); text similarity only orders | "Are there alternatives for PT-007?" (PT-015 as a candidate for engineering review; PT-045 has none) |
| Reason for recommend / reject | Match factors and rejection reasons on every result | A parts decision must be explainable | Same as above | "Why is PT-044 not a candidate for PT-045?" (different part type) |
| RFQ input | **RFQ search** (`/rfq`, natural-language routing) | Dealer enquiries arrive as sentences with quantity, spec and machine | Catalogue, fitment, demo stock. Lead time and price do **not** exist and are reported as such | "Need 20 units of a 24V starter motor for ZX210LC-7" |
| Impact analysis | Existing Graph Insights impact + BOM traversal, reused by scenarios | Which machine models stop | `Machine → Assembly → Part` (BOM is SYNTHETIC_DEMO quantities on real fitment) | "Which machines use PT-031?" |
| Compliance inheritance + check | **PASS / UNVERIFIED / WARNING / FAIL verdict** (PASS only on real evidence) (`/compliance-check`) | A substitute must meet the requirements the assembly imposes (Stage V, REACH, CLP…) | `Assembly –REQUIRES_COMPLIANCE→ Requirement`, `Part –HAS_CERTIFICATION→` with `valid_until` (SYNTHETIC_DEMO; regulation names are real EU instruments) | "Does PT-032 satisfy what PT-031's assemblies need?" |
| Supplier risk / sole source | Supplier concentration inside scenarios | Single-source parts are a real parts risk | `Part –SUPPLIED_BY→ Supplier` (77 links, all SYNTHETIC_DEMO, labelled) | "Which parts are sole-sourced?" |
| Disruption + mitigation ranking | **Scenarios** `part_unavailable`, `supplier_unavailable`, `compliance_failure`, `stock_shortage` (`/disruption`, Graph Insights › Disruption, chat) | The core "what if" for parts continuity | Above + open orders + demo stock | "What happens if Demo Hydraulics Supplier A becomes unavailable?" |
| Graph disqualifies a candidate | A candidate with compliance FAIL or whose only supplier is the disrupted one is marked **Not Suitable** and listed last | Similarity alone is unsafe | Same | PT-015 as a candidate for PT-007 is Not Suitable (demo certificate expired) |
| KPIs | **`/kpis` + KPI panel**: order traceability, master-data consistency, supplier-to-part coverage, share of orders with a known status (stock-out = DEMO; customs = rule check) | Measure the platform honestly | Live graph; each KPI shows numerator/denominator, method, real vs synthetic source | see panel |
| Web application | Existing Parts Intelligence UI extended (no redesign) | — | — | — |

> Where this table and the "Phase 11b corrections" section at the bottom differ, **11b is current**: the first-pass weighted score,
> severity levels and "recommended replacement" wording were removed after the validation pass.

## Intentionally NOT implemented

| Pavan item | Reason |
|---|---|
| Automotive connector attributes (pin count, IP rating, temperature range, connector type) and demo connector parts | HCME parts are machine parts (pumps, valves, oils, batteries). The catalogue has no such attributes; the first pass invented four connector parts and has been **removed** (`phase11_seed_pavan_gaps.py --step cleanup`). Only voltage/current already in real part names are used |
| Neural embeddings | No text/spec data richer than the catalogue exists; a local hashed-text embedding is enough and needs no external API. A neural model can be plugged in through the same `EmbeddingProvider` interface later |
| Vehicle / model-year concepts | HCME uses Machine → Machine Model → Assembly → Part |
| Customer-installed-base impact | No customer→machine data exists. The scenario output has a `customers` field that returns `[]` with an explicit note instead of inventing customers. **Future:** dealer/ERP installed-base data |
| Country / region supplier disruption | The 1,720 real SAP suppliers have no part links, so it could only be answered from 10 demo suppliers. **Future:** SAP purchasing/source-list data |
| Cross-catalog matching accuracy KPI | One catalogue, no ground-truth mapping; a number would come from a test fixture. **Future:** second catalogue + labelled mapping |
| Warranty, Affiliate/Partner entities | No source data; "Affiliate" is not yet defined for this project |
| MCP server / host | Excluded by instruction |
| Real-time SAP / supplier / stock / customs feeds | Excluded by instruction; all such data is labelled SYNTHETIC_DEMO |

## Data added (all labelled)

- `tech_voltage_v`, `tech_current_a` on PT-054/055/056 — **SOURCE_DERIVED** (stated in the real names).
- `valid_until` on 76 `HAS_CERTIFICATION` edges — **SYNTHETIC_DEMO** (10 expired, 14 expiring soon) so expiry logic is testable.
- `embedding` (256-d) on every catalogue part + vector index `part_spec_embedding_index`.
- Nothing else. No new parts, customers or suppliers remain.


## Phase 11b corrections (after the validation pass)

| Area | Change |
|---|---|
| Interchangeability | One gate (`interchangeability.py`) decides who may be shown as a candidate: orderable part only (`PRODUCT_LINE_PART_FAMILY` records excluded), same *specific* part type (oil filter != fuel filter, starter battery != traction battery), and at least one shared machine fitment. Applied to similar parts, Graph Insights mitigation, `/mitigation` and `alternatives.py`. Similarity only orders candidates that passed. Wording everywhere: **Candidate for Engineering Review** / **Not Suitable** / **Insufficient Data**. Hooks for authoritative `SUPERSEDES` / `COMPATIBLE_WITH` / `NOT_COMPATIBLE_WITH` relationships exist (none loaded) |
| Search | HCME's standard search stays primary. The hybrid/semantic search is a supporting path (typos, electrical specs, RFQ) with a relevance floor (30%, and 70% of the best match) so weak matches are not shown |
| RFQ | Parser kept. Stock, price and lead time are `NOT_CONNECTED`; the requested quantity is recorded but never compared with demo stock. `commercial_status()` is the single integration point for real feeds |
| Impact | Real fitment kept; every block carries provenance (machines real, BOM/criticality demo) |
| Compliance | `PASS` requires REAL evidence. Demo certificates give `UNVERIFIED`; missing/expired give `FAIL`; expiring soon `WARNING`; nothing recorded `NO_REQUIREMENT_RECORDED` |
| Supplier risk | Unchanged (`NOT_CONNECTED`). No new demo supplier links. Target model for real SAP data: `PHASE_11_SUPPLIER_DATA_MODEL.md` |
| Disruption | Severity and weighted scores removed. Shows affected parts, assemblies (demo), machine models, open orders, supplier dependency, candidates, compliance and stock, each with provenance. Parts with no candidate say so |
| KPIs | Kept: order traceability, master-data consistency, supplier-to-part coverage. Changed: order-status resolution time -> share of orders with a known status. Stock-out exposure marked DEMO. Customs demoted to a rule check. Cross-catalog matching removed |
