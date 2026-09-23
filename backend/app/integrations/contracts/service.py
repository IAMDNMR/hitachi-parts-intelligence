"""
backend/app/integrations/contracts/service.py

Phase 9 Service Provider Contract.

Defines the abstract interface and Pydantic models for dealer workshop,
field service scheduling, and maintenance work order integration.
Follows the established provider pattern from Phase 5/6/7.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ServiceScheduleRequest(BaseModel):
    order_id: str = Field(..., description="ID of the associated order")
    dealer_id: str = Field(..., description="Certified dealer branch ID")
    part_number: str = Field(..., description="Part number to install or service")
    machine_context: Optional[str] = Field(None, description="Target machine model or serial number")
    service_type: str = Field("PARTS_INSTALLATION", description="Service job type")
    notes: Optional[str] = Field(None, description="Customer or dispatch notes")


class ServiceScheduleResult(BaseModel):
    success: bool = Field(..., description="True if service successfully scheduled")
    status: str = Field("OPEN", description="Initial status of service job")
    external_job_id: Optional[str] = Field(None, description="External DMS/ConSite work order reference")
    message: str = Field(..., description="Provider status / diagnostic message")
    data_source: str = Field("SYNTHETIC_DEMO", description="Source system provenance")


class ServiceStatusResult(BaseModel):
    external_job_id: str = Field(..., description="External work order reference")
    status: str = Field(..., description="Current status in external system")
    notes: Optional[str] = Field(None, description="Latest status notes")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Milestone event timeline")
    integration_status: str = Field("NOT_CONNECTED", description="Live connection state")


class ServiceProvider(ABC):
    """
    Authoritative abstraction over OEM field service and dealership DMS scheduling.
    When no real DMS is connected, falls back cleanly to TestServiceProvider.
    """

    @abstractmethod
    def schedule_service(self, request: ServiceScheduleRequest) -> ServiceScheduleResult:
        """Schedule a service job with the dealer DMS or field service portal."""
        pass

    @abstractmethod
    def get_service_status(self, external_job_id: str) -> ServiceStatusResult:
        """Query dealer DMS for latest work order status and event updates."""
        pass
