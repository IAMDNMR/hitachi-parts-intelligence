from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class PricingQuery(BaseModel):
    part_number: str
    quantity: int
    customer_id: Optional[str] = None


class PriceQuote(BaseModel):
    part_number: str
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    status: str = "NOT_AVAILABLE"  # NOT_AVAILABLE | CONFIRMED
    is_confirmed: bool = False


class PricingProvider(ABC):
    @abstractmethod
    def get_price(self, query: PricingQuery) -> PriceQuote:
        """Return an authoritative price quote, or NOT_AVAILABLE if none is connected."""
        pass
