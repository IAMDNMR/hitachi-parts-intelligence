// DealerBranch — 182 rows expected (HCME Europe dealer-network locator, filtered
// to geographic Europe only; see docs/research/HCME_EUROPE_PARTS_AND_DEALER_DATA_RESEARCH.md).
// Idempotent: safe to re-run (MERGE on dealer_id, which is a stable row-position
// key assigned during extraction — see Section 19 Provenance of the research doc
// for why no HCME-native dealer identifier exists to key on instead).
// Source data is a single flat dealer-network locator feed (dealer name + one
// address per row); it does not itself distinguish an organisation ("Dealer")
// from a physical location ("DealerBranch"). Several dealer_name values repeat
// across rows (e.g. "Kiesel Süd GmbH" appears 11 times with 11 different
// addresses) — these are almost certainly the same commercial group operating
// multiple branches, but the source never states that relationship explicitly,
// so no (:Dealer)-[:HAS_BRANCH]->(:DealerBranch) grouping is created here. Only
// the (:DealerBranch) node — the entity DEALER_ARCHITECTURE.md already models —
// is populated. dealer_name is kept as a plain property so a future pass can
// group branches once/if HCME publishes an explicit dealer-group identifier.
//
// No Dealer-[:STOCKS]->Part, -[:SUPPLIES]->Part, -[:FULFILLS]->Part, or
// -[:HAS_INVENTORY]->Part relationship is created anywhere in this import —
// dealer existence never implies inventory or fulfilment capability (see
// research doc Part D).
LOAD CSV WITH HEADERS FROM 'file:///dealers.csv' AS row
MERGE (d:DealerBranch {dealer_id: row.`Dealer ID`})
SET d.dealer_name         = row.`Dealer Name`,
    d.address             = row.Address,
    d.city                = row.City,
    d.country             = row.Country,
    d.state_province      = row.`State/Province`,
    d.sub_region          = row.`Sub Region`,
    d.phone               = row.Phone,
    d.email               = row.Email,
    d.website             = row.Website,
    d.product_categories  = row.`Product Categories`,
    d.latitude            = toFloat(row.Latitude),
    d.longitude           = toFloat(row.Longitude),
    d.enquiry_link        = row.`Enquiry Link`,
    d.region              = row.Region,
    d.record_class        = row.record_class,
    d.data_class          = row.`Data Class`,
    d.source_id           = row.`Source ID`,
    d.confidence          = row.Confidence,
    d.source_date         = row.`Source Date`;
