"""
backend/app/modules/transport/router.py

FastAPI router for European Transportation Options.
Exposes:
  - GET /api/v1/transport/options
  - GET /api/v1/fulfilment-requests/{id}/transport-options
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.db.neo4j.connection import get_neo4j_session
from app.errors.exceptions import NotFoundError
from app.modules.transport.engine import compute_transport_comparison
from app.modules.transport.models import TransportComparisonResponse

router = APIRouter(tags=["Transportation"])


@router.get("/transport/options", response_model=TransportComparisonResponse)
def get_transport_options(
    destination_branch_id: str = Query(..., description="Destination DealerBranch ID (e.g. DLR-001)"),
    origin_id: str = Query("DEPOT-OOSTERHOUT", description="Origin Depot or Location ID"),
    part_number: str = Query("4663907", description="Part Number"),
    quantity: int = Query(1, ge=1, description="Order quantity"),
    selected_option_id: Optional[str] = Query(None, description="Currently selected option ID"),
    session=Depends(get_neo4j_session),
):
    """
    Compute multi-modal European transport options based on verified dealer coordinates,
    distance bands, and deterministic rates.
    """
    return compute_transport_comparison(
        session=session,
        origin_id=origin_id,
        destination_branch_id=destination_branch_id,
        part_number=part_number,
        quantity=quantity,
        selected_option_id=selected_option_id,
    )


@router.get("/fulfilment-requests/{request_id}/transport-options", response_model=TransportComparisonResponse)
def get_request_transport_options(
    request_id: str,
    session=Depends(get_neo4j_session),
):
    """
    Compute candidate transport options for an existing FulfilmentRequest node.
    """
    req = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        RETURN r.id as id, r.partNumber as part_number, r.quantity as quantity,
               r.destinationBranchId as dest_branch_id, r.selectedOptionId as selected_option_id
        """,
        {"id": request_id},
    ).single()

    if not req:
        raise NotFoundError(f"FulfilmentRequest '{request_id}' not found")

    dest_branch_id = req["dest_branch_id"] or "DLR-001"
    part_number = req["part_number"] or "4663907"
    qty = req["quantity"] or 1
    selected_opt = req["selected_option_id"]

    # If there's an assigned source in InventoryCache, resolve it; otherwise DEPOT-OOSTERHOUT
    source_row = session.run(
        """
        MATCH (c:InventoryCache {partNumber: $pn})
        RETURN c.sourceId as source_id
        ORDER BY c.inventoryTimestamp DESC
        LIMIT 1
        """,
        {"pn": part_number},
    ).single()
    origin_id = source_row["source_id"] if source_row and source_row["source_id"] else "DEPOT-OOSTERHOUT"

    return compute_transport_comparison(
        session=session,
        origin_id=origin_id,
        destination_branch_id=dest_branch_id,
        part_number=part_number,
        quantity=qty,
        selected_option_id=selected_opt,
    )
