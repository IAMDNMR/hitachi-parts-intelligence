# Phase 11 — HCME Parts Intelligence: data gaps and pilot requirements

Status: **Phase 11 baseline, frozen for stakeholder review** (2026-09-23). No feature was added for this document.
Purpose: show what works today on HCME data, what is still demonstration only, and exactly which real HCME data moves each
capability from demo to business use.

Data legend used in the UI and here:
**REAL** = HCME / source data · **SYNTHETIC_DEMO** = illustration, not HCME data · **NOT_CONNECTED** = the data does not exist in our system.

---

## A. What works today (on real HCME data)

| Capability | What it does | Real data behind it |
|---|---|---|
| Part search | Finds parts by description, part number, typo, machine model, electrical spec (24V/100A); shows relevance and hides weak matches | 60 catalogue parts (name, number, category, description) |
| Find parts for a machine / machines for a part | Fitment lookup both ways | 77 machine models, 1,496 part-to-machine fitment links (source-derived) |
| Dealer and supplier-master lookup | Dealers by country/city/name/nearest; suppliers by number, name, city, country; dealer + supplier co-location | 182 European dealers, 1,720 SAP-master suppliers (number, name, city, country) |
| Candidate parts | Candidates for engineering review, shown only if same specific part type **and** shared machine fitment; oil filter is never offered for a fuel filter; product-line family records excluded | Catalogue + fitment |
| Impact analysis | Which machine models use a part | Fitment (real) |
| Question catalogue | 34 questions whose answers were run and checked, stored in the graph and wired to the real nodes | — |
| Fallback | Every answer still works when Gemini is unavailable | — |
| KPIs (real basis) | Master-data consistency 98.8% (2,313 of 2,341 checks); supplier-to-part coverage 0% (0 of 60); order traceability on the seeded demo orders | Catalogue, dealers, supplier master |
| Honest gaps | Supplier risk says NOT_CONNECTED; RFQ says stock, price and lead time NOT_CONNECTED; compliance never says PASS on demo evidence; no invented customers | — |

## B. What is still demo-only (SYNTHETIC_DEMO)

| Item | Where it shows up | Why it is demo |
|---|---|---|
| Assemblies, BOM quantities, assembly criticality (1,206 assemblies) | Impact › critical paths, disruption | Built from real fitment with invented quantities and criticality rules |
| Supplier → part links (73 links, 10 demo suppliers, all 60 parts) | Supplier dependency, supplier-unavailable scenario | No SAP purchasing data; all flagged `synthetic=true` |
| Compliance assignment and certificates (which assembly needs which regulation, which part holds which certificate, expiry dates) | Compliance tab, candidate compliance status | Regulation names are real EU instruments; the assignment and certificates are invented. Result is `UNVERIFIED`, never `PASS` |
| Stock snapshots (39, for 37 of 60 parts) | Stock-out exposure (marked DEMO), candidate stock | No stock feed |
| Orders, shipments, customs context | Order traceability | Demo orders plus orders created while testing the Parts Store (5 orders, 4 shipments today) |
| Transport options (Road/Rail/Air) | Fulfilment options | Deterministic synthetic European transport data |
| Demo part references (`DEMO-...`) for store items without a verified HCME part number (12 with unverified numbers, product families, attachments, unidentified items) | Cart → Continue to demo order → Stage 1–7 lifecycle | Not official part numbers; labelled "DEMO PART REFERENCE — NOT AN OFFICIAL HCME PART NUMBER", never shown as verified. Real numbers (C1–C2 below) replace them |

Nothing demo-only is shown without a label: the Parts Intelligence header carries the legend, each Graph Insights tab carries
REAL / SYNTHETIC_DEMO / NOT_CONNECTED chips, and disruption results list the provenance of every block.

## C. Real HCME data required for production use

### C1. Supplier → Part links (SAP purchasing / source list / info records)
- **Fields:** supplier number, material (part) number, source-list validity, quota % or fixed source, purchasing info record (lead time, minimum order quantity), plant.
- **Load into:** `(Part)-[:SUPPLIED_BY {share_pct, role, valid_from, valid_to, lead_time_days, synthetic:false}]->(Supplier)`; optionally supplier → assembly. Target model: `PHASE_11_SUPPLIER_DATA_MODEL.md`.
- **Unlocks:** supplier risk (today NOT_CONNECTED), sole-source and dual-source detection, supplier dependency, the supplier-unavailable scenario on real suppliers, the KPI "supplier-to-part coverage" (0% → real), supplier lead time for RFQ.

### C2. Supersession / interchangeability (HCME parts engineering)
- **Fields:** Part A supersedes Part B · Part A is compatible with Part B · Part A is **not** compatible with Part B; with validity/effectivity and the source document.
- **Load into:** `SUPERSEDES`, `COMPATIBLE_WITH`, `NOT_COMPATIBLE_WITH` between Part nodes (the code already reads these; none are loaded).
- **Unlocks:** candidate parts become **approved** replacements (with the authoritative reason) instead of "Candidate for Engineering Review"; a not-compatible flag can hard-exclude a part; alternatives for parts that currently have none.

### C3. Real stock (depot and dealer)
- **Fields:** part number, location (Oosterhout depot, dealer), quantity on hand / available / reserved, as-of timestamp.
- **Unlocks:** RFQ availability (today NOT_CONNECTED), stock-out exposure as a real KPI, candidate stock in disruption and the stock-shortage scenario, fulfilment/allocation on real quantities.

