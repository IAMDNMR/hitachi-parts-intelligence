"""
backend/app/modules/dealer/service.py

Read-only queries over the 182 source-derived HCME Europe DealerBranch nodes
(SRC-049 dealer locator). Every row carries its source_id/confidence so the
caller can state provenance.
"""

import re
from typing import Any, Dict, List, Optional

# The dealer-locator feed lists account managers (people) next to dealer branches and has no type field; they are recognisable by their
# address text ("Accountmanager voor ..."). They are not dealers, so dealer answers leave them out.
NOT_ACCOUNT_MANAGER = "NOT (coalesce(d.address, '') =~ '(?i)\\s*account\\s?manager.*')"

_DEALER_FIELDS = """
    d.dealer_id AS dealer_id, d.dealer_name AS dealer_name, d.address AS address,
    d.city AS city, d.country AS country, d.phone AS phone, d.email AS email,
    d.website AS website, d.latitude AS latitude, d.longitude AS longitude,
    d.product_categories AS product_categories, d.source_id AS source_id,
    d.confidence AS confidence
"""


def list_dealers(session, country: Optional[str] = None, city: Optional[str] = None) -> List[Dict[str, Any]]:
    """Dealers filtered by ISO country code and/or city (case-insensitive)."""
    return session.run(
        f"""
        MATCH (d:DealerBranch)
        WHERE ($country IS NULL OR d.country = toUpper($country))
          AND ($city IS NULL OR toLower(d.city) = toLower($city))
          AND {NOT_ACCOUNT_MANAGER}
        RETURN {_DEALER_FIELDS}
        ORDER BY d.country, d.city, d.dealer_name
        """,
        country=country,
        city=city,
    ).data()


