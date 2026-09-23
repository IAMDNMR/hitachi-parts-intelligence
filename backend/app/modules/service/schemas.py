"""
backend/app/modules/service/schemas.py

Pydantic models for the Phase 8 Dealer & Service domain.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ServiceJobCreateRequest(BaseModel):
    order_id: str = Field(..., description="ID of the accepted order requiring service/installation")
    service_type: str = Field("PARTS_INSTALLATION", description="PARTS_INSTALLATION / PREVENTIVE_MAINTENANCE / EMERGENCY_REPAIR")
    technician_role: Optional[str] = Field("CERTIFIED_SERVICE_TECHNICIAN", description="Technician role or qualification")
    notes: Optional[str] = Field(None, description="Initial service intake notes")


class ServiceEventCreate(BaseModel):
    event_type: str = Field(..., description="PART_RECEIVED / IN_PROGRESS / PART_INSTALLED / COMPLETED / CANCELLED")
    description: str = Field(..., description="Detailed description of the service milestone")
    technician_role: Optional[str] = Field(None, description="Technician role or actor")
    notes: Optional[str] = Field(None, description="Additional workshop or inspection notes")


class ServiceEventResponse(BaseModel):
    id: str
    event_type: str
    description: str
    technician_role: Optional[str] = None
    notes: Optional[str] = None
    timestamp: str
    synthetic: bool = True
    data_source: Optional[str] = None


class ServiceJobResponse(BaseModel):
    service_job_id: str
    order_id: str
    shipment_id: Optional[str] = None
    dealer_id: str
    dealer_name: Optional[str] = None
    dealer_city: Optional[str] = None
    dealer_country: Optional[str] = None
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    machine_id: Optional[str] = None
    machine_model: Optional[str] = None
    status: str
    service_type: str
    work_order_number: Optional[str] = None
    notes: Optional[str] = None
    received_at: Optional[str] = None
    started_at: Optional[str] = None
    installed_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    cancel_reason: Optional[str] = None
    synthetic: bool = True
    data_source: Optional[str] = None
    provenance: Optional[str] = None
    events: List[ServiceEventResponse] = Field(default_factory=list)


class ServiceJourneyTraceResponse(BaseModel):
    service_job_id: str
    status: str
    part: Dict[str, Any]
    machine: Optional[Dict[str, Any]] = None
    dealer: Dict[str, Any]
    order: Dict[str, Any]
    shipment: Optional[Dict[str, Any]] = None
    fulfilment_request: Optional[Dict[str, Any]] = None
    timeline_milestones: List[Dict[str, Any]] = Field(default_factory=list)
    is_closed: bool = False
    closed_at: Optional[str] = None
    synthetic: bool = True
    data_source: Optional[str] = None
