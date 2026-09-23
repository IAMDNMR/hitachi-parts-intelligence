"""
backend/app/modules/transport/engine.py

Core European Transport Engine.
Calculates straight-line distances from real coordinates, assigns distance bands,
evaluates eligible multi-modal options, and computes deterministic costs and ETAs.
"""

from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Tuple

from app.modules.transport.models import (
    DistanceBandEnum,
    LocationInfo,
    ServiceLevel,
    TransportComparisonResponse,
    TransportMode,
    TransportOptionDTO,
)
from app.modules.transport.rate_card import (
    DISTANCE_BANDS,
    RATE_SPECS,
    resolve_distance_band,
)

# Canonical Depot Coordinate reference: Hitachi European Parts Centre, Oosterhout (NL)
OOSTERHOUT_LAT = 51.6431
OOSTERHOUT_LON = 4.8569


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance between two points on Earth in kilometres."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


def calculate_delivery_date(start_dt: datetime, business_days: int) -> str:
    """
    Calculate estimated delivery date skipping weekends (Saturday & Sunday).
    Returns ISO 8601 date string YYYY-MM-DD.
    """
    cur = start_dt
    added = 0
    days_to_add = max(1, business_days)

    while added < days_to_add:
        cur += timedelta(days=1)
        # 5 is Saturday, 6 is Sunday
        if cur.weekday() < 5:
            added += 1

    return cur.strftime("%Y-%m-%d")


def resolve_location_info(session, location_id: str) -> LocationInfo:
    """
    Resolve coordinates and display names for a location ID (Depot or DealerBranch).
    """
    loc_clean = location_id.strip()

    # Central Depot
    if "DEPOT" in loc_clean.upper() or "OOSTERHOUT" in loc_clean.upper() or loc_clean == "NL-OOST-EPC":
        row = session.run(
            "MATCH (d:Depot {depot_id: 'DEPOT-OOSTERHOUT'}) RETURN d.depot_id as id, d.name as name, d.city as city, d.country as country, d.latitude as lat, d.longitude as lon"
        ).single()
        if row:
            return LocationInfo(
                id=row["id"] or "DEPOT-OOSTERHOUT",
                name=row["name"] or "Hitachi European Parts Centre",
                city=row["city"] or "Oosterhout",
                country=row["country"] or "NL",
                latitude=float(row["lat"]) if row["lat"] is not None else OOSTERHOUT_LAT,
                longitude=float(row["lon"]) if row["lon"] is not None else OOSTERHOUT_LON,
            )
        return LocationInfo(
            id="DEPOT-OOSTERHOUT",
            name="Hitachi European Parts Centre",
            city="Oosterhout",
            country="NL",
            latitude=OOSTERHOUT_LAT,
            longitude=OOSTERHOUT_LON,
        )

    # Dealer branch lookup
    row = session.run(
        """
        MATCH (d:DealerBranch)
        WHERE d.dealer_id = $id OR toUpper(d.dealer_name) = toUpper($id)
        RETURN d.dealer_id as id, d.dealer_name as name, d.city as city, d.country as country,
               d.latitude as lat, d.longitude as lon
        LIMIT 1
        """,
        {"id": loc_clean},
    ).single()

    if row:
        lat = float(row["lat"]) if row["lat"] is not None else None
        lon = float(row["lon"]) if row["lon"] is not None else None
        return LocationInfo(
            id=row["id"],
            name=row["name"] or row["id"],
            city=row["city"] or None,
            country=row["country"] or "Europe",
            latitude=lat,
            longitude=lon,
        )

    # Fallback placeholder if not found
    return LocationInfo(
        id=loc_clean,
        name=loc_clean,
        city=None,
        country="Europe",
        latitude=None,
        longitude=None,
    )


