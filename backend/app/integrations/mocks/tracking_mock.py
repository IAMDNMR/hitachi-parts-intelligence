"""
backend/app/integrations/mocks/tracking_mock.py

Test tracking provider implementation for development, demo, and test environments.
Clearly flags integration as NOT_CONNECTED per HCME architecture requirements.
"""

from datetime import datetime, timezone

from app.integrations.contracts.tracking import (
    TrackingEventPayload,
    TrackingProvider,
    TrackingQuery,
    TrackingResult,
)


class TestTrackingProvider(TrackingProvider):
    """
    Test/development implementation of TrackingProvider.
    Supplies mock event stream for testing state transitions and tracking display.
    """

    def get_tracking(self, query: TrackingQuery) -> TrackingResult:
        now_str = datetime.now(timezone.utc).isoformat()
        return TrackingResult(
            tracking_number=query.tracking_number,
            carrier="Demo European Logistics Partner",
            status="IN_TRANSIT",
            estimated_delivery="2026-09-28",
            events=[
                TrackingEventPayload(
                    event_type="DISPATCHED",
                    timestamp=now_str,
                    location="European Parts Centre, Oosterhout (NL)",
                    description="Shipment picked up by carrier from Oosterhout distribution centre.",
                ),
                TrackingEventPayload(
                    event_type="IN_TRANSIT",
                    timestamp=now_str,
                    location="Regional Transit Hub, Eindhoven (NL)",
                    description="In transit to destination dealer facility.",
                ),
            ],
            integration_status="NOT_CONNECTED",
        )
