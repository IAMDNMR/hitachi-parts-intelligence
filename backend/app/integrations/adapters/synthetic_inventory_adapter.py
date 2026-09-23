"""
backend/app/integrations/adapters/synthetic_inventory_adapter.py

Phase 10 inventory provider for catalogue parts.

No live HCME ERP/WMS stock feed is connected. For a part that exists in the
canonical Part graph, stock is read from the SYNTHETIC_DEMO InventorySnapshot
nodes seeded by docs/data/neo4j/scripts/seed_phase10_demo_data.py (held at the
real Oosterhout depot or at a real DealerBranch) and returned with
provenance='SYNTHETIC_DEMO' so every downstream record is labelled.

Part numbers that are not in the catalogue, or whose Part node was created
by a test run (testRunId set), are delegated to the existing
TestInventoryProvider scenarios unchanged. A catalogue part with no demo
stock returns no sources — availability is never invented for it.
"""

from datetime import datetime, timezone
from typing import List

from app.config import settings
from app.db.neo4j.connection import get_neo4j_driver
from app.integrations.contracts.inventory import (
    InventoryProvider,
    InventoryStatus,
    SourceAvailabilityQuery,
    SourceInventoryItem,
    SourceType,
)
from app.integrations.mocks.inventory_mock import TestInventoryProvider

_LOCATION_TYPES = {"DEPOT": SourceType.CENTRAL_DEPOT, "DEALER": SourceType.DEALER}

_STOCK_QUERY = """
MATCH (p:Part {part_number: $pn})
OPTIONAL MATCH (p)-[:HAS_SYNTHETIC_INVENTORY]->(i:InventorySnapshot)
WHERE i.location_type IN ['DEPOT', 'DEALER']
OPTIONAL MATCH (d:Depot {depot_id: i.location_id})
OPTIONAL MATCH (b:DealerBranch {dealer_id: i.location_id})
RETURN p.part_id AS part_id, p.testRunId AS test_run_id, i.location_type AS location_type, i.location_id AS location_id,
       i.quantity AS quantity, coalesce(d.name, b.dealer_name) AS location_name
"""


class SyntheticDemoInventoryProvider(InventoryProvider):
    def __init__(self, fallback: InventoryProvider | None = None):
        self.fallback = fallback or TestInventoryProvider()

    def get_availability(self, query: SourceAvailabilityQuery) -> List[SourceInventoryItem]:
        driver = get_neo4j_driver()
        with driver.session(database=settings.NEO4J_DATABASE or None) as s:
            rows = s.run(_STOCK_QUERY, pn=query.part_number).data()

        if not rows or rows[0]["test_run_id"] is not None:
            return self.fallback.get_availability(query)

        now = datetime.now(timezone.utc).isoformat()
        return [
            SourceInventoryItem(
                source_id=r["location_id"],
                source_name=r["location_name"] or r["location_id"],
                source_type=_LOCATION_TYPES[r["location_type"]],
                location_id=r["location_id"],
                on_hand_qty=r["quantity"],
                available_qty=r["quantity"],
                status=InventoryStatus.AVAILABLE,
                inventory_timestamp=now,
                provenance="SYNTHETIC_DEMO",
            )
            for r in rows
            if r["location_id"] is not None
        ]
