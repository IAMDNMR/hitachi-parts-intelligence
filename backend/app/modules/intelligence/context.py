"""
backend/app/modules/intelligence/context.py

Read-only operational/commercial context retrieval for Parts Intelligence
(KPI scenarios 1-5, see
docs/research/HCME_EUROPE_OPERATIONAL_DATA_AND_KPI_FOUNDATION.md).

Rule enforced throughout this module, matching
backend/app/modules/intelligence/service.py: the LLM layer never touches
these functions and never generates any of the facts returned here. Every
value returned is read directly from Neo4j via parameterised Cypher. Every
record includes its `synthetic` flag and, for synthetic records,
`data_source = "SYNTHETIC_DEMO"` so a caller (API response, UI, or the LLM
explanation layer) can never present synthetic operational data as real HCME
live data. This module performs no writes.
"""

from typing import Any, Dict, List

from app.errors.exceptions import NotFoundError


def _part_or_404(session, part_id: str) -> Dict[str, Any]:
    row = session.run("MATCH (p:Part {part_id: $id}) RETURN p", {"id": part_id}).single()
    if not row:
        raise NotFoundError(f"Part '{part_id}' not found")
    return dict(row["p"])


def get_order_context(session, part_id: str) -> Dict[str, Any]:
    """KPI 1 / KPI 3 — Part -> FulfilmentRequest -> Allocation -> Order ->
    Shipment -> DealerBranch, fully graph-traversed. Only returns Order/
    Allocation/etc nodes actually linked to this Part via FOR_PART; never
    invents a status."""
    _part_or_404(session, part_id)
    rows = session.run(
        """
        MATCH (o:Order)-[:FOR_PART]->(p:Part {part_id: $id})
        OPTIONAL MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o)
        OPTIONAL MATCH (o)-[:BASED_ON_ALLOCATION]->(a:Allocation)
        OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
        OPTIONAL MATCH (sh)-[:SHIPPED_TO]->(dest:DealerBranch)
        RETURN o.id AS order_id, o.status AS order_status, o.quantity AS quantity,
               o.synthetic AS order_synthetic, o.data_source AS order_data_source,
               fr.id AS fulfilment_request_id, fr.status AS fulfilment_status,
               a.id AS allocation_id, a.status AS allocation_status, a.sourceId AS source_id,
               sh.shipment_id AS shipment_id, sh.status AS shipment_status,
               sh.carrier AS carrier, sh.tracking_number AS tracking_number,
               sh.eta AS eta, sh.shipped_at AS shipped_at, sh.delivered_at AS delivered_at,
               sh.synthetic AS shipment_synthetic,
               o.provenance AS order_provenance,
               dest.dealer_id AS dealer_id, dest.dealer_name AS dealer_name, dest.country AS dealer_country
        ORDER BY o.id
        """,
        {"id": part_id},
    ).data()
    return {
        "part_id": part_id,
        "orders": rows,
        "note": (
            "All rows are graph-confirmed traversals (FOR_PART / HAS_ORDER / "
            "BASED_ON_ALLOCATION / HAS_SHIPMENT / SHIPPED_TO). Any row with "
            "order_synthetic=true is SYNTHETIC DEMO DATA, not a real HCME order. "
            "Any other row is NOT real HCME production data either: order_provenance "
            "will read 'INTERNAL_TEST_WORKFLOW' (the app's order-creation code path "
            "has no real-transaction mode in this prototype) — such a row must never "
            "be presented as a genuine customer order."
        ),
    }


def get_order_status(session, order_id: str) -> Dict[str, Any]:
    """KPI 3 — 'What's the status of order X?' resolved purely from the
    graph. Raises NotFoundError if the order does not exist; never guesses."""
    row = session.run(
        """
        MATCH (o:Order {id: $id})
        OPTIONAL MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o)
        OPTIONAL MATCH (o)-[:BASED_ON_ALLOCATION]->(a:Allocation)
        OPTIONAL MATCH (o)-[:FOR_PART]->(p:Part)
        OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
        OPTIONAL MATCH (sh)-[:SHIPPED_TO]->(dest:DealerBranch)
        RETURN o.id AS order_id, o.status AS order_status, o.quantity AS quantity,
               o.synthetic AS synthetic, o.data_source AS data_source,
               o.provenance AS provenance,
               fr.status AS fulfilment_status, a.status AS allocation_status,
               p.part_id AS part_id, p.part_number AS part_number, p.part_name AS part_name,
               sh.shipment_id AS shipment_id, sh.status AS shipment_status,
               sh.eta AS eta, sh.delivered_at AS delivered_at,
               dest.dealer_id AS dealer_id, dest.dealer_name AS dealer_name
        """,
        {"id": order_id},
    ).single()
    if not row:
        raise NotFoundError(f"Order '{order_id}' not found")
    data = dict(row)
    if data.get("synthetic"):
        data["note"] = "SYNTHETIC DEMO DATA — this is a demo order, not a real HCME order."
    else:
        data["note"] = (
            "Status resolved from graph-confirmed Order/Allocation/Shipment state. "
            "NOT real HCME production data: provenance is 'INTERNAL_TEST_WORKFLOW' "
            "(every order created by this prototype's order-creation code path is "
            "structurally a test/development record — there is no real-transaction "
            "code path). Distinct from the synthetic=true demo-KPI orders above."
        )
    return data


