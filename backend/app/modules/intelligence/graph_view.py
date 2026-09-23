"""
backend/app/modules/intelligence/graph_view.py

Builds the {nodes, edges} graph-visualization payload for Parts Intelligence
answers that involve more than one entity type (machine/part/supplier/
dealer/depot/city/country). This is purely a display projection over the
evidence each handler in assistant.py already computed — it never queries
Neo4j itself and never invents a relationship that the handler's own
evidence doesn't already contain.

Every edge is tagged with a `relationship_source` from the classification
the platform uses everywhere else:
  REAL           — a relationship instance that actually exists in Neo4j
  SOURCE_DERIVED — computed from real source data, not itself one edge
  DERIVED        — computed at query time from other real facts (e.g. two
                   nodes sharing a City), never persisted as its own edge
  SYNTHETIC_DEMO — demo-only data (e.g. SUPPLIED_BY, which is never
                   source-derived in this dataset — see graph_query.py)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _node(node_id: str, node_type: str, label: str, data_class: str = "SOURCE_DERIVED") -> Dict[str, Any]:
    return {"id": node_id, "type": node_type, "label": label, "data_class": data_class}


def _edge(source: str, target: str, relationship: str, display: str, relationship_source: str) -> Dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "relationship": relationship,
        "display_relationship": display,
        "relationship_source": relationship_source,
    }


def _dealer_id(d: Dict[str, Any]) -> str:
    return f"dealer:{d.get('dealer_id') or d.get('dealer_name')}"


def _supplier_id(s: Dict[str, Any]) -> str:
    return f"supplier:{s.get('supplier_number') or s.get('name')}"


def _city_id(name: str) -> str:
    return f"city:{name}"


def _co_located_graph(city: str, country: Optional[str], anchor_dealer: Optional[str],
                       dealers: List[Dict[str, Any]], suppliers: List[Dict[str, Any]],
                       depots: List[str], max_each: int = 12, is_depot: bool = False) -> Dict[str, Any]:
    """Shared-city tree: DealerBranch/Depot -[:LOCATED_IN]-> City <-[:LOCATED_IN]- Supplier.

    Every edge here is a real, persisted LOCATED_IN relationship (REAL) — the
    connection being shown between the dealer/depot side and the supplier
    side is the shared city itself, so it is DERIVED, never a business
    relationship. That is stated in `relationship_note`, not invented as a
    fake edge between the two entities.
    """
    city_node_id = _city_id(city)
    nodes = [_node(city_node_id, "City", f"{city}{f', {country}' if country else ''}", "SOURCE_DERIVED")]
    edges: List[Dict[str, Any]] = []

    for name in depots[:max_each]:
        depot_id = f"depot:{name}"
        nodes.append(_node(depot_id, "Depot", name, "SOURCE_DERIVED"))
        edges.append(_edge(depot_id, city_node_id, "LOCATED_IN", "Located in", "REAL"))

    seen_dealer_ids = set()
    for d in dealers[:max_each]:
        did = _dealer_id(d)
        if did in seen_dealer_ids:
            continue
        seen_dealer_ids.add(did)
        nodes.append(_node(did, "DealerBranch", d.get("dealer_name") or "Dealer", "SOURCE_DERIVED"))
        edges.append(_edge(did, city_node_id, "LOCATED_IN", "Located in", "REAL"))

    if anchor_dealer and not any(d.get("dealer_name") == anchor_dealer for d in dealers):
        if is_depot:
            aid = f"depot:{anchor_dealer}"
            nodes.append(_node(aid, "Depot", anchor_dealer, "SOURCE_DERIVED"))
            edges.append(_edge(aid, city_node_id, "LOCATED_IN", "Located in", "REAL"))
        else:
            aid = f"dealer:{anchor_dealer}"
            nodes.append(_node(aid, "DealerBranch", anchor_dealer, "SOURCE_DERIVED"))
            edges.append(_edge(aid, city_node_id, "LOCATED_IN", "Located in", "REAL"))

    for s in suppliers[:max_each]:
        sid = _supplier_id(s)
        nodes.append(_node(sid, "Supplier", s.get("name") or "Supplier", "SOURCE_DERIVED"))
        edges.append(_edge(sid, city_node_id, "LOCATED_IN", "Located in", "REAL"))

    rel_note = (
        "Suppliers and the depot shown here share one City node — that is a geographic "
        "coincidence (SAME CITY AS DEPOT — DERIVED), not a commercial relationship."
        if is_depot else
        "Dealers and suppliers shown here share one City node — that is a geographic "
        "coincidence (SAME CITY — DERIVED), not a supplier or commercial relationship."
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "relationship_note": rel_note,
    }


def build_graph_view(intent: str, ext: Dict[str, Any], result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Graph payload with unique node ids and unique edges (the UI keys by id)."""
    g = _build_graph_view(intent, ext, result)
    if not g:
        return g
    seen, nodes = set(), []
    for n in g["nodes"]:
        if n["id"] not in seen:
            seen.add(n["id"])
            nodes.append(n)
    seen_e, edges = set(), []
    for e in g["edges"]:
        key = (e["source"], e["target"], e["relationship"])
        if key not in seen_e:
            seen_e.add(key)
            edges.append(e)
    return {**g, "nodes": nodes, "edges": edges}


