# HCME Europe Parts & Dealer Data Research

Research pass conducted 2026-09-23. Live-web research plus a structured audit of the existing
Neo4j CSV/Cypher data foundation (`docs/data/neo4j/`). This document follows the same
provenance system already in use in this repository (`source_id`, `confidence`, `data_class`,
`source_date`, `record_class` — see `docs/data/neo4j/data/provenance.csv` and
`docs/data/neo4j/reports/FINAL_GRAPH_SCHEMA.md`). No parallel scheme is introduced.

## 1. Executive Summary

This pass had two real deliverables and one honest non-deliverable:

- **Dealer network (delivered):** the HCME Europe dealer-network locator page loads a single
  **global** JSON feed (927 locations, all Hitachi Construction Machinery territories
  worldwide — Japan, the Americas, Africa, the Middle East, Asia-Pacific, and Europe combined).
  This feed was inspected via the page's own public network request (no auth, no bypass — see
  Section 3), filtered down to **182 records in geographic Europe** after removing one exact
  duplicate, and imported as `(:DealerBranch)` nodes with full provenance. This is genuinely new
  data — no dealer data of any kind previously existed in this repository.
- **Existing parts data audit (delivered, and it surfaced a real problem):** the existing
  `parts.csv` (60 rows, added across several prior sessions) contains **10 rows explicitly
  marked "INTERNALLY GENERATED DATA" (PT-044–PT-053)** and **7 further rows (PT-054–PT-060)**
  that cite `SRC-042` — a source whose own provenance description ("Official dealer page /
  Dealer network / Service delivery channel") has nothing to do with the LED light bars,
  starter motors, and alternators those 7 rows describe, and one of which (PT-054... actually
  PT-054 is a light bar; the placeholder-pattern part number belongs to another row, see
  Section 17) uses the digit sequence `12345678`. These 17 rows are flagged in Section 17/18 as
  synthetic or synthetic-adjacent and were **not deleted or altered** — per Part J of the task
  brief, existing data is reported on, not silently modified.
- **Parts catalogue re-research (not repeated in depth):** the existing 60-row parts dataset
  already represents substantial prior HCME Europe web research with real `SRC-0xx` citations.
  This session verified the *current* live category list (Section 7) and the access level of
  the Online Parts Finder / ConSite ISF and HCME Webshop (Sections 13–15), but did not re-scrape
  every parts sub-page — that work was already done in prior sessions and re-doing it from
  scratch was not the highest-value use of this session's time given the dealer network had
  **zero** prior coverage. This is flagged as a checkpoint, not a completed re-verification of
  every existing part record's live URL.

## 2. Geographic Scope

**HCME EUROPE ONLY.** This document and the corresponding data import cover only European
Hitachi Construction Machinery (Europe) NV data. The dealer-network source feed is global (see
Section 3); it was explicitly filtered to a 44-country geographic-Europe list before any data
was extracted or imported (Section 8/11). No US, Japanese, or non-European dealer, machine, or
parts data was imported. Two countries in the raw feed sit on the conventional Europe/Asia
boundary (`RU` – Russia, 3 raw records; `TR` – Turkey, 9 raw records) and were **excluded** as a
documented boundary decision, not silently dropped — see Section 8.

## 3. Official HCME Europe Sources

| Source | URL | Region | Data available | Access | Authority | Usability |
|---|---|---|---|---|---|---|
| Dealer Network page | `https://www.hitachicm.com/eu/en/dealer-network/` | Global (embedded in EU site) | Renders a dealer locator UI | Public, no auth | Official (HCME) | Page itself; data comes from the JSON below |
| Dealer locator JSON feed | `https://www.hitachicm.com/content/hitachicm/eu/en/dealer-network/jcr:content/root/container/dealerlocator.json` | **Global**, not Europe-filtered | 927 dealer/location records worldwide, all fields listed in Section 9 | Public, no auth — this is the exact request the dealer-network page itself makes to render the map/list any visitor sees; no hidden/undocumented endpoint was probed | Official (HCME) | High — used as primary source for Section 8, filtered to Europe by this research |
| Parts landing page | `https://www.hitachicm.com/eu/en/parts/` | Europe | Current parts category list (Section 7) | Public | Official | High |
| Online Parts Finder / ConSite ISF marketing page | `https://www.hitachicm.com/eu/en/service/fleet-management/online-parts-finder/` | Europe | Marketing description of ConSite ISF capabilities; a "Request more information" contact form | Public page; actual tool is authenticated | Official | Marketing-level only (Section 13) |
| HCME Webshop | `https://www.hcmewebshop.com` | International (Shopify storefront) | Public EUR retail pricing for **merchandise** (scale models, apparel, accessories) — **not genuine replacement parts** | Public, no auth for browsing; checkout requires standard e-commerce account/payment | Operated by "The Merchandise Company B.V." under HCME licence, not HCME's own parts-ordering system | Corrects a wrong assumption in the task brief — see Section 15 |
| `provenance.csv` / `FINAL_GRAPH_SCHEMA.md` | repo | N/A | Existing provenance conventions | N/A | Internal | Reused, not replaced |

## 4. Parts Catalogue Findings

No new parts were extracted in this session. The existing `docs/data/neo4j/data/parts.csv`
(60 rows) already represents prior real HCME Europe research (`SRC-016`, `SRC-027`, `SRC-030`
through `SRC-039` — battery compliance pages, official category/product pages) plus 17 rows of
concern flagged in Section 17. The current live category taxonomy was re-verified (Section 7)
and matches the existing repo's category conventions closely, with one addition: **AdBlue®** is
now a distinct nav item on the live site and was not previously represented as a category.

## 5. Machine Findings

Not re-researched this session — `machines.csv` / `machines.cypher` already exist from prior
work and were out of scope for this pass, which was scoped to the dealer network (net-new) and
an audit of parts/provenance quality (Part J). No machine data was added or altered.

## 6. Machine–Part Fitment Findings

Not touched this session. `machine_part_fitment.csv` / `.cypher` already exist. No new fitment
relationships were created — this session added no `(:Machine)-[:HAS_PART_FITMENT]->(:Part)`
edges, consistent with the rule that fitment is only ever created from an explicit European
source statement, which this session did not newly research.

## 7. Parts Categories

Verified live from `https://www.hitachicm.com/eu/en/parts/` and its footer navigation
(2026-09-23), superseding any hardcoded list assumption:

Service, **Parts**, Filters, Ground Engaging Tools, Wheel loader and excavator buckets,
Remanufactured components, Performance Parts, Undercarriage, Paint, **Fluids**, **AdBlue®**,
plus Online Parts Finder (under Fleet Management) and Dealer Network as separate nav items.
"Wheel loader and excavator buckets" is the exact current label (not simply "Buckets"), and
AdBlue® is a category not previously represented in the repo's existing category data.

## 8. Dealer Network Findings

The dealer-network page (`/eu/en/dealer-network/`) renders its list/map from a single public
JSON feed (Section 3) that is **not** pre-filtered to Europe — it is Hitachi Construction
Machinery's entire global dealer network (927 raw records spanning Japan, the US/Canada,
Australia/NZ, India, the Middle East, Africa, and Europe). This is documented explicitly here
per the task's "global source, document the distinction" rule.

