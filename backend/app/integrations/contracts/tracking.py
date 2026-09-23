"""
backend/app/integrations/contracts/tracking.py

Phase 7 Tracking Provider Contract.

Defines the abstract interface and Pydantic models for tracking queries and
event ingestion. Follows the established provider pattern from Phase 5/6.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class TrackingEventPayload(BaseModel):
    event_type: str = Field(..., description="DISPATCHED / IN_TRANSIT / EXCEPTION / DELIVERED")
    timestamp: str = Field(..., description="Timestamp of the event")
    location: Optional[str] = Field(None, description="Location reported by carrier (e.g. Oosterhout Hub, NL)")
    description: str = Field(..., description="Carrier status description")


class TrackingQuery(BaseModel):
    tracking_number: str = Field(..., description="Tracking reference issued by carrier")


class TrackingResult(BaseModel):
    tracking_number: str
    carrier: str
    status: str = Field(..., description="CREATED / DISPATCHED / IN_TRANSIT / DELIVERED / EXCEPTION")
    estimated_delivery: Optional[str] = None
    events: List[TrackingEventPayload] = Field(default_factory=list)
    integration_status: str = Field("NOT_CONNECTED", description="Connection status of real carrier API")


class TrackingProvider(ABC):
    """
    Authoritative abstraction over carrier tracking telemetry.
    Supports polling or webhook-driven event recording.
    """

    @abstractmethod
    def get_tracking(self, query: TrackingQuery) -> TrackingResult:
        """Fetch tracking events and current status for a given tracking reference."""
        pass
