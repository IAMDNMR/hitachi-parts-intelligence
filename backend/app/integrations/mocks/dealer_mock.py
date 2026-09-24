"""
backend/app/integrations/mocks/dealer_mock.py

Test dealer provider implementation for development, demo, and test environments.
Provides mock European dealer branches without requiring external HTTP or live Neo4j queries.
"""

from typing import Dict, Optional
from app.integrations.contracts.dealer import (
    DealerBranchInfo,
    DealerNetworkResult,
    DealerProvider,
)

SAMPLE_BRANCHES: Dict[str, DealerBranchInfo] = {
    "DLR-001": DealerBranchInfo(
        dealer_id="DLR-001",
        dealer_name="Hitachi Construction Machinery Nederland B.V.",
        address="Souverainestraat 4",
        city="Oosterhout",
        country="NL",
        postal_code="4903 RH",
        phone="+31 162 484 200",
        email="info@hitachicm.nl",
        website="https://www.hitachicm.nl",
        latitude=51.6431,
        longitude=4.8569,
        categories=["Excavators", "Wheel Loaders"],
        data_source="SRC-049",
    ),
    "DLR-019": DealerBranchInfo(
        dealer_id="DLR-019",
        dealer_name="Hitachi Baumaschinen Deutschland GmbH (Munich Hub)",
        address="Gutenbergstraße 12",
        city="Munich",
        country="DE",
        postal_code="85748",
        phone="+49 89 3177 0",
        email="service@hitachicm.de",
        website="https://www.hitachicm.de",
        latitude=48.1351,
        longitude=11.5820,
        categories=["Excavators", "Wheel Loaders", "Mining"],
        data_source="SRC-049",
    ),
    "DLR-042": DealerBranchInfo(
        dealer_id="DLR-042",
        dealer_name="Hitachi Construction Machinery France (Paris Hub)",
        address="Rue des Carrières 8",
        city="Paris",
        country="FR",
        postal_code="93100",
        phone="+33 1 48 57 00 00",
        email="contact@hitachicm.fr",
        website="https://www.hitachicm.fr",
        latitude=48.8566,
        longitude=2.3522,
        categories=["Excavators"],
        data_source="SRC-049",
    ),
}


class TestDealerProvider(DealerProvider):
    """
    Test/development implementation of DealerProvider.
    Supplies fixed canonical branches for offline testing.
    """

    def __init__(self, branches: Optional[Dict[str, DealerBranchInfo]] = None):
        self._branches = branches or dict(SAMPLE_BRANCHES)

    def fetch_dealer_network(self) -> DealerNetworkResult:
        branches_list = list(self._branches.values())
        return DealerNetworkResult(
            branches=branches_list,
            total_count=len(branches_list),
            source="SRC-049-TEST",
            status="ACTIVE",
        )

    def get_dealer_by_id(self, dealer_id: str) -> Optional[DealerBranchInfo]:
        if dealer_id in self._branches:
            return self._branches[dealer_id]
        # Return generic fallback branch for unknown ID
        return DealerBranchInfo(
            dealer_id=dealer_id,
            dealer_name=f"Authorized European Hitachi Dealership ({dealer_id})",
            city="Amsterdam",
            country="NL",
            latitude=52.3676,
            longitude=4.9041,
            data_source="SRC-049-MOCK",
        )
