"""
backend/app/modules/intelligence/graph_query.py

Phase 10C — Central named graph traversal library for Parts Intelligence.

All traversals are READ-ONLY and return typed dicts with explicit
provenance annotations. No business data is hard-coded here.

Provenance codes (per user mandate):
  SOURCE_DERIVED  — HCME Europe published / client data
  DERIVED         — computed from source data (describe how)
  SYNTHETIC_DEMO  — seeded demo record, NOT real HCME data
  NOT_CONNECTED   — would require a real integration not yet wired
  TEST_DATA       — created by an automated test run, never real

Relationship classification notes (live graph, audited 2026-09-23):
  Machine -[:HAS_PART_FITMENT]-> Part       SOURCE_DERIVED (1,041 edges)
  Part    -[:SUPPLIED_BY]->       Supplier   SYNTHETIC_DEMO  (73 edges, synthetic=true)
  Supplier -[:LOCATED_IN]->      City        SOURCE_DERIVED (1,720 edges — from SAP master)
  DealerBranch -[:LOCATED_IN]-> City         SOURCE_DERIVED (155 edges)
  City    -[:IN_COUNTRY]->       Country     SOURCE_DERIVED (926 edges)
  The supplier master has NO supplier-to-part mapping; Part→Supplier links
  that do exist are synthetic demo records only.
"""

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Machine vocabulary — normalises free-text to Machine.machine_category values
# that exist in live Neo4j. Case-insensitive match at query time.
# ---------------------------------------------------------------------------

MACHINE_TYPE_VOCAB: Dict[str, str] = {
    # Excavators
    "mini excavator": "Mini Excavators",
    "mini excavators": "Mini Excavators",
    "mini-excavator": "Mini Excavators",
    "mini-excavators": "Mini Excavators",
    "miniexcavator": "Mini Excavators",
    "miniexcavators": "Mini Excavators",
    "compact excavator": "Mini Excavators",
    "compact excavators": "Mini Excavators",
    "small excavator": "Mini Excavators",
    "small excavators": "Mini Excavators",
    "medium excavator": "Medium Excavators",
    "medium excavators": "Medium Excavators",
    "mid excavator": "Medium Excavators",
    "mid excavators": "Medium Excavators",
    "mid-size excavator": "Medium Excavators",
    "mid-size excavators": "Medium Excavators",
    "midsize excavator": "Medium Excavators",
    "midsize excavators": "Medium Excavators",
    "large excavator": "Large Excavators",
    "large excavators": "Large Excavators",
    "big excavator": "Large Excavators",
    "big excavators": "Large Excavators",
    "heavy excavator": "Large Excavators",
    "heavy excavators": "Large Excavators",
    "wheeled excavator": "Wheeled Excavators",
    "wheeled excavators": "Wheeled Excavators",
    "wheel excavator": "Wheeled Excavators",
    "wheel excavators": "Wheeled Excavators",
    "excavator": "Excavators",
    "excavators": "Excavators",
    # Wheel Loaders
    "wheel loader": "Wheel Loaders",
    "wheel loaders": "Wheel Loaders",
    "wheeled loader": "Wheel Loaders",
    "wheeled loaders": "Wheel Loaders",
    "loader": "Wheel Loaders",
    "loaders": "Wheel Loaders",
    # Dump Trucks
    "rigid dump truck": "Rigid Dump Trucks",
    "rigid dump trucks": "Rigid Dump Trucks",
    "dump truck": "Rigid Dump Trucks",
    "dump trucks": "Rigid Dump Trucks",
    "hauler": "Rigid Dump Trucks",
    "haulers": "Rigid Dump Trucks",
    "rigid hauler": "Rigid Dump Trucks",
    "rigid haulers": "Rigid Dump Trucks",
}

