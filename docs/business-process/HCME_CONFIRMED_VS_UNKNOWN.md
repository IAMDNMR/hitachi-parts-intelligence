# HCME Confirmed vs Unknown vs TO-BE

**Phase:** 1 — Business Process Design
**Source of truth:** `OEM Parts Fulfilment Research Package (HCME).pdf` (Phase 0)
**Status:** This is the authoritative ledger for this phase. Every other document in `docs/business-process/` must defer to this table. No document may upgrade an UNKNOWN row here into a stated fact.

## Legend

- **CONFIRMED** — Directly stated in the Phase 0 research, sourced from an official OEM/HCME page or a primary document.
- **UNKNOWN** — Actively researched in Phase 0 and not found. Treated as a real gap, not an oversight.
- **TO-BE decision needed** — A choice HCME/business stakeholders must make; Phase 0 research gives no verdict either way because the question is about *our* future system, not about what exists today.

## The table

| Area | Confirmed | Unknown | TO-BE decision needed |
|---|---|---|---|
| Dealer structure | Hitachi's Americas dealer network went independent in 2021 (after the Deere–Hitachi joint venture wound down) and reached ~90% North American coverage by mid-2025. Historical distribution agreements grant dealers exclusive territory covering machines **and service parts/components**. | Exact HCME Europe dealer count, territory map, and current contractual terms. | Which European dealers/branches participate in the Phase 1 workflow, and in what capacity. |
| European depot structure | Global tiered structure exists: dealer stock → 4 regional parts depots → Central Parts Depot (Tsukuba, Japan), operating 24/7/365, AEO customs-certified for fast cross-border clearance. | Number, location, and capability of the specific European regional depot(s) within that 4-depot network. | Which depot(s)/tier(s) the fulfilment process is allowed to query and offer as a source. |
| Inventory source | Confirmed digital touchpoints exist: Dealer Portal 2.0 (dealer-only), Selected Parts search/export tool, Online Parts Finder / ConSite ISF (Europe). | The authoritative system of record for stock quantities at any tier (dealer, regional, central). Whether real-time stock is exposed anywhere outside these portals. | Which inventory source(s) the platform is authorised to read from, and how "authoritative" is defined per tier. |
| ERP | — | No HCME-specific ERP system publicly confirmed. (Industry-wide patterns — SAP DBM, Infor CloudSuite Equipment — are documented in Phase 0 as general OEM/dealer practice, not as HCME's system.) | Not a Phase 1 decision — explicitly deferred to Phase 2 technical design, and even then requires HCME confirmation before assumption. |
| WMS | — | No HCME-specific WMS publicly confirmed. General practices (wave picking, cross-docking, cycle counting) are documented in Phase 0 as industry norms only. | Deferred to Phase 2; requires HCME confirmation. |
| Pricing | Industry-wide pattern confirmed across Hitachi, Caterpillar and Komatsu: parts pricing is not publicly published; it is dealer-quoted / account-specific. Hitachi confirms three part tiers (Genuine, Remanufactured, Selected). | The actual HCME pricing engine, price list, or pricing rule source. | Which approved pricing source/rule the Order stage is authorised to call, and how customer/dealer-specific pricing is resolved. |
| Allocation | — | No published Hitachi allocation or priority policy. (For comparison only: Caterpillar publishes a credit-backed "Services Commitment"; Volvo CE publishes a 24-hour guarantee. Neither has a confirmed Hitachi equivalent.) | Whether HCME wants a formal allocation policy, and what its rules should be. Phase 1 defines only the *system capability* to support allocation, not the policy itself. |
| VOR / priority rules | — | No Hitachi VOR (vehicle-off-road) or emergency-priority process found in Phase 0 research. | Whether HCME needs a VOR/priority tier at all, and if so, who defines its rules. |
| Order system | Dealer Portal 2.0 and Selected Parts exist as confirmed customer/dealer-facing tools. | Which system is the system of record for a created order; whether an order-management system is exposed for integration. | Which system Phase 2 will treat as the order system of record. |
| Shipment system | AEO (Authorized Economic Operator) customs certification is confirmed at the Central Parts Depot and Ami Parts Center, enabling simplified/expedited cross-border customs clearance. | No named carrier, shipment-management system, or tracking API confirmed for Hitachi. | Which carrier(s)/logistics providers HCME approves for integration. |
| Carrier | — | No carrier named anywhere in the Phase 0 research for Hitachi. | Carrier selection is an HCME commercial decision, not a research finding. |
| Tracking | — | No customer- or dealer-facing shipment tracking portal or API confirmed for Hitachi. | Whether tracking is sourced from the carrier, a TMS, or a manual dealer update — TO-BE. |
| Service system | ConSite is confirmed to exist and to link machine maintenance alerts to dealer parts preparation (human-mediated, not automated ordering). | Whether a dedicated service-job management system exists at HCME, and whether it is separate from ConSite. | Which system, if any, owns the service job lifecycle defined in this phase. |
| Authentication | Dealer Portal 2.0 is confirmed to require a login (i.e., it is access-gated). | The authentication model, identity provider, or credential scheme behind that login. | Authentication approach is explicitly out of scope for Phase 1 (see `PHASE_1_DECISIONS.md`) and deferred to Phase 2. |
| Customer identity | — | No confirmed customer identity model, account structure, or customer master system. | TO-BE, Phase 2+. |
| Dealer identity | A dealer locator exists (dealers are a discoverable, named entity). | No confirmed dealer master data model, unique dealer identifier scheme, or dealer-capability registry. | TO-BE — see `ACTORS_AND_RESPONSIBILITIES.md` for the dealer data fields this phase requires but cannot yet source. |
| Telematics integration | A public Telematics API compliant with ISO 15143-3 / AEMP 2.0 exists and is confirmed. ConSite is confirmed to surface machine alerts to dealers, who then manually prepare/order parts. | The API's authentication model and access pricing (the documentation page could not be reached in Phase 0 research). | Telematics is explicitly **not** a Phase 1 dependency — see `HCME_PARTS_FULFILMENT_PROCESS.md` §Future Inputs. If/when it is integrated, it enters as an upstream trigger only, never as an automatic allocation or ordering decision. |

## Rule for downstream documents

Any process document that needs one of the UNKNOWN rows above must:

1. Reference this table by area name rather than restating a guess.
2. Define the **system capability** required (e.g., "the platform must be able to accept an inventory quantity from an external source, tagged with a timestamp and confidence status") without naming or assuming the specific external system.
3. Leave the actual integration, system name, and policy as an open item in `HCME_BUSINESS_QUESTIONS.md`.
