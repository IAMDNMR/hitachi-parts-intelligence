"""
backend/app/modules/transport/rate_card.py

Deterministic European Rate Card and Distance Band Configuration.
Governs synthetic freight options across ROAD, RAIL, AIR, and INTERNAL_TRANSFER.
"""

from typing import Dict, List, NamedTuple, Optional
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
    mode: TransportMode
    service_level: ServiceLevel
    display_name: str
    carrier_label: str
    base_cost: float
    distance_cost_by_band: Dict[DistanceBandEnum, float]
    service_level_cost_by_band: Dict[DistanceBandEnum, float]
    transit_days_by_band: Dict[DistanceBandEnum, int]
    cutoff_time: str
    highlight_tag: Optional[str] = None


# Mode eligibility per band per audit §6 & §8:
# Band 1: Road Standard, Road Express, (Internal Transfer where applicable)
# Band 2: Road Standard, Road Express
# Band 3: Road Standard, Road Express, Rail Standard
# Band 4: Road Standard, Road Express, Rail Standard, Air Express
# Band 5: Road Standard, Road Express, Rail Standard, Air Express
# Band 6: Road Standard, Air Express

RATE_SPECS: List[OptionSpec] = [
    # 1. Road Standard (Available in all bands 1-6)
    OptionSpec(
        mode=TransportMode.ROAD,
        service_level=ServiceLevel.STANDARD,
        display_name="Road Freight Standard",
        carrier_label="European Road Logistics Partner · Demo",
        base_cost=25.0,
        distance_cost_by_band={
            DistanceBandEnum.BAND_1: 10.0,
            DistanceBandEnum.BAND_2: 20.0,
            DistanceBandEnum.BAND_3: 35.0,
            DistanceBandEnum.BAND_4: 55.0,
            DistanceBandEnum.BAND_5: 80.0,
            DistanceBandEnum.BAND_6: 120.0,
        },
        service_level_cost_by_band={b: 0.0 for b in DistanceBandEnum},
        transit_days_by_band={
            DistanceBandEnum.BAND_1: 1,
            DistanceBandEnum.BAND_2: 2,
            DistanceBandEnum.BAND_3: 3,
            DistanceBandEnum.BAND_4: 3,
            DistanceBandEnum.BAND_5: 4,
            DistanceBandEnum.BAND_6: 5,
        },
        cutoff_time="14:00 CET",
        highlight_tag="LOWEST COST",
    ),
    # 2. Road Express (Available in bands 1-5)
    OptionSpec(
        mode=TransportMode.ROAD,
        service_level=ServiceLevel.EXPRESS,
        display_name="Road Courier Express",
        carrier_label="European Express Logistics Partner · Demo",
        base_cost=35.0,
        distance_cost_by_band={
            DistanceBandEnum.BAND_1: 15.0,
            DistanceBandEnum.BAND_2: 30.0,
            DistanceBandEnum.BAND_3: 50.0,
            DistanceBandEnum.BAND_4: 75.0,
            DistanceBandEnum.BAND_5: 110.0,
            DistanceBandEnum.BAND_6: 160.0,
        },
        service_level_cost_by_band={
            DistanceBandEnum.BAND_1: 15.0,
            DistanceBandEnum.BAND_2: 25.0,
            DistanceBandEnum.BAND_3: 35.0,
            DistanceBandEnum.BAND_4: 45.0,
            DistanceBandEnum.BAND_5: 55.0,
            DistanceBandEnum.BAND_6: 65.0,
        },
        transit_days_by_band={
            DistanceBandEnum.BAND_1: 1,
            DistanceBandEnum.BAND_2: 1,
            DistanceBandEnum.BAND_3: 2,
            DistanceBandEnum.BAND_4: 2,
            DistanceBandEnum.BAND_5: 2,
            DistanceBandEnum.BAND_6: 3,
        },
        cutoff_time="17:00 CET",
        highlight_tag=None,
    ),
    # 3. Rail Standard (Available in bands 3, 4, 5 — sustainable intermodal)
    OptionSpec(
        mode=TransportMode.RAIL,
        service_level=ServiceLevel.STANDARD,
        display_name="Rail Intermodal Freight",
        carrier_label="European Rail Logistics Partner · Demo",
        base_cost=20.0,
        distance_cost_by_band={
            DistanceBandEnum.BAND_3: 25.0,
            DistanceBandEnum.BAND_4: 40.0,
            DistanceBandEnum.BAND_5: 60.0,
        },
        service_level_cost_by_band={
            DistanceBandEnum.BAND_3: 0.0,
            DistanceBandEnum.BAND_4: 0.0,
            DistanceBandEnum.BAND_5: 0.0,
        },
        transit_days_by_band={
            DistanceBandEnum.BAND_3: 3,
            DistanceBandEnum.BAND_4: 4,
            DistanceBandEnum.BAND_5: 5,
        },
        cutoff_time="12:00 CET",
        highlight_tag=None,
    ),
    # 4. Air Express (Available in bands 4, 5, 6 — emergency machine-down)
    OptionSpec(
        mode=TransportMode.AIR,
        service_level=ServiceLevel.EXPRESS,
        display_name="Air Priority Express",
        carrier_label="European Air Freight Partner · Demo",
        base_cost=75.0,
        distance_cost_by_band={
            DistanceBandEnum.BAND_4: 65.0,
            DistanceBandEnum.BAND_5: 90.0,
            DistanceBandEnum.BAND_6: 125.0,
        },
        service_level_cost_by_band={
            DistanceBandEnum.BAND_4: 45.0,
            DistanceBandEnum.BAND_5: 55.0,
            DistanceBandEnum.BAND_6: 65.0,
        },
        transit_days_by_band={
            DistanceBandEnum.BAND_4: 1,
            DistanceBandEnum.BAND_5: 1,
            DistanceBandEnum.BAND_6: 2,
        },
        cutoff_time="18:30 CET",
        highlight_tag="FASTEST",
    ),
]
