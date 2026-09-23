#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import HCME's supplier master (SAP S/4HANA migration template, sheet
"General Data") into Neo4j: supplier number, name, city and country only.

    python docs/data/neo4j/scripts/import_sap_suppliers.py "C:/.../20260609_Source data for Supplier.xlsx"            # dry run
    python docs/data/neo4j/scripts/import_sap_suppliers.py "C:/.../20260609_Source data for Supplier.xlsx" --execute

Graph written (all data_source='HCME_SAP_SUPPLIER_MASTER', synthetic=false):
  (:Supplier {supplier_number})-[:LOCATED_IN]->(:City)-[:IN_COUNTRY]->(:Country)
and the existing real DealerBranch / Depot nodes are linked to the same
City/Country nodes, so suppliers, dealers and the depot connect by location.

Corrections applied (the raw value is always kept alongside):
  - city: trimmed, ALL-CAPS/lower-case converted to title case (Dutch 'IJ' kept),
    known Dutch variants unified ('s-Hertogenbosch, Den Haag).
  - name: kept exactly; SAP 'Name 2' kept as name_line_2; display_name joins
    them only where Name 1 was cut at the 40-character field limit.
  - same name under different supplier numbers: kept (distinct SAP accounts),
    flagged with possible_duplicate_of.
The file has no part numbers, so NO Part-[:SUPPLIED_BY]->Supplier link is
created from it.
"""
import argparse
import collections
import io
import os
import re
import sys
from pathlib import Path

import openpyxl
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[4]
load_dotenv(ROOT / "backend" / ".env")

# Column positions in "General Data" (row 5 holds the SAP field names).
FIELDS = {"LIFNR": "supplier_number", "NAME_FIRST": "name", "NAME_LAST": "name_line_2", "CITY1": "city", "COUNTRY": "country"}
FIRST_DATA_ROW = 8  # 0-based: rows 0-7 are template headers

CITY_VARIANTS = {  # lower-case raw -> official spelling
    "' s-hertogenbosch": "'s-Hertogenbosch", "'s-hertogenbosch": "'s-Hertogenbosch", "s hertogenbosch": "'s-Hertogenbosch",
    "s-hertogenbosch": "'s-Hertogenbosch", "den bosch": "'s-Hertogenbosch", "s-gravenhage": "Den Haag",
    "'s-gravenhage": "Den Haag", "den haag": "Den Haag", "'s-heerenberg": "'s-Heerenberg",
}
COUNTRY_NAMES = {
    "NL": "Netherlands", "DE": "Germany", "FR": "France", "GB": "United Kingdom", "IT": "Italy", "BE": "Belgium",
    "US": "United States", "CH": "Switzerland", "JP": "Japan", "ES": "Spain", "SE": "Sweden", "NO": "Norway",
    "IE": "Ireland", "PL": "Poland", "DK": "Denmark", "PT": "Portugal", "ZA": "South Africa", "KR": "South Korea",
    "FI": "Finland", "MR": "Mauritania", "CA": "Canada", "MA": "Morocco", "CZ": "Czechia", "AT": "Austria",
    "CN": "China", "HU": "Hungary", "TR": "Türkiye", "AU": "Australia", "GH": "Ghana", "UA": "Ukraine",
    "IL": "Israel", "IN": "India", "LU": "Luxembourg", "GR": "Greece", "LT": "Lithuania", "RO": "Romania",
    "HK": "Hong Kong", "IS": "Iceland", "EE": "Estonia", "RS": "Serbia", "LV": "Latvia", "HR": "Croatia",
    "BG": "Bulgaria", "CY": "Cyprus", "BY": "Belarus", "SI": "Slovenia", "SK": "Slovakia", "SG": "Singapore",
    "BA": "Bosnia and Herzegovina", "MK": "North Macedonia", "CI": "Côte d'Ivoire", "KZ": "Kazakhstan", "ML": "Mali",
    "MQ": "Martinique", "MU": "Mauritius", "SA": "Saudi Arabia", "SC": "Seychelles", "ZM": "Zambia",
    "AE": "United Arab Emirates", "TW": "Taiwan", "TH": "Thailand", "BR": "Brazil", "MX": "Mexico", "NZ": "New Zealand",
}
EUROPE = {"NL", "DE", "FR", "GB", "IT", "BE", "CH", "ES", "SE", "NO", "IE", "PL", "DK", "PT", "FI", "CZ", "AT", "HU",
          "UA", "LU", "GR", "LT", "RO", "IS", "EE", "RS", "LV", "HR", "BG", "CY", "BY", "SI", "SK", "TR", "BA", "MK"}


def clean_city(raw: str) -> str:
    c = re.sub(r"\s+", " ", raw.strip())
    if c.lower() in CITY_VARIANTS:
        return CITY_VARIANTS[c.lower()]
    if c.isupper() or c.islower():
        c = " ".join(w[:2].upper() + w[2:] if w.lower().startswith("ij") else w.capitalize() for w in c.lower().split(" "))
        c = re.sub(r"-(\w)", lambda m: "-" + m.group(1).upper(), c)
    return c


def display_name(name: str, line2: str | None) -> str:
    # Name 1 reached SAP's 40-char limit region and Name 2 is text, not a payment code.
    if line2 and len(name) >= 33 and ":" not in name and not re.fullmatch(r"[\d\s]+", line2):
        return f"{name} {line2}".strip()
    return name


def read(path: str):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb["General Data"].iter_rows(values_only=True))
    col = {tech: i for i, tech in enumerate(rows[4]) if tech in FIELDS}
    out = []
    for r in rows[FIRST_DATA_ROW:]:
        if not r or not r[col["LIFNR"]]:
            continue
        rec = {FIELDS[t]: (str(r[i]).strip() if r[i] is not None else None) for t, i in col.items()}
        rec["city_raw"] = rec["city"]
        rec["city"] = clean_city(rec["city"]) if rec["city"] else None
        rec["country"] = (rec["country"] or "").upper() or None
        rec["country_name"] = COUNTRY_NAMES.get(rec["country"], rec["country"])
        rec["region"] = "Europe" if rec["country"] in EUROPE else "Rest of world"
        rec["display_name"] = display_name(rec["name"], rec["name_line_2"])
        out.append(rec)
    by_name = collections.defaultdict(list)
    for rec in out:
        by_name[rec["name"].strip().lower()].append(rec["supplier_number"])
    for rec in out:
        others = [n for n in by_name[rec["name"].strip().lower()] if n != rec["supplier_number"]]
        rec["possible_duplicate_of"] = others or None
    return out


WRITE = """
UNWIND $rows AS r
MERGE (co:Country {code: r.country})
  ON CREATE SET co.name = r.country_name
MERGE (ci:City {city_id: r.country + '|' + toLower(r.city)})
  ON CREATE SET ci.name = r.city, ci.country = r.country
MERGE (ci)-[:IN_COUNTRY]->(co)
MERGE (s:Supplier {supplier_number: r.supplier_number})
SET s.supplier_id = r.supplier_number, s.name = r.name, s.name_line_2 = r.name_line_2,
    s.display_name = r.display_name, s.city = r.city, s.city_raw = r.city_raw,
    s.country = r.country, s.country_name = r.country_name, s.region = r.region,
    s.possible_duplicate_of = r.possible_duplicate_of,
    s.data_source = 'HCME_SAP_SUPPLIER_MASTER', s.data_class = 'CLIENT_PROVIDED',
    s.source_file = $source_file, s.synthetic = false, s.record_class = 'SUPPLIER_MASTER'
MERGE (s)-[l:LOCATED_IN]->(ci)
SET l.data_source = 'HCME_SAP_SUPPLIER_MASTER'
RETURN count(s) AS n
"""

# Existing real dealers and the depot join the same location graph.
LINK_EXISTING = """
MATCH (n) WHERE (n:DealerBranch OR n:Depot) AND n.country IS NOT NULL
MERGE (co:Country {code: n.country})
WITH n, co
CALL (n, co) {
  WITH n, co WHERE coalesce(n.city, '') <> ''
  MERGE (ci:City {city_id: n.country + '|' + toLower(n.city)})
    ON CREATE SET ci.name = n.city, ci.country = n.country
  MERGE (ci)-[:IN_COUNTRY]->(co)
  MERGE (n)-[:LOCATED_IN]->(ci)
}
RETURN count(n) AS n
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    rows = read(args.xlsx)
    fixed_city = sum(1 for r in rows if r["city"] != r["city_raw"])
    joined = sum(1 for r in rows if r["display_name"] != r["name"])
    dups = sum(1 for r in rows if r["possible_duplicate_of"])
    print(f"suppliers: {len(rows)} | countries: {len({r['country'] for r in rows})} | "
          f"cities (clean): {len({(r['country'], r['city']) for r in rows})} | city spelling fixed: {fixed_city} | "
          f"truncated names joined: {joined} | possible duplicate accounts: {dups} | "
          f"outside Europe: {sum(1 for r in rows if r['region'] != 'Europe')}")
    for r in [r for r in rows if r["city"] != r["city_raw"]][:6]:
        print(f"   city  {r['city_raw']!r} -> {r['city']!r}")
    for r in [r for r in rows if r["display_name"] != r["name"]][:4]:
        print(f"   name  {r['name']!r} + {r['name_line_2']!r}")
    if not args.execute:
        print("DRY RUN — re-run with --execute to write to Neo4j.")
        return

    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with driver.session(database=os.environ.get("NEO4J_DATABASE") or None) as s:
        for q in ("CREATE CONSTRAINT supplier_number_unique IF NOT EXISTS FOR (s:Supplier) REQUIRE s.supplier_number IS UNIQUE",
                  "CREATE CONSTRAINT city_id_unique IF NOT EXISTS FOR (c:City) REQUIRE c.city_id IS UNIQUE",
                  "CREATE CONSTRAINT country_code_unique IF NOT EXISTS FOR (c:Country) REQUIRE c.code IS UNIQUE"):
            s.run(q).consume()
        n = 0
        for i in range(0, len(rows), 400):
            n += s.run(WRITE, rows=rows[i:i + 400], source_file=Path(args.xlsx).name).single()["n"]
        linked = s.run(LINK_EXISTING).single()["n"]
    driver.close()
    print(f"APPLIED  {n} suppliers written; {linked} dealers/depot linked to City/Country")


if __name__ == "__main__":
    main()