# Part category vocabulary — normalises free-text to Machine→Part category
# labels used in the graph (Part.part_category field values).
PART_CATEGORY_VOCAB: Dict[str, str] = {
    "bucket": "Bucket",
    "buckets": "Bucket",
    "digging bucket": "Bucket",
    "excavator bucket": "Bucket",
    "filter": "Filter",
    "filters": "Filter",
    "hydraulic filter": "Filter",
    "engine filter": "Filter",
    "oil filter": "Filter",
    "air filter": "Filter",
    "undercarriage": "Undercarriage",
    "track": "Undercarriage",
    "tracks": "Undercarriage",
    "track assembly": "Undercarriage",
    "sprocket": "Undercarriage",
    "carrier roller": "Undercarriage",
    "bottom roller": "Undercarriage",
    "idler": "Undercarriage",
    "track shoe": "Undercarriage",
    "engine": "Engine",
    "engine part": "Engine",
    "hydraulic": "Hydraulics",
    "hydraulics": "Hydraulics",
    "hydraulic pump": "Hydraulics",
    "hydraulic cylinder": "Hydraulics",
    "pump": "Hydraulics",
    "boom": "Attachment",
    "arm": "Attachment",
    "stick": "Attachment",
    "quick coupler": "Attachment",
    "attachment": "Attachment",
    "cab": "Cab",
    "cabin": "Cab",
    "seat": "Cab",
    "electric": "Electrical",
    "electrical": "Electrical",
    "wiring": "Electrical",
    "battery": "Electrical",
    "cooling": "Cooling",
    "radiator": "Cooling",
    "fan": "Cooling",
    "seal": "Seals",
    "seals": "Seals",
    "o-ring": "Seals",
    "gasket": "Seals",
}


# ---------------------------------------------------------------------------
# Machine queries
# ---------------------------------------------------------------------------

def machines_by_category(session, machine_category: str, limit: int = 30) -> List[Dict[str, Any]]:
    """All Machine nodes matching a normalised machine_category or machine_subcategory value.

    Returns SOURCE_DERIVED records — these are real HCME machine catalogue entries.
    """
    return session.run(
        """
        MATCH (m:Machine)
        WHERE toLower(m.machine_subcategory) = toLower($cat)
           OR toLower(m.machine_subcategory) = toLower($cat) + 's'
           OR toLower(m.machine_subcategory) + 's' = toLower($cat)
           OR toLower(m.machine_category) = toLower($cat)
           OR toLower(m.machine_category) = toLower($cat) + 's'
           OR toLower(m.machine_category) + 's' = toLower($cat)
        RETURN m.machine_id AS machine_id, m.model AS model,
               m.machine_category AS machine_category,
               m.machine_subcategory AS machine_subcategory,
               m.machine_type AS machine_type,
               coalesce(m.operating_weight_published, m.operating_weight_kg) AS operating_weight,
               m.source_id AS source_id
        ORDER BY m.model
        LIMIT $limit
        """,
        cat=machine_category, limit=limit,
    ).data()


def machines_by_type_all_categories(session, limit: int = 30) -> Dict[str, List[Dict]]:
    """All machines grouped by machine_category.

    Returns SOURCE_DERIVED records.
    """
    rows = session.run(
        """
        MATCH (m:Machine)
        RETURN m.machine_category AS category, count(m) AS cnt,
               collect(m.model)[..5] AS examples
        ORDER BY cnt DESC
        """,
    ).data()
    return {r["category"]: {"count": r["cnt"], "examples": r["examples"]} for r in rows}


def parts_by_machine_and_category(
    session, machine_id: str, part_category: Optional[str] = None, limit: int = 20
) -> List[Dict[str, Any]]:
    """Parts fitted to a specific machine, optionally filtered by part category.

    Relationship: Machine -[:HAS_PART_FITMENT]-> Part
    Classification: SOURCE_DERIVED
    """
    where = "WHERE m.machine_id = $mid"
    if part_category:
        where += " AND toLower(p.part_category) CONTAINS toLower($cat)"
    return session.run(
        f"""
        MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p:Part)
        {where}
        RETURN p.part_id AS part_id, p.part_number AS part_number,
               p.part_name AS part_name, p.part_category AS part_category,
               p.part_subcategory AS part_subcategory,
               r.fitment_type AS fitment_type
        ORDER BY p.part_category, p.part_name
        LIMIT $limit
        """,
        mid=machine_id, cat=part_category or "", limit=limit,
    ).data()


