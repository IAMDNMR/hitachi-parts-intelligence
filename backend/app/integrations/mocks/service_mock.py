"""
backend/app/integrations/mocks/service_mock.py

Test service provider implementation for development, demo, and test environments.
Honoring the honest reporting principle: flags external integration as NOT_CONNECTED.
"""

from datetime import datetime, timezone
import uuid

from app.integrations.contracts.service import (
    ServiceProvider,
    ServiceScheduleRequest,
    ServiceScheduleResult,
    ServiceStatusResult,
)


class TestServiceProvider(ServiceProvider):
    """
    Test/development implementation of ServiceProvider.
    Mints mock external work order references for testing while clearly
    declaring itself as NOT_CONNECTED to an external DMS.
    """

    def schedule_service(self, request: ServiceScheduleRequest) -> ServiceScheduleResult:
        external_wo = f"EXT-WO-{uuid.uuid4().hex[:8].upper()}"
        return ServiceScheduleResult(
            success=True,
            status="OPEN",
            external_job_id=external_wo,
            message="Test service scheduled (TEST/DEVELOPMENT mode — NOT_CONNECTED)",
            data_source="SYNTHETIC_DEMO",
        )

    def get_service_status(self, external_job_id: str) -> ServiceStatusResult:
        now_str = datetime.now(timezone.utc).isoformat()
        return ServiceStatusResult(
            external_job_id=external_job_id,
            status="OPEN",
            notes="Simulated service status from mock provider",
            events=[
                {
                    "event_type": "CREATED",
                    "timestamp": now_str,
                    "description": "Mock work order registered in dealer DMS simulator.",
                }
            ],
            integration_status="NOT_CONNECTED",
        )
