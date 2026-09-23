from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class InventoryStatus(str, Enum):
    ON_HAND = "ON_HAND"
    RESERVED = "RESERVED"
    ALLOCATED = "ALLOCATED"
    AVAILABLE = "AVAILABLE"
    UNKNOWN = "UNKNOWN"

class SourceType(str, Enum):
    DEALER = "DEALER"
    REGIONAL_DEPOT = "REGIONAL_DEPOT"
    CENTRAL_DEPOT = "CENTRAL_DEPOT"
    REMAN_FACILITY = "REMAN_FACILITY"

class SourceAvailabilityQuery(BaseModel):
    part_number: str
    quantity: int
    destination_branch_id: str
    customer_id: str
    machine_context: Optional[str] = None
    preferred_sources: Optional[List[str]] = None

class SourceInventoryItem(BaseModel):
    source_id: str
    source_name: str
    source_type: SourceType
    location_id: str
    on_hand_qty: int = 0
    reserved_qty: int = 0
    allocated_qty: int = 0
    available_qty: int = 0
    status: InventoryStatus = InventoryStatus.UNKNOWN
    inventory_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: str = "SYSTEM"
    is_stale: bool = False

class AvailabilityResponse(BaseModel):
    part_number: str
    requested_qty: int
    overall_status: str  # AVAILABLE, PARTIAL, UNAVAILABLE, UNKNOWN
    total_available_qty: int
    sources: List[SourceInventoryItem]
    reman_alternative_available: bool = False
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    freshness_ttl_seconds: int = 3600

class InventoryProvider(ABC):
    @abstractmethod
    def get_availability(self, query: SourceAvailabilityQuery) -> List[SourceInventoryItem]:
        """Fetch inventory availability from external or internal sources"""
        pass