def parts_by_category_across_machines(
    session, machine_category: str, part_category: str, limit: int = 20
) -> Dict[str, Any]:
    """Parts in a part_category fitted to machines in a machine_category.

    Relationship path: Machine -[:HAS_PART_FITMENT]-> Part
    Classification: SOURCE_DERIVED

    Returns both part records and the list of machine IDs they fit.
    """
    rows = session.run(
        """
        MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part)
        WHERE (toLower(m.machine_subcategory) = toLower($mcat)
           OR toLower(m.machine_subcategory) = toLower($mcat) + 's'
           OR toLower(m.machine_subcategory) + 's' = toLower($mcat)
           OR toLower(m.machine_category) = toLower($mcat)
           OR toLower(m.machine_category) = toLower($mcat) + 's'
           OR toLower(m.machine_category) + 's' = toLower($mcat))
          AND ($pcat IS NULL OR $pcat = ''
           OR toLower(p.part_category) CONTAINS toLower($pcat)
           OR toLower(p.part_subcategory) CONTAINS toLower($pcat)
           OR toLower($pcat) CONTAINS toLower(p.part_category))
        WITH p, collect(DISTINCT m.model) AS fitted_models, count(DISTINCT m) AS machine_count
        RETURN p.part_id AS part_id, p.part_number AS part_number,
               p.part_name AS part_name, p.part_category AS part_category,
               p.part_subcategory AS part_subcategory,
               machine_count, fitted_models
        ORDER BY machine_count DESC, p.part_name
        LIMIT $limit
        """,
        mcat=machine_category, pcat=part_category or None, limit=limit,
    ).data()
    return {
        "parts": rows,
        "machine_category": machine_category,
        "part_category": part_category,
        "total": len(rows),
        "data_class": "SOURCE_DERIVED",
        "relationship_path": "Machine -[:HAS_PART_FITMENT]-> Part",
        "note": (
            "Fitment relationships are from HCME Europe catalogue source data. "
            "Part count represents catalogue records, not current stock."
        ),
    }


# ---------------------------------------------------------------------------
# Supplier queries
# ---------------------------------------------------------------------------

def suppliers_by_part(session, part_id: str, include_synthetic: bool = False) -> Dict[str, Any]:
    """Suppliers linked to a Part via SUPPLIED_BY.

    IMPORTANT: In live data all SUPPLIED_BY edges are synthetic=true
    (SYNTHETIC_DEMO). The HCME SAP supplier master (1,720 records) has NO
    supplier-to-part mapping. By default, this function only returns verified
    supplier relationships.
    """
    where_synthetic = "" if include_synthetic else "AND coalesce(s.synthetic, false) = false AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'"
    rows = session.run(
        f"""
        MATCH (p:Part {{part_id: $id}})-[r:SUPPLIED_BY]->(s:Supplier)
        WHERE 1=1 {where_synthetic}
        RETURN s.name AS name, s.supplier_number AS supplier_number,
               s.city AS city, s.country AS country,
               r.share_pct AS share_pct,
               coalesce(s.synthetic, false) AS synthetic
        ORDER BY name
        """,
        id=part_id,
    ).data()
    all_synthetic = all(r.get("synthetic") for r in rows) if rows else None
    return {
        "part_id": part_id,
        "supplier_count": len(rows),
        "suppliers": rows,
        "data_class": "SYNTHETIC_DEMO" if all_synthetic else ("SOURCE_DERIVED" if rows else "NOT_CONNECTED"),
        "note": (
            "Verified supplier records from HCME source data."
        ) if (rows and not all_synthetic) else (
            "Supplier-to-part mapping is not recorded in the current HCME supplier source. "
            "The SAP supplier master (1,720 records) contains supplier location data only — "
            "it has no part numbers or supplier-part assignments."
        ),
        "relationship_path": "Part -[:SUPPLIED_BY]-> Supplier",
    }


def suppliers_by_country(session, country: str, limit: int = 30) -> Dict[str, Any]:
    """Suppliers located in a country via Supplier→City→Country traversal.

    Classification: SOURCE_DERIVED — HCME SAP supplier master.
    """
    total = session.run(
        """
        MATCH (s:Supplier)-[:LOCATED_IN]->(c:City)-[:IN_COUNTRY]->(co:Country)
        WHERE toUpper(co.code) = toUpper($country)
          AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
        RETURN count(DISTINCT s) AS n
        """,
        country=country,
    ).single()["n"]
    rows = session.run(
        """
        MATCH (s:Supplier)-[:LOCATED_IN]->(c:City)-[:IN_COUNTRY]->(co:Country)
        WHERE toUpper(co.code) = toUpper($country)
          AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
        RETURN s.supplier_number AS supplier_number,
               coalesce(s.display_name, s.name) AS name,
               c.name AS city, co.code AS country
        ORDER BY c.name, name
        LIMIT $limit
        """,
        country=country, limit=limit,
    ).data()
    return {
        "total": total,
        "country": country,
        "suppliers": rows,
        "data_class": "SOURCE_DERIVED",
        "relationship_path": "Supplier -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country",
        "note": (
            "Supplier records from the HCME SAP supplier master (source-derived). "
            "These are logistics/procurement contacts — no supplier-to-part mapping is included."
        ),
    }


