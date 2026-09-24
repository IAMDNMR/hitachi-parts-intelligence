"""
backend/app/integrations/adapters/carrier_base.py

Base adapter interface for logistics carriers and Transport Management Systems (TMS).
Enables seamless multi-carrier pluggability (Neovia TMS, DHL Express/Freight, DB Schenker, TNT).
"""

from abc import ABC, abstractmethod

from app.integrations.contracts.shipment import ShipmentCreationRequest, ShipmentCreationResult
from app.integrations.contracts.tracking import TrackingQuery, TrackingResult


class CarrierAdapter(ABC):
    """
    Abstract adapter for a specific logistics provider or TMS interface.
    Each adapter encapsulates transport protocol (REST, SOAP, EDI, Webhook)
    and authentication, while exposing standardized contract methods.
    """

    @property
    @abstractmethod
    def carrier_name(self) -> str:
        """Name of the carrier/TMS platform."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True only when valid production credentials are configured and connectivity is verified."""
        pass

    @abstractmethod
    def dispatch_shipment(self, request: ShipmentCreationRequest) -> ShipmentCreationResult:
        """Submit shipment order to carrier system."""
        pass

    @abstractmethod
    def track_shipment(self, query: TrackingQuery) -> TrackingResult:
        """Query carrier tracking API for latest events."""
        pass
