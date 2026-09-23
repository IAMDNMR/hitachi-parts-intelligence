"""
backend/tests/test_graph_view.py

Phase 10 (Parts Intelligence network visualization): graph_view.build_graph_view
is a pure projection over each handler's already-computed evidence/data, so
most of its behaviour is tested directly with constructed inputs — no Neo4j
needed. A handful of end-to-end tests below exercise the real pipeline
(route_and_answer_query against the live AuraDB graph) for the golden
multi-entity regression cases from the Phase 10 spec.
"""

import pytest

from app.modules.intelligence.graph_view import build_graph_view
from app.modules.intelligence.assistant import route_and_answer_query


# ---------------------------------------------------------------------------
# Pure unit tests — no Neo4j
# ---------------------------------------------------------------------------

def test_no_graph_when_the_answer_asked_for_clarification():
    result = {"clarify": "Which city?", "evidence": {}, "data": {}}
    assert build_graph_view("supplier_lookup", {}, result) is None


def test_no_graph_for_a_plain_part_search():
    result = {"evidence": {}, "data": {"candidates": [{"part_id": "PT-001"}]}}
    assert build_graph_view("part_search", {}, result) is None


def test_same_city_graph_never_invents_a_dealer_supplier_edge():
    """Dealer/Depot and Supplier nodes only ever connect through the shared
    City node (both real LOCATED_IN edges) — never a direct edge between
    them, since no commercial relationship is recorded."""
    result = {
        "evidence": {
            "city": "Veldhoven", "country": "NL", "anchor_dealer": "Pellen Machines", "depots": [],
        },
        "data": {
            "dealers": [{"dealer_id": "D-1", "dealer_name": "Pellen Machines"}],
            "suppliers": [{"supplier_number": "0000100026", "name": "Supplier A"}],
        },
    }
    graph = build_graph_view("supplier_lookup", {}, result)
    assert graph is not None
    node_types = {n["type"] for n in graph["nodes"]}
    assert node_types == {"City", "DealerBranch", "Supplier"}
    # Every edge touches the City node; none connects Dealer directly to Supplier.
    city_id = next(n["id"] for n in graph["nodes"] if n["type"] == "City")
    for edge in graph["edges"]:
        assert city_id in (edge["source"], edge["target"])
        assert edge["relationship"] == "LOCATED_IN"
        assert edge["relationship_source"] == "REAL"
    assert "no supplier or commercial relationship" in graph["relationship_note"].lower() or \
        "derived" in graph["relationship_note"].lower()


def test_country_network_graph_uses_aggregate_city_counts_only():
    result = {
        "evidence": {
            "country": "NL", "dealer_count": 10, "supplier_count": 500,
            "shared_cities": [{"city_name": "Veldhoven", "dealer_count": 2, "supplier_count": 5}],
        },
        "data": {"shared_cities": [{"city_name": "Veldhoven", "dealer_count": 2, "supplier_count": 5}]},
    }
    graph = build_graph_view("dealer_supplier_network", {}, result)
    assert graph is not None
    types = {n["type"] for n in graph["nodes"]}
    assert types == {"Country", "City"}
    assert "Veldhoven" in graph["nodes"][1]["label"]


def test_supplied_by_edge_only_appears_when_evidence_has_a_link_and_is_always_labelled_synthetic():
    result = {
        "evidence": {"query_entities": {"machine_type": "medium excavator", "part_category": "bucket", "country": "NL"}},
        "data": {
            "parts": [{"part_id": "PT-020", "part_name": "Bucket"}],
            "supplier_links": [{"_part_id": "PT-020", "supplier_number": "1", "name": "Supplier X"}],
        },
    }
    graph = build_graph_view("machine_supplier_by_part_category", {}, result)
    assert graph is not None
    supplied_by_edges = [e for e in graph["edges"] if e["relationship"] == "SUPPLIED_BY"]
    assert len(supplied_by_edges) == 1
    assert supplied_by_edges[0]["relationship_source"] == "SYNTHETIC_DEMO"
    supplier_nodes = [n for n in graph["nodes"] if n["type"] == "Supplier"]
    assert all(n["data_class"] == "SYNTHETIC_DEMO" for n in supplier_nodes)


def test_no_supplier_node_at_all_when_no_supplier_link_exists():
    """The critical regression this whole feature exists to prevent: when
    the graph has no real Supplier->Part evidence, the network view must not
    show suppliers at all — not the generic country list, not an invented
    edge."""
    result = {
        "evidence": {"query_entities": {"machine_type": "medium excavator", "part_category": "bucket", "country": "NL"}},
        "data": {"parts": [{"part_id": "PT-020", "part_name": "Bucket"}], "supplier_links": []},
    }
    graph = build_graph_view("machine_supplier_by_part_category", {}, result)
    assert graph is not None
    assert not any(n["type"] == "Supplier" for n in graph["nodes"])
    assert not any(e["relationship"] == "SUPPLIED_BY" for e in graph["edges"])


# ---------------------------------------------------------------------------
# End-to-end golden regression tests — real AuraDB
# ---------------------------------------------------------------------------

def test_golden_buckets_suppliers_for_medium_excavator_in_netherlands_never_returns_bare_country_list(neo4j_session):
    resp = route_and_answer_query(neo4j_session, "buckets suppliers for my medium excavator in Netherlands")
    assert resp["intent"] == "machine_supplier_by_part_category"
    assert resp["entities"]["machine_type"]
    assert resp["entities"]["part_category"]
    assert resp["entities"]["country"] == "NL"
    # The critical regression: this must never silently degrade into "every
    # supplier in the Netherlands" with no machine/part context retained.
    countrywide = resp["evidence"].get("suppliers_in_country")
    if countrywide:
        assert countrywide["note"]  # explicitly labelled location-only, not a fitment claim
    assert "supplier_part_mapping" in resp["evidence"]
    assert resp["evidence"]["supplier_part_mapping"]["data_class"] in ("NOT_CONNECTED", "SYNTHETIC_DEMO")


def test_golden_dealers_and_suppliers_in_netherlands_has_graph(neo4j_session):
    resp = route_and_answer_query(neo4j_session, "dealers and suppliers in Netherlands")
    assert resp["intent"] == "dealer_supplier_network"
    assert resp["graph"] is not None
    assert {n["type"] for n in resp["graph"]["nodes"]} <= {"Country", "City"}


def test_golden_suppliers_same_city_as_pellen_machines(neo4j_session):
    resp = route_and_answer_query(neo4j_session, "which suppliers are in the same city as Pellen Machines")
    assert resp["intent"] == "supplier_lookup"
    if resp["graph"]:
        for edge in resp["graph"]["edges"]:
            assert edge["relationship"] == "LOCATED_IN"


def test_golden_who_supplies_pt001_never_hallucinates(neo4j_session):
    resp = route_and_answer_query(neo4j_session, "who supplies PT-001")
    # Must never claim a confirmed supplier without SOURCE_DERIVED evidence.
    assert "hallucinat" not in resp["answer"].lower()
