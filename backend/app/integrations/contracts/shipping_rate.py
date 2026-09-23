from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class ShippingRateQuery(BaseModel):
    carrier_code: str
    service_level: str
    origin_location_id: str
    destination_branch_id: str
    weight_kg: Optional[float] = None
    quantity: int = 1

class ShippingRate(BaseModel):
    carrier_code: str
    service_level: str
    shipping_cost: float
    currency: str = "EUR"
    estimated_delivery_days: int
    is_confirmed: bool = False

class ShippingRateProvider(ABC):
    @abstractmethod
    def get_rate(self, query: ShippingRateQuery) -> Optional[ShippingRate]:
        """Return shipping rate estimate for a carrier, route, and package details."""
        pass
