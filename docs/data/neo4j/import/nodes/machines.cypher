// Machines — 77 rows expected (one per catalogue/product page — approved
// decision: NOT 84, NOT 79. See MODEL_CODE_RECONCILIATION_REPORT.md).
// models_covered is stored as a list so both single-code and 2-code catalogue
// pages are represented without ever creating an extra Machine node.
LOAD CSV WITH HEADERS FROM 'file:///machines.csv' AS row
MERGE (m:Machine {machine_id: row.`Machine ID`})
SET m.manufacturer           = row.Manufacturer,
    m.brand                  = row.Brand,
    m.machine_category       = row.`Machine Category`,
    m.machine_subcategory    = row.`Machine Subcategory`,
    m.category_id            = row.`Category ID`,
    m.product_family         = row.`Product Family`,
    m.model                  = row.Model,
    m.models_covered         = split(row.`Models Covered`, ' | '),
    m.model_count            = toInteger(row.`Model Count`),
    m.generation_series       = row.`Generation / Series`,
    m.machine_type            = row.`Machine Type`,
    m.configuration           = row.Configuration,
    m.power_source            = row.`Power Source`,
    m.official_product_name   = row.`Official Product Name`,
    m.available_in            = row.`Available In`,
    m.engine_rated_power      = row.`Engine / Motor Rated Power`,
    m.operating_weight_published = row.`Operating Weight (as published)`,
    m.operating_weight_kg     = toFloat(row.`Operating Weight (kg, normalised)`),
    m.bucket_capacity_published = row.`Bucket Capacity (as published)`,
    m.battery_capacity        = row.`Battery Capacity`,
    m.nominal_payload         = row.`Nominal Payload`,
    m.max_digging_depth       = row.`Max. Digging Depth`,
    m.max_digging_reach       = row.`Max. Digging Reach`,
    m.overall_width           = row.`Overall Width`,
    m.overall_height_of_cab   = row.`Overall Height of Cab`,
    m.fuel_tank_capacity      = row.`Fuel Tank Capacity`,
    m.official_overview_text  = row.`Official Overview Text`,
    m.data_class              = row.`Data Class`,
    m.source_id               = row.`Source ID`,
    m.source_date             = row.`Source Date`;
// No Official Product URL / Brochure PDF imported — dropped in the cleaning
// phase per "no URL pollution in core business properties".
