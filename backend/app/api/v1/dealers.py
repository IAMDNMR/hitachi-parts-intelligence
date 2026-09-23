"""
backend/app/api/v1/dealers.py

HCME Europe dealer network — read-only, backed by DealerBranch nodes.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from app.db.neo4j.connection import get_neo4j_session
from app.modules.dealer.service import list_dealers

router = APIRouter(prefix="/dealers", tags=["Dealers"])


@router.get("", response_model=List[Dict[str, Any]])
def get_dealers(
    country: Optional[str] = None,
    city: Optional[str] = None,
    session=Depends(get_neo4j_session),
):
    """Dealer branches, optionally filtered by ISO country code and/or city."""
    return list_dealers(session, country=country, city=city)
