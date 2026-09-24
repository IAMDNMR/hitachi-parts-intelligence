"""
backend/app/modules/transport/rate_card.py

Deterministic European Rate Card and Distance Band Configuration.
Governs synthetic freight options across ROAD, RAIL, AIR, and INTERNAL_TRANSFER.
"""

from typing import Dict, List, NamedTuple, Optional, Tuple
from app.modules.transport.models import DistanceBandEnum, TransportMode, ServiceLevel


class DistanceBandConfig(NamedTuple):
    band_id: DistanceBandEnum
    name: str
    min_km: float
    max_km: Optional[float]
    description: str


DISTANCE_BANDS: Dict[DistanceBandEnum, DistanceBandConfig] = {
    DistanceBandEnum.BAND_1: DistanceBandConfig(
        band_id=DistanceBandEnum.BAND_1,
        name="Local European Region (0–<100 km)",
        min_km=0.0,
        max_km=100.0,
        description="Local Netherlands, Antwerp, Brussels, North Rhine border",
    ),
    DistanceBandEnum.BAND_2: DistanceBandConfig(
        band_id=DistanceBandEnum.BAND_2,
        name="Cross-Border Western Europe (100–<300 km)",
        min_km=100.0,
        max_km=300.0,
        description="BeNeLux, Ruhrgebiet, Frankfurt, Cologne, Lille",
    ),
    DistanceBandEnum.BAND_3: DistanceBandConfig(
        band_id=DistanceBandEnum.BAND_3,
        name="Central European Corridor (300–<600 km)",
        min_km=300.0,
        max_km=600.0,
        description="Central Germany, Paris / Northern France, Hamburg, Stuttgart",
    ),
    DistanceBandEnum.BAND_4: DistanceBandConfig(
        band_id=DistanceBandEnum.BAND_4,
        name="Major European Freight Trunk (600–<1,000 km)",
        min_km=600.0,
        max_km=1000.0,
        description="Southern Germany (Munich), Austria, Switzerland, Lyon, London",
    ),
    DistanceBandEnum.BAND_5: DistanceBandConfig(
        band_id=DistanceBandEnum.BAND_5,
        name="Extended Pan-European Route (1,000–<1,500 km)",
        min_km=1000.0,
        max_km=1500.0,
        description="Northern Italy, Poland, Czechia, Scotland, Pyrenees",
    ),
    DistanceBandEnum.BAND_6: DistanceBandConfig(
        band_id=DistanceBandEnum.BAND_6,
        name="Peripheral European Transit (1,500+ km)",
        min_km=1500.0,
        max_km=None,
        description="Spain, Portugal, Southern Italy, Scandinavia, Baltic States, Balkans",
    ),
}


def resolve_distance_band(distance_km: float) -> DistanceBandConfig:
    d = max(0.0, distance_km)
    if d < 100.0:
        return DISTANCE_BANDS[DistanceBandEnum.BAND_1]
    elif d < 300.0:
        return DISTANCE_BANDS[DistanceBandEnum.BAND_2]
    elif d < 600.0:
        return DISTANCE_BANDS[DistanceBandEnum.BAND_3]
    elif d < 1000.0:
        return DISTANCE_BANDS[DistanceBandEnum.BAND_4]
    elif d < 1500.0:
        return DISTANCE_BANDS[DistanceBandEnum.BAND_5]
    else:
        return DISTANCE_BANDS[DistanceBandEnum.BAND_6]


class OptionSpec(NamedTuple):
    """Synthetic rate model. Cost = base (handling) + per_km x distance + service surcharge; transit comes from distance steps.
    ROAD/RAIL are priced on the estimated road distance, AIR on the straight-line distance."""
    mode: TransportMode
    service_level: ServiceLevel
    display_name: str
    carrier_label: str
    base_cost: float
    per_km: float
    service_surcharge: float
    transit_steps: List[Tuple[float, int]]  # (up to this many km, business days); the last step is open-ended
    cutoff_time: str
    highlight_tag: Optional[str] = None


def transit_days_for(spec: OptionSpec, km: float) -> int:
    for max_km, days in spec.transit_steps:
        if km <= max_km:
            return days
    return spec.transit_steps[-1][1]


def option_cost(spec: OptionSpec, km: float) -> Tuple[float, float, float, float]:
    """(base, distance cost, service surcharge, total) for a distance in km."""
    dist = round(spec.per_km * max(km, 0.0), 2)
    return spec.base_cost, dist, spec.service_surcharge, round(spec.base_cost + dist + spec.service_surcharge, 2)


# Demonstration rates only (SYNTHETIC_DEMO), set to be plausible for European pallet / air freight - not carrier quotes.
# Rule kept by the engine: paying more always buys a faster delivery. An option that costs more than another without being faster
# (e.g. air on a short route where express road is already next-day) is not offered.
RATE_SPECS: List[OptionSpec] = [
    OptionSpec(TransportMode.ROAD, ServiceLevel.STANDARD, "Road Freight Standard", "European Road Logistics Partner · Demo",
               base_cost=40.0, per_km=0.60, service_surcharge=0.0,
               transit_steps=[(300, 2), (700, 3), (1200, 4), (float("inf"), 5)], cutoff_time="14:00 CET", highlight_tag=None),
    OptionSpec(TransportMode.ROAD, ServiceLevel.EXPRESS, "Road Courier Express", "European Express Logistics Partner · Demo",
               base_cost=60.0, per_km=1.10, service_surcharge=25.0,
               transit_steps=[(700, 1), (1500, 2), (float("inf"), 3)], cutoff_time="17:00 CET", highlight_tag=None),
    OptionSpec(TransportMode.RAIL, ServiceLevel.STANDARD, "Rail Intermodal Freight", "European Rail Logistics Partner · Demo",
               base_cost=30.0, per_km=0.30, service_surcharge=0.0,
               transit_steps=[(300, 3), (700, 4), (1200, 5), (float("inf"), 6)], cutoff_time="12:00 CET", highlight_tag=None),
    OptionSpec(TransportMode.AIR, ServiceLevel.EXPRESS, "Air Freight Express", "European Air Freight Partner · Demo",
               base_cost=250.0, per_km=1.00, service_surcharge=60.0,
               transit_steps=[(1500, 1), (float("inf"), 2)], cutoff_time="18:30 CET", highlight_tag=None),
]