def get_supply_chain(session, part_id: str) -> Dict[str, Any]:
    """KPI 1 support — Part -> synthetic InventorySnapshot(s) and any Depot
    the part has actually been sourced from in a demo Allocation. The real
    Depot node (Oosterhout) is returned only with its published, non-live
    facts; never a fabricated per-part stock count."""
    _part_or_404(session, part_id)
    inventory = session.run(
        """
        MATCH (p:Part {part_id: $id})-[:HAS_SYNTHETIC_INVENTORY]->(i:InventorySnapshot)
        RETURN i.snapshot_id AS snapshot_id, i.location_type AS location_type,
               i.location_id AS location_id, i.quantity AS quantity, i.as_of AS as_of,
               i.synthetic AS synthetic, i.data_source AS data_source
        """,
        {"id": part_id},
    ).data()
    depots = session.run(
        """
        MATCH (o:Order)-[:FOR_PART]->(p:Part {part_id: $id})
        MATCH (o)-[:BASED_ON_ALLOCATION]->(:Allocation)-[:SOURCED_FROM]->(d:Depot)
        RETURN DISTINCT d.depot_id AS depot_id, d.name AS name, d.city AS city, d.country AS country,
               d.source_id AS source_id, d.confidence AS confidence, d.synthetic AS synthetic,
               d.note AS note
        """,
        {"id": part_id},
    ).data()
    suppliers = session.run(
        """
        MATCH (o:Order)-[:FOR_PART]->(p:Part {part_id: $id})
        MATCH (o)-[:BASED_ON_ALLOCATION]->(:Allocation)-[:SOURCED_FROM]->(s:Supplier)
        RETURN DISTINCT s.supplier_id AS supplier_id, s.name AS name, s.country AS country,
               s.synthetic AS synthetic, s.data_source AS data_source
        """,
        {"id": part_id},
    ).data()
    return {
        "part_id": part_id,
        "inventory_snapshots": inventory,
        "depots": depots,
        "suppliers": suppliers,
        "note": (
            "inventory_snapshots and suppliers are SYNTHETIC DEMO DATA. depots "
            "reflects the one real, published HCME facility fact (existence + "
            "published facility statistics) — never a live or per-part stock number."
        ),
    }