def _build_graph_view(intent: str, ext: Dict[str, Any], result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a {nodes, edges, relationship_note} payload for network-shaped
    answers, or None when the answer isn't a multi-entity/network question
    (a plain part search, order lookup, etc. gets no graph — the flat
    result list already is the answer)."""
    if result.get("clarify"):
        return None
    data = result.get("data") or {}
    evidence = result.get("evidence") or {}

    if intent == "supplier_lookup" and "dealers" in data and "city" in evidence:
        return _co_located_graph(
            city=evidence["city"], country=evidence.get("country"),
            anchor_dealer=evidence.get("anchor_dealer"),
            dealers=data.get("dealers") or [], suppliers=data.get("suppliers") or [],
            depots=evidence.get("depots") or [],
            is_depot=bool(evidence.get("anchor_is_depot")),
        )

    if intent == "dealer_supplier_network" and evidence.get("cities_with_both"):
        rows = evidence["cities_with_both"][:10]
        root = "europe:network"
        nodes = [_node(root, "Catalogue", "Cities with dealers and suppliers", "SOURCE_DERIVED")]
        edges = []
        for r in rows:
            cid = _city_id(f"{r['city']}|{r['country']}")
            nodes.append(_node(cid, "City", f"{r['city']} ({r['country']}) · {r['dealers']} dealer(s) · {r['suppliers']} supplier(s)", "SOURCE_DERIVED"))
            edges.append(_edge(root, cid, "CONTAINS_CITY", "Shared city", "DERIVED"))
        return {"nodes": nodes, "edges": edges,
                "relationship_note": "SAME CITY — DERIVED: dealers and suppliers share a city; no commercial relationship is implied."}

    if intent == "dealer_supplier_network":
        if "city" in evidence:
            return _co_located_graph(
                city=evidence["city"], country=evidence.get("country"), anchor_dealer=None,
                dealers=data.get("dealers") or [], suppliers=data.get("suppliers") or [],
                depots=evidence.get("depots") or [],
            )
        if "country" in evidence and evidence.get("shared_cities") is not None:
            country = evidence["country"]
            country_id = f"country:{country}"
            nodes = [_node(country_id, "Country", country, "SOURCE_DERIVED")]
            edges: List[Dict[str, Any]] = []
            for row in evidence["shared_cities"][:6]:
                city_id = _city_id(row["city_name"])
                label = f"{row['city_name']} ({row['dealer_count']} dealer(s) · {row['supplier_count']} supplier(s))"
                nodes.append(_node(city_id, "City", label, "SOURCE_DERIVED"))
                edges.append(_edge(city_id, country_id, "IN_COUNTRY", "In country", "REAL"))
            return {
                "nodes": nodes,
                "edges": edges,
                "relationship_note": (
                    f"{country} network: Country → Cities (showing dealer and supplier counts per city). "
                    "Dealers and suppliers sharing a city have relationship: SAME CITY — DERIVED "
                    "(geographic coincidence only, not a commercial relationship)."
                ),
            }
        return None

    if intent == "machine_list":
        if "machine_category" in evidence:
            cat = evidence["machine_category"]
            cat_id = f"category:{cat}"
            nodes = [_node(cat_id, "MachineCategory", cat, "SOURCE_DERIVED")]
            edges = []
            for m in (data.get("machines") or [])[:12]:
                mid = f"machine:{m.get('machine_id') or m.get('model')}"
                nodes.append(_node(mid, "Machine", m.get("model") or "Machine", "SOURCE_DERIVED"))
                edges.append(_edge(cat_id, mid, "HAS_MODEL", "Has model", "SOURCE_DERIVED"))
            return {
                "nodes": nodes,
                "edges": edges,
                "relationship_note": f"HCME Europe catalogue: {cat} models (SOURCE_DERIVED).",
            }
        if "categories" in evidence:
            root_id = "hcme:catalogue"
            nodes = [_node(root_id, "Catalogue", "HCME Machine Catalogue", "SOURCE_DERIVED")]
            edges = []
            for c in evidence["categories"]:
                cid = f"category:{c['category']}"
                nodes.append(_node(cid, "MachineCategory", f"{c['category']} ({c['count']})", "SOURCE_DERIVED"))
                edges.append(_edge(root_id, cid, "CONTAINS_CATEGORY", "Contains category", "SOURCE_DERIVED"))
            return {
                "nodes": nodes,
                "edges": edges,
                "relationship_note": "HCME Europe machinery catalogue breakdown (SOURCE_DERIVED).",
            }
        return None

    if intent == "machine_supplier_by_part_category":
        machine_type = evidence.get("query_entities", {}).get("machine_type")
        parts = data.get("parts") or []
        supplier_links = data.get("supplier_links") or []
        if not machine_type or not parts:
            return None
        mt_id = f"machine_type:{machine_type}"
        nodes = [_node(mt_id, "MachineType", machine_type, "SOURCE_DERIVED")]
        edges = []
        part_ids_in_graph = set()
        for p in parts[:6]:
            pid = f"part:{p['part_id']}"
            part_ids_in_graph.add(p["part_id"])
            nodes.append(_node(pid, "Part", f"{p['part_id']} {p.get('part_name') or ''}".strip(), "SOURCE_DERIVED"))
            edges.append(_edge(mt_id, pid, "HAS_PART_FITMENT", "Has part fitment", "SOURCE_DERIVED"))
        if not supplier_links:
            return {
                "nodes": nodes,
                "edges": edges,
                "relationship_note": (
                    "Machine → Part fitment is source-derived. Supplier-to-part mapping is not recorded "
                    "in current HCME supplier source (NOT CONNECTED)."
                ),
            }
        supplier_ids_added = set()
        for link in supplier_links:
            part_id = link.get("_part_id")
            if part_id not in part_ids_in_graph:
                continue
            sid = _supplier_id({"supplier_number": link.get("supplier_number"), "name": link.get("name")})
            data_class = link.get("_data_class") or "SYNTHETIC_DEMO"
            if sid not in supplier_ids_added:
                supplier_ids_added.add(sid)
                nodes.append(_node(sid, "Supplier", link.get("name") or "Supplier", data_class))
            edges.append(_edge(f"part:{part_id}", sid, "SUPPLIED_BY", "Supplied by", data_class))
        return {
            "nodes": nodes,
            "edges": edges,
            "relationship_note": (
                "Machine → Part fitment is source-derived. Authoritative supplier records shown."
            ),
        }

    if intent == "impact_analysis":
        part = data.get("part") or {}
        machines = data.get("machines") or []
        if not part.get("part_id") or not machines:
            return None
        pid = f"part:{part['part_id']}"
        nodes = [_node(pid, "Part", f"{part['part_id']} {part.get('name') or ''}".strip(), "SOURCE_DERIVED")]
        edges = []
        for m in machines[:12]:
            mid = f"machine:{m['machine_id']}"
            nodes.append(_node(mid, "Machine", m["model"], "SOURCE_DERIVED"))
            edges.append(_edge(pid, mid, "HAS_PART_FITMENT", "Fits", "SOURCE_DERIVED"))
        return {"nodes": nodes, "edges": edges,
                "relationship_note": f"{part['part_id']} → HAS_PART_FITMENT → Machine (SOURCE_DERIVED HCME Europe fitment data)."}

    if intent == "supply_chain":
        part = data.get("part") or {}
        if not part.get("part_id"):
            return None
        pid = f"part:{part['part_id']}"
        nodes = [_node(pid, "Part", f"{part['part_id']} {part.get('name') or ''}".strip(), "SOURCE_DERIVED")]
        edges = []
        for i, st in enumerate(data.get("stock") or []):
            sid = f"stock:{i}:{st['location']}"
            nodes.append(_node(sid, "Depot", f"{st['location']} · {st['qty']} units", "SYNTHETIC_DEMO"))
            edges.append(_edge(pid, sid, "HAS_SYNTHETIC_INVENTORY", "Stocked at (demo)", "SYNTHETIC_DEMO"))
        for s in data.get("supply_suppliers") or []:
            sid = f"supplier:{s['supplier']}"
            nodes.append(_node(sid, "Supplier", s["supplier"], "SYNTHETIC_DEMO"))
            edges.append(_edge(pid, sid, "SUPPLIED_BY", "Supplied by (demo)", "SYNTHETIC_DEMO"))
        return {"nodes": nodes, "edges": edges,
                "relationship_note": "Stock and Part → SUPPLIED_BY links are SYNTHETIC DEMO data; the real supplier master has no part numbers."}

    if intent == "dealer_supplier_network" and evidence.get("cities_with_both"):
        rows = evidence["cities_with_both"][:10]
        root = "europe:network"
        nodes = [_node(root, "Catalogue", "Cities with dealers and suppliers", "SOURCE_DERIVED")]
        edges = []
        for r in rows:
            cid = _city_id(f"{r['city']}|{r['country']}")
            nodes.append(_node(cid, "City", f"{r['city']} ({r['country']}) · {r['dealers']} dealer(s) · {r['suppliers']} supplier(s)", "SOURCE_DERIVED"))
            edges.append(_edge(root, cid, "CONTAINS_CITY", "Shared city", "DERIVED"))
        return {"nodes": nodes, "edges": edges,
                "relationship_note": "SAME CITY — DERIVED: dealers and suppliers share a city; no commercial relationship is implied."}

    if intent == "dealer_lookup":
        d = (data.get("dealers") or [None])[0]
        if not d or not d.get("city_node") or not d.get("country_name"):
            return None
        did, cid, coid = f"dealer:{d['dealer_id']}", _city_id(d["city_node"]), f"country:{d['country_name']}"
        return {"nodes": [_node(did, "Dealer", d["dealer_name"], "SOURCE_DERIVED"),
                          _node(cid, "City", d["city_node"], "SOURCE_DERIVED"),
                          _node(coid, "Country", d["country_name"], "SOURCE_DERIVED")],
                "edges": [_edge(did, cid, "LOCATED_IN", "Located in", "SOURCE_DERIVED"),
                          _edge(cid, coid, "IN_COUNTRY", "In country", "SOURCE_DERIVED")],
                "relationship_note": "DealerBranch → LOCATED_IN → City → IN_COUNTRY → Country (SOURCE_DERIVED)."}

    if intent == "machine_parts_by_category":
        machine_type = evidence.get("machine_type")
        parts = data.get("parts") or []
        if not machine_type or not parts:
            return None
        mt_id = f"machine_type:{machine_type}"
        nodes = [_node(mt_id, "MachineType", machine_type, "SOURCE_DERIVED")]
        edges = [
            _edge(mt_id, f"part:{p['part_id']}", "HAS_PART_FITMENT", "Has part fitment", "SOURCE_DERIVED")
            for p in parts[:10]
        ]
        for p in parts[:10]:
            nodes.append(_node(f"part:{p['part_id']}", "Part", f"{p['part_id']} {p.get('part_name') or ''}".strip(), "SOURCE_DERIVED"))
        return {
            "nodes": nodes, "edges": edges,
            "relationship_note": "Machine → Part fitment (SOURCE_DERIVED HCME Europe catalogue).",
        }

    return None
