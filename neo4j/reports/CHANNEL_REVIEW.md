# Channel Review — CH-EXTERNAL

## Source value
`To Name: "Yes (BNP Paribas Leasing Solutions; DLL)"`

## Source location
`13_AFTER_SALES_RELATIONSHIPS`, row `REL-3276`: `Service (SVC-022, "Financing / leasing (ZAXIS Finance)") --DELIVERED_BY--> Channel (CH-EXTERNAL)`, `Data Class: OFFICIAL WEBSITE DATA`, `Source ID: SRC-043`, `Notes: "External authorised provider named on the official page."`

## Evidence

`CH-EXTERNAL` is referenced by **two** different relationship rows in `13_AFTER_SALES_RELATIONSHIPS`, and each carries a **different** `To Name`:

| Relationship ID | From Service | To Name |
|---|---|---|
| `REL-3269` | SVC-016 "Remanufacturing / core exchange" | `"Yes (Reman centre)"` |
| `REL-3276` | SVC-022 "Financing / leasing (ZAXIS Finance)" | `"Yes (BNP Paribas Leasing Solutions; DLL)"` |

By contrast, `CH-DEALER` is referenced by many rows and every one of them carries the **same** `To Name`: `"HCME authorised dealer network"`.

Checked `14_SOURCE_REGISTER` and `00_README` for any independent definition of `CH-EXTERNAL` or a "Channel" concept — neither sheet defines Channel as an entity at all; it exists only inside `13_AFTER_SALES_RELATIONSHIPS`'s own `To Entity Type`/`To ID`/`To Name` columns.

## Finding

**A — genuinely source-defined, but not what it was being read as.** The text is real, official-page-sourced content (per the row's own `Notes`), not copied from an unrelated field and not garbage. But it is not a fixed *label for the Channel*, as the earlier import design treated it — it's the answer to a **per-service** question ("is this service delivered through an external authorised provider, and if so, who?"). `CH-EXTERNAL` is a generic "external provider" channel type; which specific company plays that role varies by which service is being delivered (a remanufacturing centre for SVC-016, two named finance companies for SVC-022).

This is not ambiguous or unresolved at the evidence level — the meaning is clear once both rows are compared side by side. The earlier design's mistake was reading a per-relationship fact into a per-node property, based on inspecting only one row (`REL-3276`) in isolation.

## Recommended graph treatment

- `Channel {channel_id: 'CH-EXTERNAL'}.label` = a stable, generic description (`"External authorised provider (varies by service — see provider_detail on each DELIVERED_BY relationship)"`), not any one service's specific provider name.
- The per-service provider text moves to `provider_detail` on the `DELIVERED_BY` relationship connecting that specific `Service` to `Channel` — implemented in `neo4j/import/relationships/channel_relationships.cypher`.
- `Channel {channel_id: 'CH-DEALER'}.label` = `"HCME authorised dealer network"`, unchanged — its text genuinely is stable across every referencing row, confirmed above.

No value was removed, guessed, or replaced — both original texts (`"Yes (Reman centre)"` and `"Yes (BNP Paribas Leasing Solutions; DLL)"`) are preserved verbatim, just relocated to the relationship where they're each actually true, instead of collapsed into one Channel-level property where only one of them could ever survive.