**Filtering methodology:** raw `country` codes were matched against a 44-entry geographic-Europe
ISO-3166 list (`AL AD AT BY BE BA BG HR CY CZ DK EE FI FR DE GR HU IS IE IT LV LI LT LU MT MD MC
ME NL MK NO PL PT RO SM RS SK SI ES SE CH UA GB VA`). This is a conservative geographic (not
commercial-territory) definition. Two transcontinental countries appearing in the raw feed were
deliberately **excluded** rather than silently kept or dropped:

- `RU` (Russia) — 3 raw records — excluded as a documented boundary call, not evaluated for
  HCME Europe commercial territory.
- `TR` (Turkey) — 9 raw records — excluded on the same basis.

If HCME Europe's own commercial territory documentation (not found publicly during this pass)
defines these differently, that is a decision for a future pass, not one this pass made silently.

183 records matched the Europe list; **1 exact duplicate** (identical `dealerName` +
`dealerAddress`: "Probst Maveg Osogna", Via Cantonale 49, CH-6703 Osogna, appearing twice
verbatim in HCME's own feed) was removed, leaving **182 imported `DealerBranch` records**.

Several dealer names repeat with different addresses (e.g. "Kiesel Süd GmbH" × 11, "Kiesel Nord
GmbH & Co. KG" × 7) — these are almost certainly the same commercial group's separate branches,
but the source feed states no explicit parent-organisation relationship, so **no
`(:Dealer)`-level grouping node or edge was invented**; each remains a distinct `DealerBranch`
with `dealer_name` as a plain string property (see `docs/data/neo4j/import/nodes/dealers.cypher`
header comment for the full reasoning).

No territory, service-region, inventory, or warehouse relationship was inferred from dealer
existence — per the task brief, dealer existence does not imply inventory.

## 9. Dealer Data Fields

Fields actually present in HCME's own feed and imported (nothing invented beyond these):
`dealer_id` (assigned row-position key, `DLR-0xx` — see Section 19 for why), `dealer_name`,
`address` (single free-text field as published — not parsed into street/postal-code because
HCME does not publish it pre-parsed), `city`, `country` (ISO-2), `state_province`, `sub_region`,
`phone`, `email`, `website`, `product_categories` (HCME's own taxonomy tags, e.g.
`large-excavator;compact-wheel-loader`), `latitude`, `longitude`, `enquiry_link`, plus the
standard provenance columns (`region=HCME_EUROPE`, `data_class`, `source_id`, `confidence`,
`source_date`, `record_class=DEALER_BRANCH`). `openingHours`, `fax`, `availableServices`,
`rentalProductCategories` exist in the raw feed but were empty/unpopulated for essentially every
European row and were not carried into the CSV to avoid a wall of empty columns; they remain
available in the raw JSON in `docs/data/neo4j/data/provenance.csv` (SRC-049) if a future pass
needs them.

## 10. Dealer Count

**182** `DealerBranch` records actually extracted and imported (183 matched the Europe country
filter; 1 exact duplicate removed). This is the real, counted figure — not a target or estimate.

## 11. Country Distribution

| Country | Count | Country | Count | Country | Count |
|---|---|---|---|---|---|
| DE (Germany) | 68 | CH (Switzerland) | 4 | HR (Croatia) | 1 |
| FR (France) | 20 | LT (Lithuania) | 3 | IE (Ireland) | 1 |
| NL (Netherlands) | 19 | UA (Ukraine) | 2 | CY (Cyprus) | 1 |
| GB (United Kingdom) | 17 | LV (Latvia) | 1 | RO (Romania) | 1 |
| IT (Italy) | 17 | SE (Sweden) | 1 | HU (Hungary) | 1 |
| AT (Austria) | 5 | DK (Denmark) | 1 | BY (Belarus) | 1 |
| BE (Belgium) | 4 | GR (Greece) | 1 | IS (Iceland) | 1 |
| ES (Spain) | 4 | PL (Poland) | 1 | RS (Serbia) | 1 |
| | | PT (Portugal) | 1 | BG (Bulgaria) | 1 |
| | | NO (Norway) | 1 | | |
| | | CZ (Czechia) | 1 | | |
| | | EE (Estonia) | 1 | | |
| | | FI (Finland) | 1 | | |

**30 countries**, 182 branches total.

## 12. European Depot/Supply Chain Findings

Not researched in depth this session (out of scope given the time budget was spent on the
higher-value dealer-network gap). No European Parts Centre / warehouse capacity figures were
found or imported. This remains **UNKNOWN** and is a candidate for a future pass — do not treat
this silence as "none exists," only as "not researched yet."

## 13. Pricing Findings

No genuine HCME Europe OEM parts pricing was found publicly. The only public EUR pricing found
(`hcmewebshop.com`) is for **merchandise** (scale models, apparel), not replacement parts — see
Section 15. This confirms and does not contradict the prior research report's finding
(`HCME_PRICING_ORDER_INTEGRATION_RESEARCH.md`). `PricingProvider` remains untouched, still
`NOT_AVAILABLE`.

## 14. Inventory Findings

No European dealer/depot inventory, stock levels, or lead times found publicly. `UNKNOWN`.
`InventoryProvider` untouched.

## 15. Ordering Findings

**Correction to an assumption in the task brief:** "HCME Webshop" (`hcmewebshop.com`) is **not**
a parts-ordering channel. It is a Shopify-hosted merchandise storefront ("Official Hitachi
Construction Machinery Merchandise") selling scale models, apparel and accessories, operated
under licence by a third party ("The Merchandise Company B.V. / CodeIQ B.V."), with standard
retail checkout (cards, PayPal, Klarna, etc.). It carries genuine public EUR prices (e.g. a
"Scale EX1200-7 Large Excavator" model at €189.26) but these are **not** replacement-part
prices and have no bearing on parts ordering. No public European OEM parts order-creation,
status, or fulfilment API was found. `OrderProvider` remains untouched, `NOT_CONNECTED`.

**ConSite ISF / Online Parts Finder:** the public marketing page
(`/eu/en/service/fleet-management/online-parts-finder/`) describes the tool's capabilities
(search by machine model code/name/part number, exportable/printable/emailable parts lists,
part illustrations) but the tool itself is not embedded or reachable from that public page — only
a lead-generation "Request more information" contact form is public. Classified
**DOCUMENTED BUT ACCESS-RESTRICTED**, consistent with the task's explicit instruction not to
bypass this.

## 16. Existing Neo4j Data Audit

Audited via the repository's CSV files (no live AuraDB query was run this session — `backend/.env`
exists but a live connection was not attempted since the CSV files already gave a complete,
faster answer to the audit questions asked). Findings:

- **Parts (`parts.csv`, 60 rows):** 37 `ORDERABLE_OEM_PART` + 23 `PRODUCT_LINE_PART_FAMILY`.
  Zero duplicate part numbers. Zero rows missing a `Source ID`. **However**, 10 rows
  (PT-044–PT-053) are labelled `data_class = "INTERNALLY GENERATED DATA"`, `confidence = LOW`,
  citing `SRC-048`, whose own provenance description reads *"Internally generated / AI-illustrated
  — not an HCME publication"* — this is disclosed in the provenance file itself, which is good
  practice, but these 10 rows are **not real HCME data** and are currently indistinguishable from
  genuine rows by `record_class` alone (all still tagged `ORDERABLE_OEM_PART`). See Section 17/18
  for the more serious finding: 7 further rows (PT-054–PT-060) are tagged `HIGH` confidence /
  `"OFFICIAL WEBSITE DATA"` citing `SRC-042`, but `SRC-042`'s actual provenance description
  ("Official dealer page / Dealer network / Service delivery channel") does not match the LED
  light bar / starter motor / alternator content of those rows at all.
- **Dealers:** zero pre-existing records of any kind (`(:Dealer)` / `(:DealerBranch)` did not
  exist anywhere in `docs/data/neo4j/import/` or `docs/data/neo4j/data/` before this session,
  and no label for either existed in `backend/app/db/neo4j/schema.py`). `DATA_OWNERSHIP.md` and
  `DEALER_ARCHITECTURE.md` both explicitly documented this as `TO-BE`/`UNKNOWN` prior to this
  session. This session is the first to populate real dealer data.
- **US/non-European contamination in existing parts data:** none found — all 60 existing part
  rows' descriptions and sources reference European HCME pages (Zaxis/ZX model families, EU
  compliance pages). No contamination found.
- **Provenance file:** 48 `SRC-0xx` entries prior to this session (all real, dated 2026-09-10,
  except `SRC-048` which is explicitly self-disclosed as internal/non-HCME). This session added
  `SRC-049` for the dealer-locator feed.

## 17. Data Quality Findings

Two distinct quality problems exist in the pre-existing `parts.csv`, both **left in place**
(not deleted — see Section 16/20/21 and the task's explicit "report, don't silently modify"
instruction) but flagged here for a deliberate follow-up decision:

1. **PT-044–PT-053** (10 rows): honestly self-disclosed as internally generated / AI-illustrated
   via `SRC-048` and `confidence=LOW`. The disclosure is correct and traceable, but their
   `record_class` of `ORDERABLE_OEM_PART` is misleading — a `PRODUCT_LINE_PART_FAMILY`-adjacent
   or a genuinely new `record_class` (e.g. `REFERENCE_ONLY` or a dedicated synthetic marker) would
   more honestly represent that these are not verified real OEM part numbers. Recommend a
   follow-up pass to either relabel or remove them.
2. **PT-054–PT-060** (7 rows): tagged `confidence=HIGH`, `data_class="OFFICIAL WEBSITE DATA"`,
   citing `SRC-042`. `SRC-042` in `provenance.csv` is titled "Dealer network" /
   "Service delivery channel" with no connection to LED light bars, starter motors, or
   alternators. One part number in this range (`12345678`) is a placeholder-pattern digit
   sequence, not a real Hitachi part number format. **This citation appears to be incorrect or
   fabricated**, and the `HIGH` confidence label on these rows should not be trusted without
   independent re-verification against a real HCME source. This is the most important finding
   of this audit and is called out explicitly rather than silently corrected, per the task's
   instruction not to destructively alter existing data without the report making the case first.

## 18. Duplicate Findings

- **Dealers:** 1 exact duplicate found and removed in the source feed itself (Section 8) —
  "Probst Maveg Osogna" appeared twice with byte-identical name+address. 0 duplicates remain in
  the imported 182-row set (verified by exact name+address key — see Section 20 validation).
  7 dealer *names* repeat across genuinely distinct addresses (multi-branch groups) — these are
  correctly kept as separate `DealerBranch` rows, not treated as duplicates.
- **Parts:** 0 duplicate `Part Number` values in the existing 60-row set (verified this session).
  The 17 rows flagged in Section 17 are a provenance/authenticity problem, not a duplication
  problem.

## 19. Provenance

All 182 imported dealer rows carry `source_id = SRC-049` (added to `provenance.csv` this
session: *"Official website - dealer locator JSON feed (public network request made by the page
itself)"*, dated 2026-09-23, `Official Source = Yes`), `data_class = "OFFICIAL WEBSITE DATA"`,
`confidence = HIGH`, `region = HCME_EUROPE`, `record_class = DEALER_BRANCH`.

**Why `dealer_id` is a row-position key (`DLR-001`…`DLR-182`) rather than an HCME-native
identifier:** HCME's feed does not publish any dealer/location ID field — `dealerName` is the
only stable-looking identifier, and it is not unique (multi-branch groups share it, Section 8).
A synthetic sequential key was therefore used, exactly as `PT-xxx`/`DLR`-style keys are already
used elsewhere in this repo for rows without a natural key — this is not "inventing data," it is
a row identifier, and every substantive field on the row is HCME's own published data.

## 20. Data We Can Import

- 182 `DealerBranch` nodes (imported this session — `docs/data/neo4j/data/dealers.csv` +
  `docs/data/neo4j/import/nodes/dealers.cypher`).
- Existing 60 `Part` rows remain importable as before (unchanged this session), with the caveat
  in Section 17 that 17 of them warrant a follow-up trust/relabelling decision before being
  surfaced to a user as equivalent-confidence data to the other 43.

## 21. Data That Must Remain UNKNOWN

Dealer territory/service-region boundaries, dealer inventory/stock, dealer-to-machine
relationships, dealer-to-part fulfilment relationships, European depot/warehouse live capacity
or inventory, EUR parts pricing, parts inventory/lead times, and any European parts order API.
None of these were found publicly and none were fabricated. `PricingProvider`,
`InventoryProvider`, and `OrderProvider` are untouched.

## 22. Data That May Later Be Synthetic

None was added as synthetic in this session. The pre-existing PT-044–PT-060 rows (Section 17)
already are synthetic-or-suspect and are flagged, not newly created.

## 23. Recommended Neo4j Structure

`(:DealerBranch {dealer_id, dealer_name, address, city, country, state_province, sub_region,
phone, email, website, product_categories, latitude, longitude, enquiry_link, region,
record_class, data_class, source_id, confidence, source_date})`, unique-constrained on
`dealer_id` (added to `docs/data/neo4j/import/01_constraints.cypher` this session). No
`(:Dealer)` parent/organisation node was added (Section 8 — not supported by source data). No
`DealerBranch`-to-`Part`/`Machine` relationship of any kind was added — per the task brief, that
requires an explicit HCME statement this pass did not find. This is additive only: no existing
label, constraint, or Phase 6 entity was touched.

## 24. Source URLs

- `https://www.hitachicm.com/eu/en/dealer-network/`
- `https://www.hitachicm.com/content/hitachicm/eu/en/dealer-network/jcr:content/root/container/dealerlocator.json`
- `https://www.hitachicm.com/eu/en/parts/`
- `https://www.hitachicm.com/eu/en/service/fleet-management/online-parts-finder/`
- `https://www.hcmewebshop.com`
