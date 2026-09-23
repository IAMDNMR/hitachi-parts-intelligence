"""
backend/app/integrations/contracts/shipment.py

Phase 7 Shipment Provider Contract.

Defines the abstract interface and Pydantic models for logistics / carrier
shipment dispatch integration. Follows the established provider pattern from
Phase 5/6 (InventoryProvider, OrderProvider, PricingProvider, RoutingProvider).
"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field


class ShipmentCreationRequest(BaseModel):
    order_id: str = Field(..., description="ID of the accepted order to ship")
    part_number: str = Field(..., description="Canonical part number")
    quantity: int = Field(..., ge=1, description="Quantity being shipped")
    origin_source_id: str = Field(..., description="Depot or supplier source ID")
    destination_branch_id: str = Field(..., description="Receiving DealerBranch ID")
    service_tier: str = Field("STANDARD", description="Selected logistics service level (STANDARD / EXPEDITED)")


class ShipmentCreationResult(BaseModel):
    status: str = Field(..., description="SUCCESS / FAILED / NOT_CONNECTED")
    carrier: str = Field(..., description="Name of carrier or logistics system")
    tracking_number: Optional[str] = Field(None, description="Tracking reference issued by carrier")
    estimated_delivery: Optional[str] = Field(None, description="Initial estimated delivery ISO-8601 string or date")
    message: str = Field(..., description="Provider status / diagnostic message")


class ShipmentProvider(ABC):
    """
    Authoritative abstraction over logistics / carrier shipment creation.
    Per HCME architecture rules, when no real HCME carrier integration is
    connected, the provider remains NOT_CONNECTED and marks test data accordingly.
    """

    @abstractmethod
    def create_shipment(self, request: ShipmentCreationRequest) -> ShipmentCreationResult:
        """Create and register a shipment with the carrier system."""
        pass
