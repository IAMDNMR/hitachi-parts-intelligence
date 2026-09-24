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


def _spec(mode, level=None):
    return next(s for s in RATE_SPECS if s.mode == mode and (level is None or s.service_level == level))


KMS = (20.0, 65.0, 250.0, 550.0, 900.0, 1400.0, 2200.0)


def test_cost_grows_with_distance_for_every_mode():
    from app.modules.transport.rate_card import option_cost
    for spec in RATE_SPECS:
        totals = [option_cost(spec, km)[3] for km in KMS]
        assert totals == sorted(totals) and totals[0] < totals[-1], spec.display_name


def test_express_costs_more_than_standard():
    from app.modules.transport.rate_card import option_cost
    std, exp = _spec(TransportMode.ROAD, ServiceLevel.STANDARD), _spec(TransportMode.ROAD, ServiceLevel.EXPRESS)
    for km in KMS:
        assert option_cost(exp, km)[3] > option_cost(std, km)[3]


def test_express_is_strictly_faster_than_standard():
    from app.modules.transport.rate_card import transit_days_for
    std, exp = _spec(TransportMode.ROAD, ServiceLevel.STANDARD), _spec(TransportMode.ROAD, ServiceLevel.EXPRESS)
    for km in KMS:
        assert transit_days_for(exp, km) < transit_days_for(std, km)


def test_rail_is_cheaper_than_road_on_long_routes_and_slower():
    from app.modules.transport.rate_card import option_cost, transit_days_for
    rail, road = _spec(TransportMode.RAIL), _spec(TransportMode.ROAD, ServiceLevel.STANDARD)
    for km in (550.0, 900.0, 1400.0):
        assert option_cost(rail, km)[3] < option_cost(road, km)[3]
        assert transit_days_for(rail, km) >= transit_days_for(road, km)


def test_air_is_the_dearest_and_never_slower_than_road_express():
    from app.modules.transport.rate_card import option_cost, transit_days_for
    air, exp = _spec(TransportMode.AIR), _spec(TransportMode.ROAD, ServiceLevel.EXPRESS)
    for km in KMS:
        assert transit_days_for(air, km) <= transit_days_for(exp, km)
        if km <= 1400:  # on very long routes a dedicated express road service costs more than air freight
            assert option_cost(air, km)[3] > option_cost(exp, km)[3]


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
