"""
backend/app/modules/shipment/schemas.py

Pydantic models for the Phase 7 Shipment & Tracking domain.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ShipmentCreateRequest(BaseModel):
    order_id: str = Field(..., description="ID of the accepted order to ship")
    service_tier: str = Field("STANDARD", description="STANDARD or EXPEDITED")


class ShipmentEventCreate(BaseModel):
    event_type: str = Field(..., description="DISPATCHED / IN_TRANSIT / EXCEPTION / DELIVERED")
    description: str = Field(..., description="Description of the event")
    location: Optional[str] = Field(None, description="Location of the event")


class ShipmentEventResponse(BaseModel):
    id: str
    event_type: str
    description: str
    location: Optional[str] = None
    timestamp: str
    synthetic: bool = True
    data_source: Optional[str] = None


class ShipmentResponse(BaseModel):
    shipment_id: str
    order_id: str
    status: str
    carrier: str
    tracking_number: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    destination_branch_id: Optional[str] = None
    eta: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    synthetic: bool = True
    data_source: Optional[str] = None
    provenance: Optional[str] = None
    integration_status: str = "NOT_CONNECTED"
    integration_label: str = "TEST/DEVELOPMENT — no real HCME carrier system is connected"
    events: List[ShipmentEventResponse] = Field(default_factory=list)


class PublicTrackingResponse(BaseModel):
    tracking_number: str
    shipment_id: str
    status: str
    carrier: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    eta: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    synthetic: bool = True
    integration_status: str = "NOT_CONNECTED"
    events: List[ShipmentEventResponse] = Field(default_factory=list)
