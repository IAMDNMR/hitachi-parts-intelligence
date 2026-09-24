"""
backend/app/integrations/adapters/osrm_adapter.py

Phase 9 OSRM (Open Source Routing Machine) European Road Route Adapter.
Source reference: OpenStreetMap contributors / Project OSRM.

Computes actual European road transit distances and driving times between
the Hitachi European Parts Centre (Oosterhout, Netherlands) and certified
European dealer branches.

Features:
- Connects to public European OSRM endpoint:
  http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false
- Strict 2.0s timeout to protect backend SLAs.
- Deterministic Haversine + road winding factor (1.30) fallback if offline or unreachable.
- Never crashes or raises exceptions on network failure.
"""

import math
import time
from typing import Any, Dict, List, Tuple

import httpx

from app.integrations.contracts.routing import (
    RouteOption,
    RouteQuery,
    RoutingProvider,
)
from app.logging_config.logger import logger

# Canonical HCME European Coordinates Dictionary
KNOWN_COORDINATES: Dict[str, Tuple[float, float]] = {
    # Central Depot
    "DEPOT-OOSTERHOUT": (51.6431, 4.8569),
    "SRC-050": (51.6431, 4.8569),
    "NL-OOST-EPC": (51.6431, 4.8569),
    "OOSTERHOUT": (51.6431, 4.8569),
    # Regional Depots
    "REGIONAL-DEPOT-AMS": (52.3676, 4.9041),
    "DEPOT-AMSTERDAM": (52.3676, 4.9041),
    "AMS": (52.3676, 4.9041),
    "DEPOT-ROTTERDAM": (51.9244, 4.4777),
    "REMAN-FACILITY-NL": (51.4416, 5.4697),
    # Dealership Hubs
    "DLR-001": (51.6431, 4.8569),    # Oosterhout, NL
    "DLR-019": (48.1351, 11.5820),   # Munich, DE
    "DEALER-DEPOT-MUNICH": (48.1351, 11.5820),
    "DLR-042": (48.8566, 2.3522),    # Paris, FR
    "DLR-088": (45.4642, 9.1900),    # Milan, IT
    "ANTWERP": (51.2194, 4.4025),    # Antwerp, BE
    "HAMBURG": (53.5511, 9.9937),    # Hamburg, DE
    "LYON": (45.7640, 4.8357),       # Lyon, FR
    "MADRID": (40.4168, -3.7038),    # Madrid, ES
    "WARSAW": (52.2297, 21.0122),    # Warsaw, PL
}

DEFAULT_ORIGIN_COORDS = (51.6431, 4.8569)   # Oosterhout EPC
DEFAULT_DEST_COORDS = (48.1351, 11.5820)    # Munich Hub


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in km."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


class OSRMRouteAdapter(RoutingProvider):
    """
    Concrete adapter calculating European driving routes via OSRM public service
    with robust Haversine fallback and 2.0s network timeout.
    """

    def __init__(self, base_url: str = "http://router.project-osrm.org/route/v1/driving"):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = 2.0

    def _resolve_coordinates(self, location_id: str, default: Tuple[float, float]) -> Tuple[float, float]:
        loc_clean = location_id.strip().upper()
        if loc_clean in KNOWN_COORDINATES:
            return KNOWN_COORDINATES[loc_clean]

        for k, coords in KNOWN_COORDINATES.items():
            if k in loc_clean:
                return coords

        return default

    def calculate_route_metrics(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> Dict[str, Any]:
        """
        Query OSRM API or fall back to Haversine. Never raises network exceptions.
        """
        start_time = time.perf_counter()
        url = f"{self.base_url}/{origin_lon:.6f},{origin_lat:.6f};{dest_lon:.6f},{dest_lat:.6f}?overview=false"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.get(url)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "Ok" and data.get("routes"):
                        route0 = data["routes"][0]
                        distance_km = round(route0.get("distance", 0.0) / 1000.0, 2)
                        duration_hours = round(route0.get("duration", 0.0) / 3600.0, 2)
                        return {
                            "distance_km": distance_km,
                            "duration_hours": duration_hours,
                            "is_live_osrm": True,
                            "latency_ms": latency_ms,
                            "status": "ACTIVE",
                        }
        except Exception as e:
            logger.debug(f"OSRM request failed ({e}), using Haversine calculation.")

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        crow_fly = haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
        road_km = round(crow_fly * 1.30, 2)  # European winding factor
        duration_hours = round(road_km / 70.0, 2)  # Avg truck/van highway speed 70 km/h

        return {
            "distance_km": road_km,
            "duration_hours": duration_hours,
            "is_live_osrm": False,
            "latency_ms": latency_ms,
            "status": "FALLBACK",
        }

    def find_routes(self, query: RouteQuery) -> List[RouteOption]:
        orig_lat, orig_lon = self._resolve_coordinates(query.origin_location_id, DEFAULT_ORIGIN_COORDS)
        dest_lat, dest_lon = self._resolve_coordinates(query.destination_branch_id, DEFAULT_DEST_COORDS)

        # Same location / local pickup
        if query.origin_location_id.upper() == query.destination_branch_id.upper() or (
            abs(orig_lat - dest_lat) < 0.01 and abs(orig_lon - dest_lon) < 0.01
        ):
            return [
                RouteOption(
                    route_id=f"osrm-local-{query.origin_location_id}-{query.destination_branch_id}",
                    origin_location_id=query.origin_location_id,
                    destination_branch_id=query.destination_branch_id,
                    transport_mode="INTERNAL_TRANSFER",
                    carrier_code="DEALER_FLEET",
                    service_level="SAME_DAY",
                    estimated_transit_days=0,
                    is_confirmed=True,
                )
            ]

        metrics = self.calculate_route_metrics(orig_lat, orig_lon, dest_lat, dest_lon)
        hours = metrics["duration_hours"]

        if hours <= 4.0:
            transit_days = 1
        elif hours <= 14.0:
            transit_days = 1
        elif hours <= 28.0:
            transit_days = 2
        else:
            transit_days = max(2, math.ceil(hours / 14.0))

        is_confirmed = metrics["is_live_osrm"]

        routes: List[RouteOption] = [
            RouteOption(
                route_id=f"osrm-road-std-{query.origin_location_id}-{query.destination_branch_id}",
                origin_location_id=query.origin_location_id,
                destination_branch_id=query.destination_branch_id,
                transport_mode="ROAD",
                carrier_code="OSRM_ROAD_FREIGHT",
                service_level="STANDARD",
                estimated_transit_days=transit_days,
                is_confirmed=is_confirmed,
            ),
            RouteOption(
                route_id=f"osrm-courier-exp-{query.origin_location_id}-{query.destination_branch_id}",
                origin_location_id=query.origin_location_id,
                destination_branch_id=query.destination_branch_id,
                transport_mode="COURIER",
                carrier_code="DHL_EXPRESS",
                service_level="EXPRESS",
                estimated_transit_days=max(1, transit_days - 1),
                is_confirmed=is_confirmed,
            ),
        ]

        return routes
