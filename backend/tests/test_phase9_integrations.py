"""
backend/tests/test_phase9_integrations.py

Comprehensive Phase 9 Real Integrations Unit & Integration Test Suite.

Covers:
1. ServiceProvider and DealerProvider contracts and mocks.
2. Concrete adapters: OSRMRouteAdapter, HitachiDealerFeedAdapter, DHLExpressAdapter, PostNLAdapter.
3. Provider factory dynamic resolution and fallback behavior.
4. Neo4j AuraDB Provenance synchronization for Order, Shipment, and ServiceJob.
5. Invariant check: DealerBranch.synthetic remains NULL on canonical nodes.
6. Integration Health API: GET /api/v1/health/integrations covering all 9 operational domains.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.health import IntegrationsHealthResponse
from app.integrations.contracts.dealer import (
    DealerBranchInfo,
    DealerNetworkResult,
    DealerProvider,
)
from app.integrations.contracts.service import (
    ServiceProvider,
    ServiceScheduleRequest,
    ServiceScheduleResult,
    ServiceStatusResult,
)
from app.integrations.contracts.shipment import (
    ShipmentCreationRequest,
    ShipmentCreationResult,
    ShipmentProvider,
)
from app.integrations.contracts.tracking import (
    TrackingProvider,
    TrackingQuery,
    TrackingResult,
)
from app.integrations.contracts.routing import RouteQuery, RoutingProvider
from app.integrations.mocks.dealer_mock import TestDealerProvider
from app.integrations.mocks.service_mock import TestServiceProvider
from app.integrations.adapters.dhl_adapter import DHLExpressAdapter
from app.integrations.adapters.hitachi_dealer_adapter import HitachiDealerFeedAdapter
from app.integrations.adapters.neovia_adapter import NeoviaLogisticsAdapter
from app.integrations.adapters.osrm_adapter import OSRMRouteAdapter, haversine_km
from app.integrations.adapters.postnl_adapter import PostNLAdapter
from app.integrations.factory import (
    get_dealer_provider,
    get_inventory_provider,
    get_order_provider,
    get_pricing_provider,
    get_routing_provider,
    get_service_provider,
    get_shipment_provider,
    get_shipping_rate_provider,
    get_tracking_provider,
    reset_providers,
    set_provider_override,
)
from app.modules.availability.service import check_availability
from app.modules.fulfilment.service import (
    generate_fulfilment_options,
    proceed_to_allocation_pending,
    select_fulfilment_option,
)
from app.modules.allocation.service import create_allocation
from app.modules.order.service import accept_order, create_order, get_order
from app.modules.shipment.service import create_shipment, get_shipment, get_tracking
from app.modules.service.service import create_service_job, get_service_job

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Contract & Mock Tests
# ---------------------------------------------------------------------------

def test_service_provider_contract_and_mock():
    mock_service = TestServiceProvider()
    assert isinstance(mock_service, ServiceProvider)

    req = ServiceScheduleRequest(
        order_id="order-123",
        dealer_id="DLR-001",
        part_number="4658521",
        service_type="PARTS_INSTALLATION",
        notes="Urgent hydraulic pump replacement",
    )
    result = mock_service.schedule_service(req)
    assert isinstance(result, ServiceScheduleResult)
    assert result.success is True
    assert result.status == "OPEN"
    assert result.external_job_id.startswith("EXT-WO-")
    assert result.data_source == "SYNTHETIC_DEMO"

    status = mock_service.get_service_status(result.external_job_id)
    assert isinstance(status, ServiceStatusResult)
    assert status.status == "OPEN"
    assert status.integration_status == "NOT_CONNECTED"


def test_dealer_provider_contract_and_mock():
    mock_dealer = TestDealerProvider()
    assert isinstance(mock_dealer, DealerProvider)

    network = mock_dealer.fetch_dealer_network()
    assert isinstance(network, DealerNetworkResult)
    assert network.total_count >= 3
    assert any(b.dealer_id == "DLR-001" for b in network.branches)

    branch = mock_dealer.get_dealer_by_id("DLR-001")
    assert branch is not None
    assert branch.dealer_id == "DLR-001"
    assert branch.city == "Oosterhout"
    assert branch.country == "NL"


# ---------------------------------------------------------------------------
# 2. Concrete Adapters Tests
# ---------------------------------------------------------------------------

def test_osrm_adapter_haversine_and_offline_routing():
    # Distance between Oosterhout (51.6431, 4.8569) and Munich (48.1351, 11.5820)
    crow_fly = haversine_km(51.6431, 4.8569, 48.1351, 11.5820)
    assert 600.0 < crow_fly < 700.0

    adapter = OSRMRouteAdapter()
    assert isinstance(adapter, RoutingProvider)

    query = RouteQuery(
        origin_location_id="DEPOT-OOSTERHOUT",
        destination_branch_id="DLR-019",
        part_number="4658521",
        quantity=1,
    )
    routes = adapter.find_routes(query)
    assert len(routes) >= 2
    assert any(r.transport_mode == "ROAD" for r in routes)
    assert any(r.transport_mode == "COURIER" for r in routes)

    # Verify same-location immediate pickup
    same_query = RouteQuery(
        origin_location_id="DLR-001",
        destination_branch_id="DLR-001",
        part_number="4658521",
        quantity=1,
    )
    local_routes = adapter.find_routes(same_query)
    assert len(local_routes) == 1
    assert local_routes[0].transport_mode == "INTERNAL_TRANSFER"
    assert local_routes[0].estimated_transit_days == 0


def test_hitachi_dealer_adapter():
    adapter = HitachiDealerFeedAdapter()
    assert isinstance(adapter, DealerProvider)

    # Should fetch network from feed, AuraDB, or embedded sample without throwing
    res = adapter.fetch_dealer_network()
    assert isinstance(res, DealerNetworkResult)
    assert res.total_count > 0

    branch = adapter.get_dealer_by_id("DLR-001")
    assert branch is not None
    assert branch.dealer_id == "DLR-001"


def test_dhl_express_adapter():
    adapter = DHLExpressAdapter()
    assert isinstance(adapter, ShipmentProvider)
    assert isinstance(adapter, TrackingProvider)
    assert adapter.carrier_name == "DHL Express Europe"

    req = ShipmentCreationRequest(
        order_id="order-test-dhl",
        part_number="4658521",
        quantity=1,
        origin_source_id="DEPOT-OOSTERHOUT",
        destination_branch_id="DLR-019",
    )
    res = adapter.create_shipment(req)
    assert isinstance(res, ShipmentCreationResult)
    assert res.status == "SUCCESS"
    assert "DHL" in res.tracking_number

    track = adapter.get_tracking(TrackingQuery(tracking_number=res.tracking_number))
    assert isinstance(track, TrackingResult)
    assert track.carrier == "DHL Express Europe"


def test_postnl_adapter():
    adapter = PostNLAdapter()
    assert isinstance(adapter, ShipmentProvider)
    assert isinstance(adapter, TrackingProvider)
    assert adapter.carrier_name == "PostNL Europe Parcel"

    req = ShipmentCreationRequest(
        order_id="order-test-pnl",
        part_number="4658521",
        quantity=1,
        origin_source_id="DEPOT-OOSTERHOUT",
        destination_branch_id="DLR-001",
    )
    res = adapter.create_shipment(req)
    assert isinstance(res, ShipmentCreationResult)
    assert res.status == "SUCCESS"
    assert "3S" in res.tracking_number

    track = adapter.get_tracking(TrackingQuery(tracking_number=res.tracking_number))
    assert isinstance(track, TrackingResult)
    assert track.carrier == "PostNL Europe Parcel"


# ---------------------------------------------------------------------------
# 3. Provider Factory Resolution Tests
# ---------------------------------------------------------------------------

def test_provider_factory_resolution():
    reset_providers()

    assert get_inventory_provider() is not None
    assert get_pricing_provider() is not None
    assert get_order_provider() is not None
    assert get_shipping_rate_provider() is not None
    assert get_service_provider() is not None

    # Default fallback
    assert isinstance(get_shipment_provider(), ShipmentProvider)
    assert isinstance(get_tracking_provider(), TrackingProvider)
    assert isinstance(get_dealer_provider(), DealerProvider)

    # Test override
    custom_dealer = TestDealerProvider()
    set_provider_override("dealer", custom_dealer)
    assert get_dealer_provider() is custom_dealer

    reset_providers()


# ---------------------------------------------------------------------------
# 4. Neo4j AuraDB Provenance Synchronization & Integrity Tests
# ---------------------------------------------------------------------------

def test_auradb_provenance_synchronization(neo4j_session, test_run_id):
    """
    Ensures Order, Shipment, and ServiceJob store external IDs, synced_at,
    and data_source while keeping DealerBranch.synthetic as NULL on canonical nodes.
    """
    pn = f"PN9-PROV-{test_run_id}-{neo4j_session.run('RETURN randomUUID() AS u').single()['u'][:8]}"
    neo4j_session.run(
        "MERGE (p:Part {part_number: $pn}) ON CREATE SET p.part_id = $pn, p.testRunId = $run",
        {"pn": pn, "run": test_run_id},
    ).consume()

    # 1. Fulfilment -> Allocation -> Order
    avail_res = check_availability(
        session=neo4j_session,
        fulfilment_request_id=None,
        part_number=pn,
        quantity=1,
        test_run_id=test_run_id,
    )
    req_id = avail_res["fulfilment_request_id"]
    options = generate_fulfilment_options(neo4j_session, req_id, test_run_id=test_run_id)
    select_fulfilment_option(neo4j_session, req_id, options[0]["id"], test_run_id=test_run_id)
    proceed_to_allocation_pending(neo4j_session, req_id, test_run_id=test_run_id)
    create_allocation(neo4j_session, req_id, test_run_id=test_run_id)

    order = create_order(neo4j_session, req_id, test_run_id=test_run_id)
    assert "data_source" in order
    assert "synced_at" in order
    assert order["data_source"] is not None

    accepted = accept_order(neo4j_session, order["id"], test_run_id=test_run_id)
    assert accepted["status"] == "ACCEPTED"

    # 2. Shipment
    sh = create_shipment(neo4j_session, order_id=accepted["id"], test_run_id=test_run_id)
    assert "external_shipment_id" in sh
    assert "synced_at" in sh
    assert "data_source" in sh
    assert sh["external_shipment_id"] is not None
    assert sh["data_source"] is not None

    fetched_sh = get_shipment(neo4j_session, sh["shipment_id"])
    assert fetched_sh["external_shipment_id"] == sh["external_shipment_id"]
    assert fetched_sh["synced_at"] is not None

    tracking_data = get_tracking(neo4j_session, sh["tracking_number"])
    assert tracking_data["external_shipment_id"] == sh["external_shipment_id"]

    # 3. ServiceJob
    sj = create_service_job(neo4j_session, order_id=accepted["id"], test_run_id=test_run_id)
    assert "external_job_id" in sj
    assert "synced_at" in sj
    assert "data_source" in sj
    assert sj["data_source"] is not None

    fetched_sj = get_service_job(neo4j_session, sj["service_job_id"])
    assert fetched_sj["external_job_id"] == sj["external_job_id"]
    assert fetched_sj["synced_at"] is not None

    # 4. Critical Invariant Check: DealerBranch.synthetic MUST be NULL on canonical nodes
    res = neo4j_session.run(
        "MATCH (d:DealerBranch) WHERE d.synthetic IS NOT NULL RETURN count(d) AS c"
    ).single()
    assert res["c"] == 0, "Canonical DealerBranch nodes must have synthetic IS NULL!"


# ---------------------------------------------------------------------------
# 5. Integration Health API Endpoint Tests (/api/v1/health/integrations)
# ---------------------------------------------------------------------------

def test_health_integrations_endpoint():
    response = client.get("/api/v1/health/integrations")
    assert response.status_code == 200
    data = response.json()

    # Validate response adheres to IntegrationsHealthResponse schema
    assert "timestamp" in data
    assert "status" in data
    assert data["status"] in ("UP", "DEGRADED", "DOWN")
    assert "database" in data
    assert data["database"]["provider"] == "Neo4j AuraDB"
    assert "integrations" in data

    integrations = data["integrations"]
    assert len(integrations) == 9

    expected_domains = [
        "Parts / Product Master",
        "Inventory & Stock Availability",
        "Pricing & Commercial Terms",
        "Dealer Network & DMS",
        "Order & ERP",
        "Allocation & Stock Ledger",
        "Shipment & TMS",
        "Carrier Tracking",
        "Field Service & Telematics",
    ]

    domain_names = [item["domain"] for item in integrations]
    for d in expected_domains:
        assert d in domain_names, f"Expected domain '{d}' missing from health integrations report"

    # Verify specific authoritative classifications
    inv = next(i for i in integrations if i["domain"] == "Inventory & Stock Availability")
    assert inv["classification"] == "PARTNER / COMMERCIAL ACCESS REQUIRED"
    assert inv["status"] == "NOT_CONNECTED"
    assert inv["mode"] == "SYNTHETIC_FALLBACK"

    pricing = next(i for i in integrations if i["domain"] == "Pricing & Commercial Terms")
    assert pricing["classification"] == "AUTHENTICATED / DEALER ACCESS REQUIRED"
    assert pricing["status"] == "NOT_AVAILABLE"
    assert pricing["mode"] == "HONEST_PLACEHOLDER"

    parts = next(i for i in integrations if i["domain"] == "Parts / Product Master")
    assert parts["classification"] == "CONNECTED"
    assert parts["mode"] == "CANONICAL"
