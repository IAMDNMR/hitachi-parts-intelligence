"""
backend/app/integrations/contracts/dealer.py

Phase 9 Dealer Provider Contract.

Defines the abstract interface and Pydantic models for European dealer network
directory lookup, location metadata, and branch capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DealerBranchInfo(BaseModel):
    dealer_id: str = Field(..., description="Canonical dealer branch ID (e.g. DLR-001)")
    dealer_name: str = Field(..., description="Official dealership name")
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    country: Optional[str] = Field(None, description="ISO-3166-1 alpha-2 country code")
    postal_code: Optional[str] = Field(None, description="Postal / ZIP code")
    phone: Optional[str] = Field(None, description="Telephone contact")
    email: Optional[str] = Field(None, description="Support email")
    website: Optional[str] = Field(None, description="Dealer website URL")
    latitude: Optional[float] = Field(None, description="WGS84 latitude coordinate")
    longitude: Optional[float] = Field(None, description="WGS84 longitude coordinate")
    categories: List[str] = Field(default_factory=list, description="Authorized machine categories")
    data_source: str = Field("SRC-049", description="Source system identifier")


class DealerNetworkResult(BaseModel):
    branches: List[DealerBranchInfo] = Field(default_factory=list, description="List of dealer branches")
    total_count: int = Field(0, description="Total number of branches returned")
    source: str = Field("SRC-049", description="Data source provenance")
    status: str = Field("ACTIVE", description="Feed status")


class DealerProvider(ABC):
    """
    Authoritative abstraction over the HCME European dealer locator feed (SRC-049)
    and AuraDB dealer graph cache.
    """

    @abstractmethod
    def fetch_dealer_network(self) -> DealerNetworkResult:
        """Fetch the full European dealer network directory."""
        pass

    @abstractmethod
    def get_dealer_by_id(self, dealer_id: str) -> Optional[DealerBranchInfo]:
        """Fetch specific dealer branch details by its canonical dealer_id."""
        pass
