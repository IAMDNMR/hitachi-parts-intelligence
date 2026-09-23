# HCME Pricing / Order / Inventory Integration Research

Research pass conducted 2026-09-23. Scope: determine what REAL, legitimately-accessible
HCME/Hitachi data and integration surfaces actually exist, before any synthetic
pricing/order/inventory data is built for the prototype. This is a research report only —
no production code was changed as part of this task.

Method: public web research (HitachiCM corporate/regional sites, press releases, one
third-party dealer-software vendor site) via browser and web-search tools, plus a
read-only inspection of this repository's existing integration-contract, mock-provider,
module, and Neo4j-schema/seed-data code. No login walls, CAPTCHAs, or access controls were
bypassed; authenticated systems were identified and left untouched.

---

## A. Executive Summary

No real, publicly-accessible HCME/Hitachi API for **pricing**, **order submission**, or
**live inventory/availability** was found. What was confirmed to be real:

- HCME publicly markets several named parts/service systems — **ConSite ISF (Intelligent
  Service Parts Finder)**, **Global e-Service** (with **Owner's Site**, **ConSite**, and
  **"Hitachi Online Parts"**), and a separate **Telematics API** — but these are either
  marketing pages with a "request more information" contact form, or (for Telematics API)
  a real, documented API that covers **machine operational telemetry only** (location,
  fuel, hours, CO2), not parts, pricing, or ordering.
- HCME operates a real, login-only **Dealer Portal** (`hcmedealerportal.com`) and a
  **Dealer Locator** with no documented public API behind it.
- HCME publicly documents two real parts programmes — **Hitachi Genuine Parts** and
  **SELECTED PARTS** (undercarriage + GET) — at a marketing/catalog-PDF level, with no
  public pricing, part-level API, or machine-readable feed.
- A third-party dealer-management-software vendor, **Flyntlok**, publicly claims a live,
  bidirectional integration with Hitachi covering parts pricing, availability, PO
  submission, and warranty lookup ("100% Hitachi API Coverage"). This is Flyntlok's own
  marketing claim, not confirmed or documented by Hitachi/HCME anywhere this research
  found, and by its own description it operates only inside an authorized Hitachi dealer's
  DMS account — it is evidence that *some* real dealer-side integration layer likely
  exists, not usable evidence of a public API.
- No official Hitachi/HCME developer portal, OpenAPI spec, or public parts/pricing/order
  API documentation was found anywhere.

This means: **for pricing and ordering specifically, the codebase's existing honest
`NOT_CONNECTED` mock pattern (Part 3 below) remains the correct posture.** No new
synthetic pricing/order data should be built to look real. The one area with legitimately
importable *public* data is Genuine/Selected/Reman parts programme facts and dealer
locator-type reference data — consistent with what the Neo4j graph already imports today
(see §B/§C of the existing `docs/data/neo4j/reports/FINAL_GRAPH_SCHEMA.md`).

---

## B. Source Inventory