def _classify_difference(part: Dict[str, Any], catalog_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic, non-LLM comparison. Never calls the LLM — the master-
    data consistency verdict must be graph/rule-derived, not generated."""
    # part_name is the short canonical name (comparable to a catalogue
    # listing); part_description is often a long compliance-page excerpt
    # (see Part PT-001), so prefer part_name for this comparison and only
    # fall back to description when no part_name is recorded.
    part_desc = (part.get("part_name") or part.get("description") or "").strip().lower()
    cat_desc = (catalog_entry.get("description") or "").strip().lower()
    part_cat = (part.get("part_category") or "").strip().lower()
    cat_cat = (catalog_entry.get("category") or "").strip().lower()

    if not cat_desc and not cat_cat:
        return {"verdict": "UNKNOWN", "reason": "CatalogEntry has no comparable description or category."}

    part_words = set(part_desc.replace("-", " ").split())
    cat_words = set(cat_desc.replace("-", " ").split())
    overlap = len(part_words & cat_words) / max(len(part_words | cat_words), 1)

    category_mismatch = bool(part_cat and cat_cat and part_cat != cat_cat)

    if part_desc == cat_desc and not category_mismatch:
        return {"verdict": "MATCH", "reason": "Description and category are identical.", "overlap": round(overlap, 2)}
    if category_mismatch or overlap < 0.3:
        return {
            "verdict": "SIGNIFICANT_DIFFERENCE",
            "reason": (
                f"Category mismatch (part='{part_cat or 'n/a'}' vs catalog='{cat_cat or 'n/a'}')"
                if category_mismatch
                else "Descriptions share little wording overlap."
            ),
            "overlap": round(overlap, 2),
        }
    return {
        "verdict": "MINOR_DIFFERENCE",
        "reason": "Same category, differing description wording — likely a stylistic/translation difference, not an error.",
        "overlap": round(overlap, 2),
    }


def get_cross_catalog(session, part_id: str) -> Dict[str, Any]:
    """KPI 2 (cross-catalog matching) + KPI 4 (master-data consistency).
    Returns every CatalogEntry evidenced (via CROSS_REFERENCES/
    ALTERNATIVE_FOR/SUPERSEDES) against this canonical Part, plus a
    deterministic MATCH/MINOR_DIFFERENCE/SIGNIFICANT_DIFFERENCE/UNKNOWN
    verdict with the evidence shown (never a plain 'error' label for
    stylistic differences)."""
    part = _part_or_404(session, part_id)
    rows = session.run(
        """
        MATCH (c:CatalogEntry)-[r:CROSS_REFERENCES|ALTERNATIVE_FOR|SUPERSEDES]->(p:Part {part_id: $id})
        RETURN c.catalog_entry_id AS catalog_entry_id, c.catalog_name AS catalog_name,
               c.catalog_part_number AS catalog_part_number, c.description AS description,
               c.category AS category, c.synthetic AS synthetic, c.data_source AS data_source,
               type(r) AS relationship_type, r.synthetic AS relationship_synthetic
        """,
        {"id": part_id},
    ).data()
    entries = []
    for row in rows:
        verdict = _classify_difference(part, row)
        entries.append({**row, **verdict})
    return {
        "part_id": part_id,
        "canonical_part": {
            "part_number": part.get("part_number"),
            "part_name": part.get("part_name"),
            "part_category": part.get("part_category"),
            "description": part.get("description"),
        },
        "catalog_entries": entries,
        "note": (
            "SYNTHETIC DEMO DATA — every CatalogEntry relationship here is a demo "
            "relationship built for KPI demonstration; no real HCME cross-catalog "
            "or supersession evidence beyond what prior research already covers was found. "
            "Verdicts are computed deterministically from graph fields, never by the LLM."
        ),
    }


def get_customs_flags(session, part_id: str) -> Dict[str, Any]:
    """KPI 5 — Part -> Order -> Shipment -> CustomsContext. All synthetic;
    never claims a real HCME shipment has a customs issue."""
    _part_or_404(session, part_id)
    rows = session.run(
        """
        MATCH (o:Order)-[:FOR_PART]->(p:Part {part_id: $id})
        MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)-[:HAS_CUSTOMS_CONTEXT]->(cc:CustomsContext)
        RETURN sh.shipment_id AS shipment_id, sh.origin AS origin, sh.destination AS destination,
               cc.customs_context_id AS customs_context_id, cc.origin_country AS origin_country,
               cc.destination_country AS destination_country, cc.hs_code AS hs_code,
               cc.requires_declaration AS requires_declaration, cc.customs_status AS customs_status,
               cc.flag_reason AS flag_reason, cc.synthetic AS synthetic, cc.data_source AS data_source
        """,
        {"id": part_id},
    ).data()
    return {
        "part_id": part_id,
        "customs_flags": rows,
        "note": "SYNTHETIC DEMO DATA — illustrates the customs-flag reasoning pattern only. No real HCME shipment customs data exists.",
    }


def get_graph_stats(session) -> Dict[str, Any]:
    """Part 22 validation surface, exposed live via API so the numbers in
    the KPI report can always be re-verified against the running graph."""
    def count(label: str, where: str = "") -> int:
        return session.run(f"MATCH (n:`{label}`) {where} RETURN count(n) AS c").single()["c"]

    return {
        "real": {
            "Part": count("Part"),
            "Machine": count("Machine"),
            "DealerBranch": count("DealerBranch"),
            "Depot": count("Depot", "WHERE n.synthetic = false"),
            "HAS_PART_FITMENT_relationships": session.run(
                "MATCH ()-[r:HAS_PART_FITMENT]->() RETURN count(r) AS c"
            ).single()["c"],
        },
        "synthetic": {
            "Supplier": count("Supplier"),
            "CatalogEntry": count("CatalogEntry"),
            "InventorySnapshot": count("InventorySnapshot"),
            "Order": count("Order", "WHERE n.synthetic = true"),
            "Shipment": count("Shipment"),
            "CustomsContext": count("CustomsContext"),
        },
        "integrity_checks": {
            "synthetic_records_missing_synthetic_flag": session.run(
                "MATCH (n) WHERE n.data_source = 'SYNTHETIC_DEMO' AND (n.synthetic IS NULL OR n.synthetic = false) RETURN count(n) AS c"
            ).single()["c"],
            "real_part_nodes_with_synthetic_property_set": session.run(
                "MATCH (p:Part) WHERE p.synthetic IS NOT NULL RETURN count(p) AS c"
            ).single()["c"],
            "real_dealer_nodes_with_synthetic_property_set": session.run(
                "MATCH (d:DealerBranch) WHERE d.synthetic IS NOT NULL RETURN count(d) AS c"
            ).single()["c"],
        },
    }
