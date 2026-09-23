"""
backend/app/modules/transport/models.py

Pydantic models and schemas for European Transport Options engine.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TransportMode(str, Enum):
    ROAD = "ROAD"
    RAIL = "RAIL"
    AIR = "AIR"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"


class ServiceLevel(str, Enum):
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"


class DistanceBandEnum(str, Enum):
    BAND_1 = "BAND_1"  # 0 to <100 km
    BAND_2 = "BAND_2"  # 100 to <300 km
    BAND_3 = "BAND_3"  # 300 to <600 km
    BAND_4 = "BAND_4"  # 600 to <1,000 km
    BAND_5 = "BAND_5"  # 1,000 to <1,500 km
    BAND_6 = "BAND_6"  # 1,500+ km


class TransportOptionDTO(BaseModel):
    transport_option_id: str
    mode: TransportMode
    service_level: ServiceLevel
    display_name: str
    carrier_label: str
    transit_days: int
    estimated_delivery_date: str
    dispatch_cutoff_time: str
    currency: str = "EUR"
    base_cost: float
    distance_cost: float
    service_level_cost: float
    total_cost: float
    data_class: str = "SYNTHETIC_DEMO"
    provenance_note: str = (
        "Calculated from straight-line distance using synthetic European freight rate model."
    )
    highlight_tag: Optional[str] = None  # e.g. "LOWEST COST", "FASTEST"
    is_selected: bool = False


class LocationInfo(BaseModel):
    id: str
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TransportComparisonResponse(BaseModel):
    origin: LocationInfo
    destination: LocationInfo
    straight_line_distance_km: float
    estimated_road_distance_km: float
    distance_band: str
    distance_band_name: str
    options: List[TransportOptionDTO]
    provenance: Dict[str, Any]