| Source | Owner | Data Available | Public? | Authentication | API Verified? | Authoritative? | Usable Now? |
|---|---|---|---|---|---|---|---|
| ConSite ISF (Online Parts Finder) | HCME | Marketing description only ("search by model code/name/part number, generate selected parts list, illustrations") | Marketing page yes; tool itself unknown | Unknown — page is "request more information" gated, tool not reached | No | N/A (not reached) | No |
| Global e-Service / Owner's Site / ConSite | HCME (via globaleservice.com) | Machine performance data (meter readings, location, fuel, CO2), maintenance info; "Hitachi Online Parts" referenced as part of the same ecosystem | Marketing description public; the application itself requires an account | Account required (Global e-Service login) | No public API doc found | N/A (not reached) | No |
| Telematics API | Hitachi Construction Machinery (global) | Machine operational telemetry (location, fuel consumption, hours, diagnostics), ISO 15143-3 / AEMP 2.0 compliant | Marketing/overview page public; API itself is not public | "Select one of several authentication methods"; "contact your Hitachi dealer" for applicable models/data/regions; some service tiers are paid | **Yes — real, named, standards-based API confirmed to exist** | Yes (HCM's own telemetry data) | **Not for this task** — scope is machine telemetry, not parts/pricing/order/inventory |
| HCME Dealer Portal (hcmedealerportal.com) | HCME | "Wide range of tools dedicated to support authorised dealers" | No — login wall is the entire visible surface | Dealer account (email/password) required | No | N/A (not reached — login not attempted) | No |
| HCME Dealer Locator / Dealer Network page | HCME | Interactive dealer search/list widget | Yes, public UI | None to browse | No API documented — do not assume one exists behind the widget | Yes (it's HCME's own public dealer directory) | Only as already-used public dealer facts (the app already holds this per the prior commit); no API to integrate against |
| Hitachi Genuine Parts | HCME / Hitachi CM (global + regional) | Marketing description; PDF brochure exists (`Genuine_Parts.pdf`, ZA region) | Yes | None | No | Yes, as marketing-level fact | Yes, as marketing-level reference text/provenance only — not pricing or SKUs |
| SELECTED PARTS (Undercarriage + GET) | Hitachi Construction Machinery (global) | Programme description, warranty parity claim, downloadable catalog PDFs (8.2–8.4MB) | Yes | None | No | Yes, as marketing-level fact | Catalog PDFs could be manually reviewed for programme-level facts (not attempted here — out of scope per Part 4 instructions, no numeric pricing was copied) |
| Flyntlok (third-party DMS) — "Hitachi Dealers" page | Flyntlok (NOT Hitachi/HCME) | Vendor's own description of a claimed Hitachi dealer integration: live parts pricing, stock levels, warehouse locations, two-way PO submission, warranty/PIP lookup, pricing/substitution file sync | Marketing page is public; underlying integration is inside Flyntlok's product, dealer-account-gated | Requires a Flyntlok+Hitachi-dealer relationship | **Unverified — third-party claim only, not confirmed by any Hitachi/HCME source** | **No — third-party, not authoritative** | No |
| LANDCROS Sales Navigator (press release, 2026-05-19) | Hitachi Construction Machinery (global) | Dealer *sales/CRM* info-management tool, rolling out Japan/SE Asia first | Yes, press release public | N/A (tool itself is internal to dealers) | No | Yes, as a fact that this tool exists | Not parts/pricing/order-relevant; noted only as evidence Hitachi is actively building dealer-side digital tools |
| Industry EDI patterns (850/855/846 etc.) | Generic industry (Cleo, EDI2XML, TrueCommerce, etc.) | General EDI transaction types used for PO, PO ack, inventory advice in manufacturing/equipment sectors | Yes | N/A | N/A | **Not Hitachi-specific — general industry context only** | For terminology/pattern reference only |

---

## C. Pricing Findings

| Field | Finding |
|---|---|
| SOURCE | No HCME/Hitachi public pricing source found. Flyntlok (third party) claims "live pricing" flows from Hitachi into dealer DMS. |
| DATA | Unknown at part-number-and-price-point granularity. HCME's own pages state parts are available "at competitive pricing" — no figures shown. |
| ACCESS | Public marketing pages describe programmes; no price list, price API, or price feed is publicly reachable. |
| AUTHENTICATION | Real pricing, if it exists in the form Flyntlok describes, sits behind an authorized-Hitachi-dealer DMS relationship — not attempted, not verifiable from outside. |
| API | No public pricing API or documentation found from Hitachi/HCME. Flyntlok's "100% Hitachi API Coverage" is an unverified third-party marketing claim. |
| REGION | Not applicable — no pricing data obtained. |
| CURRENCY | Not applicable — no pricing data obtained. The existing `ShippingRateProvider` mock defaults to EUR, consistent with HCME being the Europe/West Africa regional entity, but that is a shipping-cost mock default, not evidence of a real pricing currency. |
| FRESHNESS | Not applicable. |
| AUTHORITATIVE? | No. |
| CAN WE USE IT NOW? | **No.** Real pricing exists somewhere in Hitachi's dealer/DMS ecosystem (per the Flyntlok claim), but public access/API access was not verified. No price number should be treated as reusable data. |

---

## D. Order Findings

Flow: **CUSTOMER/DEALER → PARTS ORDER → HCME/Hitachi → ORDER CONFIRMATION → FULFILMENT → SHIPMENT**

| Stage | Status | Evidence |
|---|---|---|
| Customer/Dealer places parts order | Authenticated-only (inferred) | ConSite ISF lets a user "generate a selected parts list which can be exported and printed, or sent via email" — this is a *list generator*, not a confirmed order-submission mechanism. No evidence it submits an order directly. |
| Order transmitted to HCME/Hitachi | Unknown / third-party-claimed only | Flyntlok claims "two-way PO submission with real-time confirmation" from its DMS to Hitachi. Not confirmed by any Hitachi/HCME source. |
| Order confirmation | Unknown / third-party-claimed only | Same Flyntlok claim ("real-time confirmation," "order documentation routed back automatically"). No HCME-side documentation. |
| Fulfilment status | Unknown | No public documentation found. |
| Shipment status | Unknown | See §H. |
| Cancellation / backorder | Unknown | No public documentation found for any HCME-side workflow. |

**Conclusion:** no stage of the order flow is publicly verified. The only evidence of any
electronic order-submission mechanism is the unverified third-party (Flyntlok) claim,
which — even if true — is a dealer-DMS-to-Hitachi channel, not something this
consumer/dealer-facing prototype could call directly or document credentials for.

---

## E. Inventory / Availability Findings

| Category | Status | Evidence |
|---|---|---|
| Dealer stock | Unknown / third-party-claimed only | Flyntlok claims "stock levels, and warehouse locations" surface in real time via its Hitachi integration. Not HCME-confirmed. |
| Regional/central depot stock | REAL PUBLIC (fact of existence only) | HCME's own site confirms a real physical **"Hitachi European Parts Centre" in Oosterhout, Netherlands** — this is a real, named facility, but no stock-level data about it is public. |
| Lead time / backorder / alternative source | Unknown | Not documented publicly anywhere found. |
| Live availability feed/API | Unknown | No Hitachi/HCME-side public documentation. Flyntlok's claim is the only reference and is unverified/third-party. |

---

## F. Dealer / Depot / Supply-Chain Findings

What is realistically supportable as Neo4j nodes/relationships, based only on evidence
found:

- `(:Dealer)` / `(:DealerBranch)` — **supportable as reference data** (name, location,
  country served). HCME publicly operates a Dealer Locator; the repo's own
  `docs/architecture/DATA_OWNERSHIP.md` already documents `(:Dealer)`/`(:DealerBranch)`
  node labels as planned, currently `TO-BE`/`UNKNOWN` pending a real source (see Part 3
  below) — this research does not upgrade that status; it only confirms the dealer
  locator itself is real and public.
- `(:Depot)` — **candidate only.** One real, named depot fact was found: the "Hitachi
  European Parts Centre" in Oosterhout, NL. No address-level, capacity, or stock data is
  public. Any `(:Depot)` node built from this should carry only that one fact plus
  provenance, not invented depots.
- `(:Supplier)` — **no evidence found.** No public HCME documentation names third-party
  parts suppliers (aside from the general "Selected Parts" programme description, which
  names no specific supplier company). Do not create `(:Supplier)` nodes from this
  research.
- `(:Dealer)-[:SERVES]->(:Country)` — supportable at the level the dealer locator already
  implies (a dealer has a country/region), consistent with data the app already holds per
  the git history (dealer network data already ingested in a prior commit).
- `(:Depot)-[:SERVES]->(:Region)` — **not supportable from this research** — no public
  source states which regions the Oosterhout centre serves; would be an invented
  relationship.
- `(:Supplier)-[:SUPPLIES]->(:Part)` — **not supportable** — no supplier entities were
  confirmed.

---

## G. Cross-Reference / Supersession Findings

- HCME's own SELECTED PARTS programme is publicly and explicitly described as a *parallel,
  warranty-equivalent alternative* to Genuine Parts for the same machine applications
  (undercarriage and GET/bucket-teeth categories specifically). This is a real,
  HCME-documented **candidate relationship type** (Genuine Part ↔ Selected Part
  equivalent) — but the source pages describe it at a *programme* level, not a
  part-number-to-part-number cross-reference table. No specific Genuine-to-Selected part
  number pairing was found publicly.
- This repository's own Neo4j `Part` schema **already has `supersedes_part_number` and
  `superseded_by` fields** (`docs/data/neo4j/import/nodes/parts.cypher`, confirmed by
  reading the file), but the actual seed data (`docs/data/neo4j/data/parts.csv`) has these
  fields **empty for every row checked** — i.e., the schema anticipates supersession data,
  but no real supersession facts have been imported yet, and this research did not find
  any public source of genuine Hitachi part-number-to-part-number supersession data to
  fill them.
- No reman-part-to-genuine-part cross-reference table was found publicly.
- **Recommendation:** treat "Genuine Part X is functionally equivalent to Selected Part Y"
  as a candidate relationship only if/when specific part numbers for both are found in the
  same authoritative source (e.g., the SELECTED PARTS catalog PDF, not reviewed for
  part-level detail in this pass) — never infer it from similar-looking part numbers or
  category matches.

---

## H. Shipment / Tracking Findings

No public HCME/Hitachi documentation of shipment status, carrier, tracking numbers, a
shipment API, EDI, or logistics integration was found in this research. The existing
`RoutingProvider`/`ShippingRateProvider` mocks in this codebase (see Part 3) already
reflect this correctly — they return illustrative, clearly-`is_confirmed=False` test data,
not real carrier data, and nothing found here changes that. No carrier name or tracking
mechanism should be invented.

---

## I. Integration Opportunities

Mapped to the actual existing contract files (read directly in this research):

| Provider contract | Path | Real source found? | Recommendation |
|---|---|---|---|
| `PricingProvider` | `backend/app/integrations/contracts/pricing.py` | No | Keep `TestPricingProvider` (`backend/app/integrations/mocks/pricing_mock.py`) exactly as-is — it already always returns `NOT_AVAILABLE`. No real pricing source to wire in. |
| `OrderProvider` | `backend/app/integrations/contracts/order.py` | No (only unverified third-party dealer-DMS claim) | Keep `TestOrderProvider` (`backend/app/integrations/mocks/order_mock.py`) exactly as-is — already honestly returns `NOT_CONNECTED`. |
| `InventoryProvider` | `backend/app/integrations/contracts/inventory.py` | No | Keep `TestInventoryProvider` (`backend/app/integrations/mocks/inventory_mock.py`) as-is; its `production` branch already returns `UNKNOWN`/`UNCONFIRMED_EXTERNAL_API`, which matches this research's findings. |
| "DealerProvider" (no such contract file exists yet) | N/A — not present in `backend/app/integrations/contracts/` | Partial — public dealer locator exists, no API | If a `DealerProvider`-style contract is ever added, it should source from the same manually-curated public dealer-directory approach the app already uses (per git history), not a live API — none exists. |
| `RoutingProvider` / "ShipmentProvider" / "TrackingProvider" | `backend/app/integrations/contracts/routing.py`, `shipping_rate.py` (no dedicated Shipment/Tracking contract exists) | No | Keep `TestRoutingProvider`/`TestShippingRateProvider` as-is. No real carrier/tracking source exists to integrate. |

No code changes are recommended as a result of this research pass.

---

## J. Evidence / URLs

- https://www.hitachicm.com/eu/en/service/fleet-management/online-parts-finder/ — Confirms the real name **"ConSite ISF (Intelligent Service Parts Finder)"**; describes search-by-model/part-number and an exportable parts list; page is a "request more information" contact-form gate, not the tool itself.
- https://www.hitachicm.com/eu/en/service-parts/ — Confirms Hitachi Support Chain components (Global e-Service, HELP, Technical Support, Hitachi Parts); names **Owner's Site**, **ConSite**, and **"Hitachi Online Parts"** as sub-tools of Global e-Service (accessed via globaleservice.com, account-gated); confirms parts categories (Genuine, Reman, Performance Parts/GET, Undercarriage) with no pricing shown.
- https://www.hitachicm.com/global/en/solutions/telematics-api/ — Confirms a real, named **Telematics API**, ISO 15143-3/AEMP 2.0 compliant, for machine operational data only (location, fuel, hours); states authentication method is selectable and some tiers are paid; directs users to "contact your Hitachi dealer" for access — no public API docs/spec found.
- https://www.hcmedealerportal.com/ — Confirms the **HCME Dealer Portal** is a real, named, login-only system ("tools dedicated to support authorised dealers"); only login/account-creation UI is public.
- https://www.hitachicm.com/eu/en/dealer-network/ — Confirms a real, public **Dealer Locator** UI (search/filter/list); no API documented behind it — per the task's safety rules, an interactive search box does not itself imply a public API.
- https://www.hitachicm.com/global/en/products/parts-service/parts/selected-parts/ — Confirms the real **SELECTED PARTS** programme (Undercarriage + GET), warranty parity with Genuine Parts claim, downloadable catalog PDFs; no pricing or part-number data extracted.
- https://www.flyntlok.com/hitachi-dealers/ — **Third-party vendor claim** of a live Hitachi dealer integration (pricing, stock, PO submission, warranty/PIP lookup, "100% Hitachi API Coverage"). Not confirmed by any Hitachi/HCME source; treated as unverified evidence that *some* dealer-side integration exists, not as usable data or proof of a public API.
- https://www.hitachicm.com/global/en/news/press-releases/2026/26-05-19/ — Press release confirming **LANDCROS Sales Navigator**, a dealer sales/CRM data-management tool (not parts/pricing/order-related); cited only as evidence Hitachi is actively investing in dealer-facing digital tools.
- https://www.hitachicm.com/content/dam/hitachicm/za/en/docs/Parts/Genuine_Parts.pdf — Referenced in search results as a real Hitachi Genuine Parts brochure (South Africa region); not opened/reviewed in this pass, cited only as evidence such marketing collateral exists publicly.

---

## K. Confidence Tags

- ConSite ISF exists as a named tool: **CONFIRMED**
- Global e-Service / Owner's Site / ConSite / "Hitachi Online Parts" exist as named tools, account-gated: **CONFIRMED** (existence); **DOCUMENTED BUT ACCESS-RESTRICTED** (contents/data)
- Telematics API exists, is real, ISO 15143-3/AEMP 2.0 compliant, machine-telemetry-only: **CONFIRMED**
- Telematics API covers pricing/parts/order data: **UNKNOWN** — no evidence found; this research assumes it does NOT based on its stated scope (operational/telemetry data), but this is an absence-of-evidence inference, not a confirmed negative.
- HCME Dealer Portal exists, login-only: **CONFIRMED**
- HCME Dealer Locator exists publicly, no API confirmed: **CONFIRMED** (locator); **UNKNOWN** (any API behind it)
- Hitachi Genuine Parts / SELECTED PARTS programmes exist, warranty-parity claim: **CONFIRMED** (as marketing-level facts)
- Hitachi European Parts Centre (Oosterhout, NL) exists as a real depot: **CONFIRMED** (existence only — no stock/capacity data)
- Any live pricing feed, pricing API, or order-submission API from Hitachi/HCME: **UNKNOWN**
- Flyntlok's claimed Hitachi dealer integration (pricing, stock, PO, warranty): **THIRD-PARTY** — unverified by any Hitachi/HCME source
- Genuine-Part-to-Selected-Part specific number cross-reference data: **UNKNOWN** (programme-level equivalence is CONFIRMED as a concept; specific pairings are UNKNOWN)
- Part supersession data (`supersedes_part_number`/`superseded_by`) for any real HCME part: **UNKNOWN** — schema fields exist and are currently empty in the seed data
- Shipment/carrier/tracking API or EDI documented by Hitachi/HCME: **UNKNOWN** — no evidence found either way
- General EDI transaction types (850/855/846) as an industry pattern: **CONFIRMED** as general industry practice; **NOT Hitachi-specific** — no evidence Hitachi uses these codes

Nothing above has been upgraded to CONFIRMED without a direct, cited source.

---

## Recommended Next Step

**D. NO USABLE REAL DATA/API → recommend a clearly-labeled synthetic/demo provider,
consistent with the existing honest `NOT_CONNECTED` pattern already in this codebase.**

Justification, strictly from Parts 1–3 above: no real, public, machine-readable pricing,
ordering, or live-inventory source was found. The one real API found (Telematics API) is
out of scope (machine telemetry, not parts/commerce) and is access-gated through a dealer
relationship with no public documentation of endpoints or schemas. The one integration
that plausibly does provide real pricing/order/inventory data (the Flyntlok-Hitachi dealer
DMS integration) is a third-party product feature inside an authorized dealer's own
software, not something this prototype can call, and its existence is unverified by
Hitachi itself.

This does **not** mean building fake pricing/order data — that is explicitly out of scope
for this task per the instructions, and the existing `TestPricingProvider` /
`TestOrderProvider` / `TestInventoryProvider` mocks already do the right thing: they are
honestly labeled `NOT_AVAILABLE` / `NOT_CONNECTED` / `UNKNOWN` and should stay that way.
If a future implementer wants a richer *demo* experience for stakeholders, any such data
must be as explicit as the existing mocks already are about being illustrative test data,
never presented as a real HCME feed — this report does not propose implementing that here.

Option B ("real system exists but access is restricted") was considered but rejected as
the primary recommendation: while the Dealer Portal and Global e-Service clearly exist and
are real, restricted systems, this research found no concrete evidence (no credential
process, no published API surface, no documented dealer-onboarding path for API access)
that would let a future implementer meaningfully "keep the provider interface ready" with
specific target details beyond what the interfaces already assume. If HCME dealer
credentials become available through a business relationship, the correct file to revisit
first is `backend/app/integrations/contracts/order.py` and `pricing.py`, and the exact
Flyntlok-described data shape (pricing, stock, PO submission, warranty/PIP by serial
number) is a reasonable target schema to validate against real credentials if/when they
exist.

---

## Data Governance Rule

Any future Neo4j import of real or reference HCME/Hitachi data must carry provenance
fields **consistent with the convention already established in this codebase**, confirmed
by reading `docs/data/neo4j/reports/FINAL_GRAPH_SCHEMA.md` and
`docs/data/neo4j/import/nodes/parts.cypher`:

- `source_id` — a reference to a row in the existing `docs/data/neo4j/data/provenance.csv`
  ledger (already populated with real `SRC-###` entries, official-source URLs, and access
  dates) — **do not invent a parallel provenance-ID scheme.**
- `confidence` — `HIGH` / `MEDIUM` (existing convention; the codebase does not currently
  use a `LOW` tier in the parts data reviewed).
- `data_class` — `CORE` (`OFFICIAL WEBSITE DATA`) vs `DERIVED` (`DERIVED FROM OFFICIAL
  SOURCE`) — existing convention distinguishing directly-observed facts from
  inferred/derived ones; any new import must pick one honestly, never default to `CORE`.
- `source_date` — the date the source was accessed (matches `provenance.csv`'s `Date
  Accessed` column).
- `record_class` — already used on `Part` nodes to distinguish a real orderable SKU
  (`ORDERABLE_OEM_PART`) from a non-orderable concept (`PRODUCT_LINE_PART_FAMILY`) — any
  new Dealer/Depot/Supplier node type introduced later should define an equivalent
  explicit class field rather than letting a UI assume orderability/authoritativeness.

Separately, at the **API/provider integration layer** (not the Neo4j import layer), this
codebase already uses `status` values like `NOT_AVAILABLE` / `NOT_CONNECTED` / `UNKNOWN`,
an `is_confirmed` boolean (routing/shipping), and an `integration_status` +
`integration_label` pair (Order module's `get_order`). Any new provider added in future
should reuse these exact existing conventions rather than introducing new field names such
as `synthetic` or `retrieved_at`, which do not currently appear anywhere in this codebase's
schema or provider layer.
