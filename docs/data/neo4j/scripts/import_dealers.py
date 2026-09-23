#!/usr/bin/env python3
"""Idempotent import of docs/data/neo4j/data/dealers.csv (182 real HCME Europe
DealerBranch rows, SRC-049) into the live AuraDB graph via the Python driver
(mirrors docs/data/neo4j/import/nodes/dealers.cypher field-for-field, since
Aura does not support LOAD CSV FROM 'file:///')."""
import csv
import os
import sys

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = r"C:\Users\iamdn\OneDrive\Desktop\Parts&Service"
load_dotenv(os.path.join(ROOT, "backend", ".env"))
URI = os.environ["NEO4J_URI"]
USER = os.environ["NEO4J_USER"]
PW = os.environ["NEO4J_PASSWORD"]
DB = os.environ.get("NEO4J_DATABASE")

CSV_PATH = os.path.join(ROOT, "docs", "data", "neo4j", "data", "dealers.csv")

CYPHER = """
MERGE (d:DealerBranch {dealer_id: $dealer_id})
SET d.dealer_name        = $dealer_name,
    d.address             = $address,
    d.city                = $city,
    d.country             = $country,
    d.state_province      = $state_province,
    d.sub_region          = $sub_region,
    d.phone               = $phone,
    d.email               = $email,
    d.website             = $website,
    d.product_categories  = $product_categories,
    d.latitude            = toFloat($latitude),
    d.longitude           = toFloat($longitude),
    d.enquiry_link        = $enquiry_link,
    d.region              = $region,
    d.record_class        = $record_class,
    d.data_class           = $data_class,
    d.source_id           = $source_id,
    d.confidence          = $confidence,
    d.source_date         = $source_date
"""

def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PW))
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "dealer_id": row["Dealer ID"],
                "dealer_name": row["Dealer Name"],
                "address": row["Address"],
                "city": row["City"],
                "country": row["Country"],
                "state_province": row["State/Province"],
                "sub_region": row["Sub Region"],
                "phone": row["Phone"],
                "email": row["Email"],
                "website": row["Website"],
                "product_categories": row["Product Categories"],
                "latitude": row["Latitude"] or None,
                "longitude": row["Longitude"] or None,
                "enquiry_link": row["Enquiry Link"],
                "region": row["Region"],
                "record_class": row["record_class"],
                "data_class": row["Data Class"],
                "source_id": row["Source ID"],
                "confidence": row["Confidence"],
                "source_date": row["Source Date"],
            })
    print(f"Read {len(rows)} rows from dealers.csv")
    with driver.session(database=DB) as s:
        s.run("CREATE CONSTRAINT DealerBranch_dealer_id IF NOT EXISTS FOR (n:DealerBranch) REQUIRE n.dealer_id IS UNIQUE").consume()
        for r in rows:
            s.run(CYPHER, r).consume()
        cnt = s.run("MATCH (n:DealerBranch) RETURN count(n) AS c").single()["c"]
        print(f"DealerBranch count after import: {cnt}")
    driver.close()

if __name__ == "__main__":
    sys.exit(main())