def compute_transport_comparison(
    session,
    origin_id: str,
    destination_branch_id: str,
    part_number: str,
    quantity: int = 1,
    selected_option_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> TransportComparisonResponse:
    """
    Compute candidate multi-modal European transport options based on verified GPS coordinates,
    distance bands, and deterministic rate cards.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    origin = resolve_location_info(session, origin_id)
    destination = resolve_location_info(session, destination_branch_id)

    orig_lat = origin.latitude if origin.latitude is not None else OOSTERHOUT_LAT
    orig_lon = origin.longitude if origin.longitude is not None else OOSTERHOUT_LON
    dest_lat = destination.latitude if destination.latitude is not None else OOSTERHOUT_LAT
    dest_lon = destination.longitude if destination.longitude is not None else OOSTERHOUT_LON

    straight_line_km = round(haversine_distance_km(orig_lat, orig_lon, dest_lat, dest_lon), 2)
    # European highway winding factor (1.25x straight-line distance)
    estimated_road_km = round(straight_line_km * 1.25, 2)

    band_cfg = resolve_distance_band(straight_line_km)
    band_id = band_cfg.band_id

    options: List[TransportOptionDTO] = []

    # Check for same branch / internal transfer (< 10km)
    is_local = straight_line_km < 10.0 or origin.id == destination.id

    if is_local:
        opt_id = f"TR-LOCAL-{origin.id}-{destination.id}"
        options.append(
            TransportOptionDTO(
                transport_option_id=opt_id,
                mode=TransportMode.INTERNAL_TRANSFER,
                service_level=ServiceLevel.STANDARD,
                display_name="Dealer Local Pickup / Transfer",
                carrier_label="Dealer Internal Fleet · Demo",
                transit_days=0,
                estimated_delivery_date=now.strftime("%Y-%m-%d"),
                dispatch_cutoff_time="16:00 CET",
                currency="EUR",
                base_cost=10.0,
                distance_cost=0.0,
                service_level_cost=0.0,
                total_cost=10.0,
                data_class="SYNTHETIC_DEMO",
                provenance_note="Local dealer transfer calculated from co-located inventory.",
                highlight_tag="LOWEST COST",
                is_selected=(selected_option_id == opt_id),
            )
        )

    # Evaluate options from RATE_SPECS for this distance band
    for spec in RATE_SPECS:
        if band_id not in spec.distance_cost_by_band:
            continue

        opt_id = f"TR-{spec.mode.value}-{spec.service_level.value}-{band_id.value}"
        base = spec.base_cost
        dist_cost = spec.distance_cost_by_band[band_id]
        srv_cost = spec.service_level_cost_by_band.get(band_id, 0.0)
        total = round(base + dist_cost + srv_cost, 2)
        transit_days = spec.transit_days_by_band[band_id]
        delivery_date = calculate_delivery_date(now, transit_days)

        options.append(
            TransportOptionDTO(
                transport_option_id=opt_id,
                mode=spec.mode,
                service_level=spec.service_level,
                display_name=spec.display_name,
                carrier_label=spec.carrier_label,
                transit_days=transit_days,
                estimated_delivery_date=delivery_date,
                dispatch_cutoff_time=spec.cutoff_time,
                currency="EUR",
                base_cost=base,
                distance_cost=dist_cost,
                service_level_cost=srv_cost,
                total_cost=total,
                data_class="SYNTHETIC_DEMO",
                provenance_note="Calculated from straight-line distance using synthetic European freight rate model.",
                highlight_tag=spec.highlight_tag,
                is_selected=(selected_option_id == opt_id),
            )
        )

    # Refine highlight tags dynamically across options:
    # 1. Cheapest gets "LOWEST COST"
    if options:
        min_cost = min(o.total_cost for o in options)
        min_transit = min(o.transit_days for o in options)
        for opt in options:
            if opt.total_cost == min_cost and not opt.highlight_tag:
                opt.highlight_tag = "LOWEST COST"
            elif opt.transit_days == min_transit and opt.service_level == ServiceLevel.EXPRESS:
                opt.highlight_tag = "FASTEST"

    return TransportComparisonResponse(
        origin=origin,
        destination=destination,
        straight_line_distance_km=straight_line_km,
        estimated_road_distance_km=estimated_road_km,
        distance_band=band_id.value,
        distance_band_name=band_cfg.name,
        options=options,
        provenance={
            "distance": "DERIVED · STRAIGHT-LINE DISTANCE",
            "rates": "SYNTHETIC_DEMO",
            "carrier_connectivity": "NOT_CONNECTED",
        },
    )