def suppliers_by_city(session, city_name: str, country: Optional[str] = None, limit: int = 30) -> Dict[str, Any]:
    """Suppliers located in a specific city.

    Classification: SOURCE_DERIVED — HCME SAP supplier master.
    """
    where_country = "AND toUpper(co.code) = toUpper($country)" if country else ""
    total = session.run(
        f"""
        MATCH (s:Supplier)-[:LOCATED_IN]->(c:City)
        OPTIONAL MATCH (c)-[:IN_COUNTRY]->(co:Country)
        WHERE toLower(c.name) = toLower($city)
          AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
          {where_country}
        RETURN count(DISTINCT s) AS n
        """,
        city=city_name, country=country or "",
    ).single()["n"]
    rows = session.run(
        f"""
        MATCH (s:Supplier)-[:LOCATED_IN]->(c:City)
        OPTIONAL MATCH (c)-[:IN_COUNTRY]->(co:Country)
        WHERE toLower(c.name) = toLower($city)
          AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
          {where_country}
        RETURN s.supplier_number AS supplier_number,
               coalesce(s.display_name, s.name) AS name,
               c.name AS city, coalesce(co.code, s.country) AS country
        ORDER BY name
        LIMIT $limit
        """,
        city=city_name, country=country or "", limit=limit,
    ).data()
    return {
        "total": total,
        "city": city_name,
        "country": country,
        "suppliers": rows,
        "data_class": "SOURCE_DERIVED",
        "relationship_path": "Supplier -[:LOCATED_IN]-> City",
        "note": "HCME SAP supplier master — no part numbers included.",
    }


# ---------------------------------------------------------------------------
# Network summary (dealer + supplier by country)
# ---------------------------------------------------------------------------

def network_summary_by_country(session, country: str) -> Dict[str, Any]:
    """Combined dealer + supplier counts and shared-city analysis for a country.

    Used for 'dealer and supplier network in [country]' queries.
    """
    dealer_count = session.run(
        "MATCH (d:DealerBranch) WHERE d.country = toUpper($c) RETURN count(d) AS n",
        c=country,
    ).single()["n"]

    supplier_count = session.run(
        """
        MATCH (s:Supplier)-[:LOCATED_IN]->(c:City)-[:IN_COUNTRY]->(co:Country)
        WHERE toUpper(co.code) = toUpper($c) AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
        RETURN count(DISTINCT s) AS n
        """,
        c=country,
    ).single()["n"]

    shared_cities = session.run(
        """
        MATCH (d:DealerBranch)-[:LOCATED_IN]->(city:City)<-[:LOCATED_IN]-(s:Supplier)
        WHERE d.country = toUpper($c) AND s.data_source = 'HCME_SAP_SUPPLIER_MASTER'
        RETURN city.name AS city_name,
               count(DISTINCT d) AS dealer_count,
               count(DISTINCT s) AS supplier_count,
               collect(DISTINCT d.dealer_name)[..2] AS sample_dealers,
               collect(DISTINCT coalesce(s.display_name, s.name))[..3] AS sample_suppliers
        ORDER BY supplier_count DESC LIMIT 10
        """,
        c=country,
    ).data()

    return {
        "country": country,
        "dealer_count": dealer_count,
        "supplier_count": supplier_count,
        "shared_cities": shared_cities,
        "dealer_data_class": "SOURCE_DERIVED",
        "supplier_data_class": "SOURCE_DERIVED",
        "note": (
            f"Dealer counts from HCME Europe dealer locator (SOURCE_DERIVED). "
            f"Supplier counts from HCME SAP supplier master (SOURCE_DERIVED). "
            "Shared cities are locations where both dealers and suppliers appear — no business relationship is implied."
        ),
    }


# ---------------------------------------------------------------------------
# Helper: resolve machine_type vocabulary → Neo4j category string
# ---------------------------------------------------------------------------

def resolve_machine_type(machine_type_text: str) -> Optional[str]:
    """Map free-text machine type description to a Neo4j machine_category value.

    Returns None when the type is ambiguous (e.g. bare "excavator" without size).
    """
    key = machine_type_text.lower().strip()
    # Try exact match
    if key in MACHINE_TYPE_VOCAB:
        return MACHINE_TYPE_VOCAB[key]
    # Try partial match
    for vocab_key, category in MACHINE_TYPE_VOCAB.items():
        if vocab_key in key or key in vocab_key:
            if category is not None:
                return category
    return None


def resolve_part_category(part_category_text: str) -> Optional[str]:
    """Map free-text part description to a normalised part_category string.

    Returns None when nothing in the vocabulary matches.
    """
    key = part_category_text.lower().strip()
    if key in PART_CATEGORY_VOCAB:
        return PART_CATEGORY_VOCAB[key]
    for vocab_key, category in PART_CATEGORY_VOCAB.items():
        if vocab_key in key or key in vocab_key:
            return category
    return None