def nearest_dealers(session, lat: float, lon: float, country: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Dealers ranked by great-circle distance (km) from a point. Dealers
    without coordinates are excluded (they cannot be ranked honestly)."""
    return session.run(
        f"""
        MATCH (d:DealerBranch)
        WHERE d.latitude IS NOT NULL AND d.longitude IS NOT NULL
          AND ($country IS NULL OR d.country = toUpper($country))
          AND {NOT_ACCOUNT_MANAGER}
        WITH d, point.distance(point({{latitude: d.latitude, longitude: d.longitude}}),
                               point({{latitude: $lat, longitude: $lon}})) / 1000.0 AS km
        RETURN {_DEALER_FIELDS}, round(km, 1) AS distance_km
        ORDER BY km ASC LIMIT $limit
        """,
        lat=lat, lon=lon, country=country, limit=limit,
    ).data()


def find_dealers_by_name(session, name: str, limit: int = 5) -> List[Dict[str, Any]]:
    return session.run(
        f"""
        MATCH (d:DealerBranch) WHERE toLower(d.dealer_name) CONTAINS toLower($name)
        RETURN {_DEALER_FIELDS} ORDER BY d.country, d.dealer_name LIMIT $limit
        """,
        name=name, limit=limit,
    ).data()


# Machine.machine_category -> the dealer-locator product-category slugs that
# cover it. This is a join key between two source vocabularies, not data.
_CATEGORY_SLUGS = {
    "Excavators": ["mini-excavator", "middle-excavator", "large-excavator", "wheeled-excavator"],
    "Wheel Loaders": ["wheel-loader", "compact-wheel-loader"],
    "Rigid Dump Trucks": ["rigid-hauler"],
}


def dealers_for_machine_categories(session, categories: List[str], country: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Dealers whose published product categories cover any of the given
    machine categories (DERIVED relationship — no part-level dealer data)."""
    slugs = sorted({s for c in categories for s in _CATEGORY_SLUGS.get(c, [])})
    if not slugs:
        return []
    return session.run(
        f"""
        MATCH (d:DealerBranch)
        WHERE ($country IS NULL OR d.country = toUpper($country)) AND {NOT_ACCOUNT_MANAGER}
          AND any(s IN $slugs WHERE any(pc IN d.product_categories WHERE pc CONTAINS s))
        RETURN {_DEALER_FIELDS} ORDER BY d.country, d.dealer_name LIMIT $limit
        """,
        slugs=slugs, country=country, limit=limit,
    ).data()


_SUPPLIER_FIELDS = """
    s.supplier_number AS supplier_number, coalesce(s.display_name, s.name) AS name, s.city AS city,
    s.country AS country, s.country_name AS country_name, s.region AS region,
    s.possible_duplicate_of AS possible_duplicate_of, s.data_source AS data_source
"""


def find_suppliers(session, number: Optional[str] = None, name: Optional[str] = None, city: Optional[str] = None,
                   country: Optional[str] = None, limit: int = 30) -> Dict[str, Any]:
    """HCME SAP supplier master lookup (real data; the file has no part links)."""
    where = " AND ".join([
        "s.data_source = 'HCME_SAP_SUPPLIER_MASTER'",
        "($number IS NULL OR s.supplier_number = $number OR s.supplier_number ENDS WITH $number)",
        "($name IS NULL OR toLower(coalesce(s.display_name, s.name)) CONTAINS toLower($name))",
        "($city IS NULL OR toLower(s.city) = toLower($city))",
        "($country IS NULL OR s.country = toUpper($country))",
    ])
    params = {"number": number, "name": name, "city": city, "country": country}
    total = session.run(f"MATCH (s:Supplier) WHERE {where} RETURN count(s) AS n", **params).single()["n"]
    rows = session.run(f"MATCH (s:Supplier) WHERE {where} RETURN {_SUPPLIER_FIELDS} "
                       "ORDER BY s.country, s.city, name LIMIT $limit", limit=limit, **params).data()
    return {"total": total, "suppliers": rows}


def co_located(session, dealer_name: Optional[str] = None, city: Optional[str] = None, limit: int = 30) -> Dict[str, Any]:
    """Suppliers, dealers and the depot that share a City node."""
    row = None
    if dealer_name:
        is_depot = "depot" in dealer_name.lower()
        cleaned_target = re.sub(r"\b(the|depot|dealer|branch)\b", "", dealer_name, flags=re.I).strip()
        if is_depot or not cleaned_target:
            row = session.run(
                "MATCH (d:Depot)-[:LOCATED_IN]->(c:City) "
                "WHERE toLower(d.name) CONTAINS toLower($n) OR toLower(c.name) CONTAINS toLower($n) "
                "RETURN c.city_id AS id, c.name AS city, c.country AS country, d.name AS anchor, true AS is_depot LIMIT 1",
                n=cleaned_target or "oosterhout").single()
        if not row and cleaned_target:
            row = session.run(
                "MATCH (d:DealerBranch)-[:LOCATED_IN]->(c:City) WHERE toLower(d.dealer_name) CONTAINS toLower($n) "
                "RETURN c.city_id AS id, c.name AS city, c.country AS country, d.dealer_name AS anchor, false AS is_depot LIMIT 1",
                n=cleaned_target).single()
        if not row and cleaned_target:
            row = session.run(
                "MATCH (d:Depot)-[:LOCATED_IN]->(c:City) WHERE toLower(d.name) CONTAINS toLower($n) OR toLower(c.name) CONTAINS toLower($n) "
                "RETURN c.city_id AS id, c.name AS city, c.country AS country, d.name AS anchor, true AS is_depot LIMIT 1",
                n=cleaned_target).single()
    if not row and city:
        row = session.run(
            "MATCH (c:City) WHERE toLower(c.name) = toLower($c) RETURN c.city_id AS id, c.name AS city, "
            "c.country AS country, null AS anchor, false AS is_depot ORDER BY c.country = 'NL' DESC LIMIT 1", c=city).single()
    if not row:
        return {"city": None}
    sups = session.run(f"MATCH (c:City {{city_id: $id}})<-[:LOCATED_IN]-(s:Supplier) "
                       f"WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' "
                       f"RETURN {_SUPPLIER_FIELDS} ORDER BY name LIMIT $limit", id=row["id"], limit=limit).data()
    dealers = session.run(f"MATCH (c:City {{city_id: $id}})<-[:LOCATED_IN]-(d:DealerBranch) WHERE {NOT_ACCOUNT_MANAGER} RETURN {_DEALER_FIELDS}",
                          id=row["id"]).data()
    depots = session.run("MATCH (c:City {city_id: $id})<-[:LOCATED_IN]-(d:Depot) RETURN d.name AS name", id=row["id"]).value()
    total = session.run("MATCH (c:City {city_id: $id})<-[:LOCATED_IN]-(s:Supplier) "
                        "WHERE s.data_source = 'HCME_SAP_SUPPLIER_MASTER' RETURN count(s) AS n",
                        id=row["id"]).single()["n"]
    return {"city": row["city"], "country": row["country"], "anchor_dealer": row["anchor"],
            "anchor_is_depot": row["is_depot"],
            "supplier_total": total, "suppliers": sups, "dealers": dealers, "depots": depots}
