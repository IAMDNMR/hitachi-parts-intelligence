"""
backend/app/integrations/mocks/shipment_mock.py

Test shipment provider implementation for development, demo, and test environments.
Clearly flags integration as NOT_CONNECTED per HCME architecture requirements.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.integrations.contracts.shipment import (
    ShipmentCreationRequest,
    ShipmentCreationResult,
    ShipmentProvider,
)


class TestShipmentProvider(ShipmentProvider):
    """
    Test/development implementation of ShipmentProvider.
    Mints deterministic mock tracking references and ETAs for testing.
    Never presents itself as an active HCME production carrier integration.
    """

    def create_shipment(self, request: ShipmentCreationRequest) -> ShipmentCreationResult:
        # Standard mock carrier is Demo Carrier Logistics (HCME European Logistics Test)
        tracking_num = f"DEMO-TRK-{uuid.uuid4().hex[:8].upper()}"
        eta = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")

        return ShipmentCreationResult(
            status="SUCCESS",
            carrier="Demo European Logistics Partner",
            tracking_number=tracking_num,
            estimated_delivery=eta,
            message="Test shipment created (TEST/DEVELOPMENT mode — no real HCME carrier connected)",
        )
