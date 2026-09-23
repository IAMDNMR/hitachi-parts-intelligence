"""
backend/tests/test_operational_demo_data.py

Tests for the operational/commercial context layer (HCME Europe KPI
foundation) built by docs/data/neo4j/scripts/seed_operational_demo_data.py
and read by backend/app/modules/intelligence/context.py.

Unlike the other test modules, these tests do NOT use the per-test
testRunId/cleanup fixture — the demo dataset is persistent seed data (like
the real Part/DealerBranch graph), not per-test scratch data. Tests only
read it (and, for the idempotency test, re-run the seed script's own `run()`
function, which is itself pure MERGE). Nothing here mutates Phase 6 state.

Requires the seed script to have already been run once against the target
Neo4j database (`python docs/data/neo4j/scripts/seed_operational_demo_data.py`).
"""

import importlib.util
import os
import sys

import pytest

from app.modules.intelligence import context as intelligence_context

# Import the seed script as a module (it lives outside backend/app, so
# import it by path rather than as an installed package).
_SEED_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "data", "neo4j", "scripts", "seed_operational_demo_data.py"
)
_spec = importlib.util.spec_from_file_location("seed_operational_demo_data", _SEED_SCRIPT_PATH)
seed_module = importlib.util.module_from_spec(_spec)
sys.modules["seed_operational_demo_data"] = seed_module
_spec.loader.exec_module(seed_module)


PART_1 = "PT-001"
PART_2 = "PT-002"
PART_3 = "PT-010"


def test_seed_is_idempotent(neo4j_session):
    """Re-running the seed script must not change any node/relationship
    count in the demo layer (pure MERGE, keyed on stable ids)."""
    def counts():
        labels = ["Depot", "Supplier", "CatalogEntry", "InventorySnapshot", "Shipment", "CustomsContext"]
        out = {}
        for lbl in labels:
            # Only the seed's own nodes: API-flow tests may create untagged Shipments transiently.
            extra = " AND n.shipment_id STARTS WITH 'ship-demo-'" if lbl == "Shipment" else ""
            out[lbl] = neo4j_session.run(f"MATCH (n:`{lbl}`) WHERE n.testRunId IS NULL{extra} RETURN count(n) AS c").single()["c"]
        out["demo_Order"] = neo4j_session.run(
            "MATCH (o:Order) WHERE o.id STARTS WITH 'order-demo-' RETURN count(o) AS c"
        ).single()["c"]
        return out

    before = counts()
    seed_module.run(dry_run=False)
    after = counts()
    assert before == after


def test_canonical_part_preserved(neo4j_session):
    """The seed script must never create/duplicate Part nodes — only MATCH
    existing canonical ones. part_number must be unchanged for the demo
    parts."""
    for part_id, expected_pn in [(PART_1, "4663907"), (PART_2, "4621541"), (PART_3, "YA60106848")]:
        row = neo4j_session.run(
            "MATCH (p:Part {part_id: $id}) RETURN p.part_number AS pn, p.synthetic AS synthetic", {"id": part_id}
        ).single()
        assert row is not None, f"{part_id} must already exist as a real canonical Part"
        assert row["pn"] == expected_pn
        assert row["synthetic"] is None, "seeding must never write a synthetic flag onto a real Part node"


def test_dealer_linkage_real(neo4j_session):
    """Demo shipments must link to real DealerBranch nodes, never a
    synthetic/duplicated dealer."""
    rows = neo4j_session.run(
        """
        MATCH (sh:Shipment)-[:SHIPPED_TO]->(d:DealerBranch)
        RETURN d.dealer_id AS dealer_id, d.synthetic AS synthetic
        """
    ).data()
    assert len(rows) >= 2
    for row in rows:
        assert row["synthetic"] is None


