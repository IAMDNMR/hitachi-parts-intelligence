from datetime import datetime, timezone, timedelta
from typing import List
from app.config import settings
from app.integrations.contracts.inventory import (
    InventoryProvider,
    SourceAvailabilityQuery,
    SourceInventoryItem,
    InventoryStatus,
    SourceType,
)

class TestInventoryProvider(InventoryProvider):
    def get_availability(self, query: SourceAvailabilityQuery) -> List[SourceInventoryItem]:
        # Rule BR-01: In production mode with unconfirmed external APIs, return UNKNOWN
        if settings.ENVIRONMENT == "production":
            return [
                SourceInventoryItem(
                    source_id="EXT-DEALER-PROD",
                    source_name="Production Dealer Provider",
                    source_type=SourceType.DEALER,
                    location_id="PROD-LOC-1",
                    on_hand_qty=0,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=0,
                    status=InventoryStatus.UNKNOWN,
                    provenance="UNCONFIRMED_EXTERNAL_API",
                    is_stale=True,
                )
            ]

        pn = query.part_number
        req_qty = query.quantity
        now = datetime.now(timezone.utc)
        iso_now = now.isoformat()
        iso_stale = (now - timedelta(seconds=settings.AVAILABILITY_FRESHNESS_TTL_SECONDS + 300)).isoformat()

        # Scenario 1: EXACT_MATCH_IN_STOCK
        if pn == "4656429" or pn == "TEST-EXACT-STOCK":
            return [
                SourceInventoryItem(
                    source_id="REGIONAL-DEPOT-AMS",
                    source_name="Amsterdam Regional Depot",
                    source_type=SourceType.REGIONAL_DEPOT,
                    location_id="BIN-A-12",
                    on_hand_qty=50,
                    reserved_qty=5,
                    allocated_qty=0,
                    available_qty=45,
                    status=InventoryStatus.AVAILABLE,
                    inventory_timestamp=iso_now,
                    provenance="HCME_ERP_SAP",
                    is_stale=False,
                )
            ]

        # Scenario 2: STALE_INVENTORY_TRIGGER
        if pn == "TEST-STALE":
            return [
                SourceInventoryItem(
                    source_id="DEALER-DEPOT-MUNICH",
                    source_name="Munich Dealer Depot",
                    source_type=SourceType.DEALER,
                    location_id="BIN-M-01",
                    on_hand_qty=10,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=10,
                    status=InventoryStatus.UNKNOWN,
                    inventory_timestamp=iso_stale,
                    provenance="DEALER_DMS_CACHE",
                    is_stale=True,
                )
            ]

        # Scenario 3: EXCEEDS_QUANTITY_PARTIAL
        if pn == "TEST-PARTIAL":
            return [
                SourceInventoryItem(
                    source_id="CENTRAL-DEPOT-JP",
                    source_name="Central Depot Japan",
                    source_type=SourceType.CENTRAL_DEPOT,
                    location_id="WH-CENTRAL-01",
                    on_hand_qty=3,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=3,
                    status=InventoryStatus.AVAILABLE,
                    inventory_timestamp=iso_now,
                    provenance="HCME_ERP_SAP",
                    is_stale=False,
                )
            ]

        # Scenario 4: PART_NOT_FOUND
        if pn == "TEST-NOT-FOUND" or pn == "INVALID-99999":
            return []

        # Scenario 5: PROVIDER_TIMEOUT / SYSTEM_UNAVAILABLE_BROKEN
        if pn == "TEST-TIMEOUT" or pn == "TEST-BROKEN":
            return [
                SourceInventoryItem(
                    source_id="DEALER-SYSTEM-ERR",
                    source_name="Unreachable Dealer DMS",
                    source_type=SourceType.DEALER,
                    location_id="UNKNOWN",
                    on_hand_qty=0,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=0,
                    status=InventoryStatus.UNKNOWN,
                    inventory_timestamp=iso_now,
                    provenance="PROVIDER_TIMEOUT",
                    is_stale=True,
                )
            ]

        # Scenario 6: DEALER_STOCK_PREFERRED
        if pn == "TEST-DEALER-PREFERRED":
            return [
                SourceInventoryItem(
                    source_id="DEALER-LOCAL-01",
                    source_name="Local Dealer Branch",
                    source_type=SourceType.DEALER,
                    location_id="BIN-D-05",
                    on_hand_qty=req_qty + 2,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=req_qty + 2,
                    status=InventoryStatus.AVAILABLE,
                    inventory_timestamp=iso_now,
                    provenance="DEALER_DMS",
                    is_stale=False,
                )
            ]

        # Scenario 7: MULTI_SOURCE_SPLIT
        if pn == "TEST-MULTI-SPLIT":
            return [
                SourceInventoryItem(
                    source_id="DEALER-BRANCH-A",
                    source_name="Branch A",
                    source_type=SourceType.DEALER,
                    location_id="BIN-A-01",
                    on_hand_qty=2,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=2,
                    status=InventoryStatus.AVAILABLE,
                    inventory_timestamp=iso_now,
                    provenance="DEALER_DMS",
                    is_stale=False,
                ),
                SourceInventoryItem(
                    source_id="REGIONAL-DEPOT-AMS",
                    source_name="Amsterdam Depot",
                    source_type=SourceType.REGIONAL_DEPOT,
                    location_id="BIN-R-10",
                    on_hand_qty=5,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=5,
                    status=InventoryStatus.AVAILABLE,
                    inventory_timestamp=iso_now,
                    provenance="HCME_ERP_SAP",
                    is_stale=False,
                )
            ]

        # Scenario 8: REMAN_ALTERNATIVE_AVAILABLE
        if pn == "TEST-REMAN":
            return [
                SourceInventoryItem(
                    source_id="REMAN-FACILITY-NL",
                    source_name="HCME Reman Center",
                    source_type=SourceType.REMAN_FACILITY,
                    location_id="REMAN-BAY-02",
                    on_hand_qty=10,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=10,
                    status=InventoryStatus.AVAILABLE,
                    inventory_timestamp=iso_now,
                    provenance="REMAN_INVENTORY_SYSTEM",
                    is_stale=False,
                )
            ]

        # Scenario 9: CONCURRENCY_CONFLICT_TRIGGER
        if pn == "TEST-CONCURRENCY":
            return [
                SourceInventoryItem(
                    source_id="TEST-CONCURRENCY-SOURCE",
                    source_name="Concurrency Test Source",
                    source_type=SourceType.REGIONAL_DEPOT,
                    location_id="LOCK-BIN-01",
                    on_hand_qty=1,
                    reserved_qty=0,
                    allocated_qty=0,
                    available_qty=1,
                    status=InventoryStatus.AVAILABLE,
                    inventory_timestamp=iso_now,
                    provenance="TEST_SYSTEM",
                    is_stale=False,
                )
            ]

        # Default Fallback for generic parts: Return 10 available
        return [
            SourceInventoryItem(
                source_id="REGIONAL-DEPOT-DEFAULT",
                source_name="Standard Depot",
                source_type=SourceType.REGIONAL_DEPOT,
                location_id="DEFAULT-BIN",
                on_hand_qty=req_qty + 5,
                reserved_qty=0,
                allocated_qty=0,
                available_qty=req_qty + 5,
                status=InventoryStatus.AVAILABLE,
                inventory_timestamp=iso_now,
                provenance="DEFAULT_MOCK",
                is_stale=False,
            )
        ]