### C4. Lead time
- **Fields:** part number (or supplier + part), replenishment lead time, transport lead time by lane.
- **Unlocks:** RFQ deadline check ("required within 4 weeks"), delivery promise in fulfilment options, supplier lead-time risk.

### C5. Real compliance evidence
- **Fields:** requirement (e.g. Stage V, REACH, CE/EMC, Battery Regulation) per part or assembly, certificate/declaration reference, issuing body, valid-from/valid-until, document link.
- **Load into:** `HAS_CERTIFICATION` edges with `synthetic:false` and `valid_until`; assembly requirements from engineering.
- **Unlocks:** compliance `PASS` (today capped at `UNVERIFIED`), real expiry warnings, compliance-failure scenario on real evidence, the compliance gate on candidate parts.

### C6. Real dealer / parts questions and expected answers
- **Fields:** 100+ real questions from dealers, parts desk and service (as asked, typos included), with the expected part / dealer / answer and who confirmed it.
- **Unlocks:** measured search accuracy (top-1 / top-5), a regression set, tuning of the relevance threshold, evidence for whether a neural model is needed at all.

### C7. Real orders and shipments (where required)
- **Fields:** order number, part, quantity, status history, dealer, shipment/carrier/dates, delivery confirmation, service completion.
- **Unlocks:** order traceability KPI on real volume (today 2 of 2 seeded demo orders), open-order impact in disruption, a customs flag on real cross-border shipments (needs origin, destination, HS code).

### C8. Also needed for specific features
| Data | Unlocks |
|---|---|
| Customer / installed base (customer → machine serials, dealer) | "Which customers are affected" (field exists, returns empty) |
| Real BOM / assemblies from engineering | Replaces demo assemblies and criticality in impact and disruption |
| Part technical attributes (only those HCME actually specifies per part type) | Specification matching beyond the 24V / 100A values in part names |

## D. Data item → feature it unlocks

| Data item | Feature unlocked | Feature today |
|---|---|---|
| Supplier → part | Supplier risk, sole source, supplier-unavailable, supplier coverage KPI | NOT_CONNECTED / demo |
| Supersession / interchangeability | Approved replacements, hard exclusions | Candidate for Engineering Review only |
| Real stock | RFQ availability, stock KPIs, stock-shortage scenario | NOT_CONNECTED / demo |
| Lead time | RFQ deadline check, delivery promise | NOT_CONNECTED |
| Compliance evidence | Compliance PASS, expiry, gate on candidates | UNVERIFIED (demo) |
| Dealer questions + answers | Measured search quality, regression set | Verified 34-question catalogue only |
| Real orders/shipments | Traceability / status / customs KPIs on real volume | Demo orders |
| Real BOM | Real assembly impact and criticality | Demo assemblies |
| Installed base | Customer impact | Empty |

## E. What we should NOT build until that data exists

- MCP server or host, and any real-time integration (nothing to serve or connect until C1–C4 exist).
- Neural embeddings (no evaluation set to show they help — C6 first).
- Customer installed-base impact, warranty, affiliate/partner entities (no data, and "affiliate" is not yet defined).
- Cross-catalog matching accuracy (one catalogue, no ground truth).
- Country/region supplier disruption (no supplier → part links for the real suppliers).
- Severity scores or weighted mitigation scores (no validated HCME rules).
- More synthetic supplier, stock, compliance or customer records to make features look complete.
- Connector/automotive attributes (HCME parts do not have them).

## F. Proposed pilot phase

**Goal:** prove value on one real product area with real data, replacing the demo layer there and nowhere else.

1. **Scope (weeks 1–2):** choose one product family with the most dealer questions (suggest the starter/traction batteries and hydraulic parts already in the catalogue), one depot (Oosterhout) and 3–5 pilot dealers.
2. **Data (weeks 1–4, in this order):** C6 dealer questions → C1 supplier-part links for the pilot family → C2 supersession for the pilot family → C3/C4 stock and lead time → C5 compliance evidence.
3. **Build only what the data enables (weeks 3–6):** load real relationships with `synthetic=false`; switch the same screens from demo to real; no new features.
4. **Measure (weeks 5–8):** search top-5 accuracy on the real question set; share of pilot parts with real supplier link / interchangeability status / stock; dealer time-to-answer versus today.
5. **Decision gate:** expand to more product families only if the accuracy and coverage targets agreed with HCME are met.

**Success criteria (to be agreed with HCME, not set by us):** search accuracy on real questions; % of pilot parts with real supplier link, interchangeability status and stock; zero unlabelled demo data on pilot screens.

## Known rough edges (not fixed in this freeze, by design)

- "Which parts fit <machine>?" ranks generic product-line records (e.g. Genuine Oil Filter) first with a heuristic match %; "What hydraulic parts fit ZX210LC-7?" gives the more specific answer and is the verified catalogue question.
- With Gemini on, the wording of an answer can vary; the cards and data are authoritative. With Gemini off the deterministic wording is used.
- The data audit reports 4 of 42 checks: two are documented source limits (4 dealers without usable coordinates, 22 duplicate supplier names); two (3 requests without an order, 23 fulfilment options marked CONFIRMED by the mock transport) come from manual Parts Store test sessions and should be cleared before a stakeholder demo.