def test_order_context_traversal_kpi1(neo4j_session):
    """KPI 1: Part -> Order -> Allocation/FulfilmentRequest -> Shipment ->
    DealerBranch is fully graph-traversable and explainable."""
    result = intelligence_context.get_order_context(neo4j_session, PART_1)
    assert result["part_id"] == PART_1
    assert len(result["orders"]) >= 1
    order = result["orders"][0]
    assert order["order_synthetic"] is True
    assert order["order_data_source"] == "SYNTHETIC_DEMO"
    assert order["fulfilment_request_id"] is not None
    assert order["allocation_id"] is not None


def test_order_status_query_kpi3(neo4j_session):
    """KPI 3: order status resolved purely from the graph, no LLM."""
    result = intelligence_context.get_order_status(neo4j_session, "order-demo-001")
    assert result["order_status"] in ("CREATED", "ACCEPTED", "CANCELLED")
    assert result["synthetic"] is True
    assert "SYNTHETIC DEMO DATA" in result["note"]


def test_order_status_unknown_order_raises(neo4j_session):
    from app.errors.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        intelligence_context.get_order_status(neo4j_session, "order-does-not-exist")


def test_supply_chain_real_depot_flagged_correctly(neo4j_session):
    """The Depot returned for PART_1 must carry synthetic=False (real) while
    inventory snapshots carry synthetic=True."""
    result = intelligence_context.get_supply_chain(neo4j_session, PART_1)
    assert len(result["depots"]) >= 1
    for depot in result["depots"]:
        assert depot["synthetic"] is False
        assert depot["source_id"] == "SRC-050"
    for inv in result["inventory_snapshots"]:
        assert inv["synthetic"] is True
        assert inv["data_source"] == "SYNTHETIC_DEMO"


def test_cross_catalog_master_data_verdicts_kpi2_kpi4(neo4j_session):
    """KPI 2/4: verdicts must be MATCH / MINOR_DIFFERENCE / SIGNIFICANT_DIFFERENCE
    / UNKNOWN, never a bare 'error', and every entry must be marked synthetic."""
    result = intelligence_context.get_cross_catalog(neo4j_session, PART_1)
    assert len(result["catalog_entries"]) >= 2
    verdicts = {e["catalog_entry_id"]: e["verdict"] for e in result["catalog_entries"]}
    assert verdicts["CAT-DEMO-001"] == "MATCH"
    assert verdicts["CAT-DEMO-003"] == "SIGNIFICANT_DIFFERENCE"
    for e in result["catalog_entries"]:
        assert e["synthetic"] is True
        assert e["verdict"] in ("MATCH", "MINOR_DIFFERENCE", "SIGNIFICANT_DIFFERENCE", "UNKNOWN")


def test_customs_flags_kpi5(neo4j_session):
    """KPI 5: cross-border demo shipment (NL->GB) must be flagged; the
    intra-EU shipment must have no CustomsContext at all."""
    result_gb = intelligence_context.get_customs_flags(neo4j_session, PART_2)
    assert len(result_gb["customs_flags"]) == 1
    flag = result_gb["customs_flags"][0]
    assert flag["requires_declaration"] is True
    assert flag["synthetic"] is True
    assert flag["destination_country"] == "GB"

    result_nl = intelligence_context.get_customs_flags(neo4j_session, PART_1)
    assert result_nl["customs_flags"] == []


def test_graph_stats_no_unflagged_synthetic_records(neo4j_session):
    """Part 22 critical check: zero synthetic records missing synthetic=true,
    and zero real Part/DealerBranch nodes with a synthetic property set."""
    stats = intelligence_context.get_graph_stats(neo4j_session)
    assert stats["integrity_checks"]["synthetic_records_missing_synthetic_flag"] == 0
    assert stats["integrity_checks"]["real_part_nodes_with_synthetic_property_set"] == 0
    assert stats["integrity_checks"]["real_dealer_nodes_with_synthetic_property_set"] == 0
    assert stats["real"]["DealerBranch"] == 182
