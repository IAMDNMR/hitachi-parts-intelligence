// Services — 22 rows expected.
LOAD CSV WITH HEADERS FROM 'file:///services.csv' AS row
MERGE (s:Service {service_id: row.`Service ID`})
SET s.service_name       = row.`Service Name`,
    s.service_category   = row.`Service Category`,
    s.description         = row.Description,
    s.applies_to_category = row.`Applies To Machine Category`,
    s.applies_to_model    = row.`Applies To Machine Model`,
    s.customer_site       = row.`Customer Site`,
    s.dealer_workshop     = row.`Dealer Workshop`,
    s.other_location      = row.`Other Location`,
    s.dealer_delivered    = row.`Dealer Delivered`,
    s.external_authorised_provider = row.`External Authorised Provider`,
    s.related_parts       = row.`Related Parts`,
    s.related_machine_data = row.`Related Machine Data`,
    s.official_or_derived = row.`Official / Derived`,
    s.source_id           = row.`Source ID`,
    s.source_date         = row.`Source Date`;
