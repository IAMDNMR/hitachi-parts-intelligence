"""
backend/tests/test_transport_engine.py

Unit and integration tests for Phase 10 European Transport Engine.
Verifies distance bands 1-6, mode eligibility, price scaling, transit times,
weekend-skipping ETA calculations, and API contracts.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.transport.engine import (
    calculate_delivery_date,
    haversine_distance_km,
    resolve_location_info,
    compute_transport_comparison,
)
from app.modules.transport.models import DistanceBandEnum, ServiceLevel, TransportMode
from app.modules.transport.rate_card import (
    DISTANCE_BANDS,
    RATE_SPECS,
    resolve_distance_band,
)

client = TestClient(app)


def test_distance_band_resolution():
    """Verify that distances map accurately to Distance Bands 1 through 6."""
    assert resolve_distance_band(45.0).band_id == DistanceBandEnum.BAND_1
    assert resolve_distance_band(99.9).band_id == DistanceBandEnum.BAND_1
    assert resolve_distance_band(100.0).band_id == DistanceBandEnum.BAND_2
    assert resolve_distance_band(250.0).band_id == DistanceBandEnum.BAND_2
    assert resolve_distance_band(300.0).band_id == DistanceBandEnum.BAND_3
    assert resolve_distance_band(550.0).band_id == DistanceBandEnum.BAND_3
    assert resolve_distance_band(600.0).band_id == DistanceBandEnum.BAND_4
    assert resolve_distance_band(850.0).band_id == DistanceBandEnum.BAND_4
    assert resolve_distance_band(1000.0).band_id == DistanceBandEnum.BAND_5
    assert resolve_distance_band(1400.0).band_id == DistanceBandEnum.BAND_5
    assert resolve_distance_band(1500.0).band_id == DistanceBandEnum.BAND_6
    assert resolve_distance_band(2500.0).band_id == DistanceBandEnum.BAND_6


def test_haversine_distance_accuracy():
    """Verify Great-Circle straight-line distance between Oosterhout and Munich."""
    # Oosterhout: 51.6431, 4.8569
    # Munich: 48.1351, 11.5820
    dist = haversine_distance_km(51.6431, 4.8569, 48.1351, 11.5820)
    # Straight-line distance is ~630 km
    assert 600.0 < dist < 660.0


def test_eta_skips_weekends():
    """Verify delivery calculation skips Saturday and Sunday."""
    # Friday 2026-09-25
    friday = datetime(2026, 9, 25, 10, 0, tzinfo=timezone.utc)
    # 1 business day from Friday is Monday 2026-09-28
    assert calculate_delivery_date(friday, 1) == "2026-09-28"
    # 2 business days from Friday is Tuesday 2026-09-29
    assert calculate_delivery_date(friday, 2) == "2026-09-29"


def test_express_costs_more_than_standard():
    """Verify that Express strictly costs more than Standard across all applicable distance bands."""
    for band_enum in DistanceBandEnum:
        road_std = next(
            (s for s in RATE_SPECS if s.mode == TransportMode.ROAD and s.service_level == ServiceLevel.STANDARD and band_enum in s.distance_cost_by_band),
            None,
        )
        road_exp = next(
            (s for s in RATE_SPECS if s.mode == TransportMode.ROAD and s.service_level == ServiceLevel.EXPRESS and band_enum in s.distance_cost_by_band),
            None,
        )
        if road_std and road_exp:
            cost_std = road_std.base_cost + road_std.distance_cost_by_band[band_enum] + road_std.service_level_cost_by_band[band_enum]
            cost_exp = road_exp.base_cost + road_exp.distance_cost_by_band[band_enum] + road_exp.service_level_cost_by_band[band_enum]
            assert cost_exp > cost_std, f"Express should cost more than Standard in {band_enum.value}"


def test_express_is_faster_or_equal_to_standard():
    """Verify that Express transit time is <= Standard transit time in all applicable distance bands."""
    for band_enum in DistanceBandEnum:
        road_std = next(
            (s for s in RATE_SPECS if s.mode == TransportMode.ROAD and s.service_level == ServiceLevel.STANDARD and band_enum in s.transit_days_by_band),
            None,
        )
        road_exp = next(
            (s for s in RATE_SPECS if s.mode == TransportMode.ROAD and s.service_level == ServiceLevel.EXPRESS and band_enum in s.transit_days_by_band),
            None,
        )
        if road_std and road_exp:
            days_std = road_std.transit_days_by_band[band_enum]
            days_exp = road_exp.transit_days_by_band[band_enum]
            assert days_exp <= days_std, f"Express should be faster or equal in {band_enum.value}"


def test_rail_lower_cost():
    """Verify Rail freight provides lower cost than Road Standard on heavy trunk routes (Bands 3, 4, 5)."""
    for band_enum in [DistanceBandEnum.BAND_3, DistanceBandEnum.BAND_4, DistanceBandEnum.BAND_5]:
        rail = next((s for s in RATE_SPECS if s.mode == TransportMode.RAIL and band_enum in s.distance_cost_by_band), None)
        road = next((s for s in RATE_SPECS if s.mode == TransportMode.ROAD and s.service_level == ServiceLevel.STANDARD and band_enum in s.distance_cost_by_band), None)
        assert rail is not None and road is not None
        cost_rail = rail.base_cost + rail.distance_cost_by_band[band_enum]
        cost_road = road.base_cost + road.distance_cost_by_band[band_enum]
        assert cost_rail < cost_road, f"Rail should cost less than Road Standard in {band_enum.value}"


def test_transport_options_api_endpoint():
    """Test the HTTP GET /api/v1/transport/options endpoint."""
    resp = client.get("/api/v1/transport/options?destination_branch_id=DLR-001&part_number=4663907&quantity=1")
    assert resp.status_code == 200
    data = resp.json()

    assert "origin" in data
    assert "destination" in data
    assert "straight_line_distance_km" in data
    assert "estimated_road_distance_km" in data
    assert "distance_band" in data
    assert "options" in data
    assert len(data["options"]) >= 2

    # Check option fields
    opt0 = data["options"][0]
    assert opt0["currency"] == "EUR"
    assert opt0["data_class"] == "SYNTHETIC_DEMO"
    assert "provenance_note" in opt0
    assert opt0["transit_days"] >= 0
    assert opt0["total_cost"] > 0
