"""
backend/app/integrations/adapters/__init__.py

Phase 9 concrete European adapters.
"""

from app.integrations.adapters.carrier_base import CarrierAdapter
from app.integrations.adapters.dhl_adapter import DHLExpressAdapter
from app.integrations.adapters.hitachi_dealer_adapter import HitachiDealerFeedAdapter
from app.integrations.adapters.neovia_adapter import NeoviaLogisticsAdapter
from app.integrations.adapters.osrm_adapter import OSRMRouteAdapter
from app.integrations.adapters.postnl_adapter import PostNLAdapter

__all__ = [
    "CarrierAdapter",
    "DHLExpressAdapter",
    "HitachiDealerFeedAdapter",
    "NeoviaLogisticsAdapter",
    "OSRMRouteAdapter",
    "PostNLAdapter",
]
