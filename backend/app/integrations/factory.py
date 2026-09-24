"""
backend/app/integrations/factory.py

Phase 9 Integration Provider Factory & Registry.

Exposes dependency-injected getter functions for all 9 operational domains.
Resolves concrete European adapters when configured via environment variables
with clean, honest fallback to TestProvider mocks when unconfigured or in testing.

Domains covered:
1. InventoryProvider
2. PricingProvider
3. OrderProvider
4. RoutingProvider
5. ShippingRateProvider
6. ShipmentProvider
7. TrackingProvider
8. ServiceProvider
9. DealerProvider
"""

import os
from typing import Any, Dict

# Contracts
from app.integrations.contracts.inventory import InventoryProvider
from app.integrations.contracts.pricing import PricingProvider
from app.integrations.contracts.order import OrderProvider
from app.integrations.contracts.routing import RoutingProvider
from app.integrations.contracts.shipping_rate import ShippingRateProvider
from app.integrations.contracts.shipment import ShipmentProvider
from app.integrations.contracts.tracking import TrackingProvider
from app.integrations.contracts.service import ServiceProvider
from app.integrations.contracts.dealer import DealerProvider

# Mocks
from app.integrations.mocks.inventory_mock import TestInventoryProvider
from app.integrations.mocks.pricing_mock import TestPricingProvider
from app.integrations.mocks.order_mock import TestOrderProvider
from app.integrations.mocks.routing_mock import TestRoutingProvider
from app.integrations.mocks.shipping_rate_mock import TestShippingRateProvider
from app.integrations.mocks.shipment_mock import TestShipmentProvider
from app.integrations.mocks.tracking_mock import TestTrackingProvider
from app.integrations.mocks.service_mock import TestServiceProvider
from app.integrations.mocks.dealer_mock import TestDealerProvider

# Concrete Adapters
from app.integrations.adapters.dhl_adapter import DHLExpressAdapter
from app.integrations.adapters.hitachi_dealer_adapter import HitachiDealerFeedAdapter
from app.integrations.adapters.neovia_adapter import NeoviaLogisticsAdapter
from app.integrations.adapters.osrm_adapter import OSRMRouteAdapter
from app.integrations.adapters.postnl_adapter import PostNLAdapter
from app.integrations.adapters.synthetic_inventory_adapter import SyntheticDemoInventoryProvider

# Process-level provider cache
_PROVIDERS: Dict[str, Any] = {}


def set_provider_override(domain: str, provider_instance: Any) -> None:
    """Allow runtime injection or test fixture overrides for a domain."""
    _PROVIDERS[domain] = provider_instance


def reset_providers() -> None:
    """Clear cached provider instances."""
    _PROVIDERS.clear()


def get_inventory_provider() -> InventoryProvider:
    if "inventory" in _PROVIDERS:
        return _PROVIDERS["inventory"]

    prov_type = os.environ.get("INVENTORY_PROVIDER", "synthetic_demo").lower()
    # No public OEM parts inventory API exists. Catalogue parts read labelled
    # SYNTHETIC_DEMO stock from Neo4j; other part numbers use the test scenarios.
    if prov_type == "test":
        instance = TestInventoryProvider()
    else:
        instance = SyntheticDemoInventoryProvider()
    _PROVIDERS["inventory"] = instance
    return instance


def get_pricing_provider() -> PricingProvider:
    if "pricing" in _PROVIDERS:
        return _PROVIDERS["pricing"]

    prov_type = os.environ.get("PRICING_PROVIDER", "test").lower()
    # Dealer authenticated access required; fallback to TestPricingProvider
    instance = TestPricingProvider()
    _PROVIDERS["pricing"] = instance
    return instance


def get_order_provider() -> OrderProvider:
    if "order" in _PROVIDERS:
        return _PROVIDERS["order"]

    prov_type = os.environ.get("ORDER_PROVIDER", "test").lower()
    # SAP ERP requires commercial partner link; fallback to TestOrderProvider
    instance = TestOrderProvider()
    _PROVIDERS["order"] = instance
    return instance


def get_routing_provider() -> RoutingProvider:
    if "routing" in _PROVIDERS:
        return _PROVIDERS["routing"]

    prov_type = os.environ.get("ROUTING_PROVIDER", "test").lower()
    if prov_type in ("osrm", "live", "real"):
        instance = OSRMRouteAdapter()
    else:
        instance = TestRoutingProvider()
    _PROVIDERS["routing"] = instance
    return instance


def get_shipping_rate_provider() -> ShippingRateProvider:
    if "shipping_rate" in _PROVIDERS:
        return _PROVIDERS["shipping_rate"]

    prov_type = os.environ.get("SHIPPING_RATE_PROVIDER", "test").lower()
    instance = TestShippingRateProvider()
    _PROVIDERS["shipping_rate"] = instance
    return instance


def get_shipment_provider() -> ShipmentProvider:
    if "shipment" in _PROVIDERS:
        return _PROVIDERS["shipment"]

    prov_type = os.environ.get("SHIPMENT_PROVIDER", "test").lower()
    if prov_type == "dhl":
        instance = DHLExpressAdapter()
    elif prov_type == "postnl":
        instance = PostNLAdapter()
    elif prov_type == "neovia":
        instance = NeoviaLogisticsAdapter()
    else:
        instance = TestShipmentProvider()
    _PROVIDERS["shipment"] = instance
    return instance


def get_tracking_provider() -> TrackingProvider:
    if "tracking" in _PROVIDERS:
        return _PROVIDERS["tracking"]

    prov_type = os.environ.get("TRACKING_PROVIDER", "test").lower()
    if prov_type == "dhl":
        instance = DHLExpressAdapter()
    elif prov_type == "postnl":
        instance = PostNLAdapter()
    elif prov_type == "neovia":
        instance = NeoviaLogisticsAdapter()
    else:
        instance = TestTrackingProvider()
    _PROVIDERS["tracking"] = instance
    return instance


def get_service_provider() -> ServiceProvider:
    if "service" in _PROVIDERS:
        return _PROVIDERS["service"]

    prov_type = os.environ.get("SERVICE_PROVIDER", "test").lower()
    instance = TestServiceProvider()
    _PROVIDERS["service"] = instance
    return instance


def get_dealer_provider() -> DealerProvider:
    if "dealer" in _PROVIDERS:
        return _PROVIDERS["dealer"]

    prov_type = os.environ.get("DEALER_PROVIDER", "hitachi").lower()
    if prov_type in ("test", "mock"):
        instance = TestDealerProvider()
    else:
        instance = HitachiDealerFeedAdapter()
    _PROVIDERS["dealer"] = instance
    return instance
