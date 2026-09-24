from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel

class RouteQuery(BaseModel):
    origin_location_id: str
    destination_branch_id: str
    part_number: str
    quantity: int

class RouteOption(BaseModel):
    route_id: str
    origin_location_id: str
    destination_branch_id: str
    transport_mode: str  # ROAD, COURIER, INTERNAL_TRANSFER, AIR, UNKNOWN
    carrier_code: str    # e.g., 'HCME_LOGISTICS', 'UNKNOWN'
    service_level: str   # 'STANDARD', 'EXPRESS', 'UNKNOWN'
    estimated_transit_days: int
    is_confirmed: bool = False

class RoutingProvider(ABC):
    @abstractmethod
    def find_routes(self, query: RouteQuery) -> List[RouteOption]:
        """Determine feasible transport routes and estimated transit time from source to destination."""
        pass
