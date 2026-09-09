from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Part, Requirement, StockLevel
from ..schemas import PartDetail, PartOut, PartRow, PartUsageOut, StockAdjust, StockOut

router = APIRouter(prefix="/api/parts", tags=["parts"])


@router.get("", response_model=list[PartRow])
def list_parts(search: str | None = None, db: Session = Depends(get_db)) -> list[PartRow]:
    # Fitments and stock come along with the parts rather than being fetched
    # per row: without selectinload this is one query per part per
    # relationship, which is the classic way a list endpoint gets slow
    # quietly.
    q = db.query(Part).options(selectinload(Part.fitments), selectinload(Part.stock))

    # A part that something else supersedes is not offered.
    #
    # Supersession is not a revision in place — a new number replaces an old
    # one, and the old row has to survive because machines in the field still
    # carry it on their labels. Surviving is not the same as being for sale:
    # listing it here would put two "Hydraulic Pump" rows in the catalogue,
    # one of which cannot be had, and would let a requirement be raised
    # against a number that is no longer supplied.
    #
    # It stays reachable by id — GET /api/parts/{id} does not filter — which
    # is exactly the rule: the old number goes on resolving to the new one.
    superseded = db.query(Part.supersedes_id).filter(Part.supersedes_id.isnot(None))
    q = q.filter(Part.id.notin_(superseded))
    if search:
        # Name, number and category — the three things someone actually has
        # in hand when looking for a part. Not the description: matching
        # prose returns everything that mentions "hydraulic" and is noise.
        like = f"%{search}%"
        q = q.filter(
            or_(Part.name.ilike(like), Part.part_number.ilike(like), Part.category.ilike(like))
        )
    rows = q.order_by(Part.name).all()
    return [
        PartRow(
            id=p.id,
            part_number=p.part_number,
            name=p.name,
            category=p.category,
            description=p.description,
            lead_time_days=p.lead_time_days,
            machines=list(dict.fromkeys(f.machine_model for f in p.fitments)),
            stock=StockOut.model_validate(p.stock) if p.stock else None,
        )
        for p in rows
    ]


@router.get("/{part_id}", response_model=PartDetail)
def get_part(part_id: str, db: Session = Depends(get_db)):
    part = (
        db.query(Part)
        .options(
            selectinload(Part.fitments),
            selectinload(Part.documents),
            selectinload(Part.stock),
            selectinload(Part.supersedes),
        )
        .filter(Part.id == part_id)
        .first()
    )
    if part is None:
        raise HTTPException(status_code=404, detail=f"No part '{part_id}'.")

    # Read the supersession key backwards. Someone arriving at this record
    # has a number off a machine's label; if that number has been replaced,
    # the replacement is the whole answer, and without this the record can
    # only say what it superseded — never what supersedes it.
    detail = PartDetail.model_validate(part)
    successor = db.query(Part).filter(Part.supersedes_id == part_id).first()
    if successor is not None:
        detail.superseded_by = PartOut.model_validate(successor)
    return detail


@router.get("/{part_id}/stock", response_model=StockOut)
def get_stock(part_id: str, db: Session = Depends(get_db)) -> StockLevel:
    stock = db.get(StockLevel, part_id)
    if stock is None:
        raise HTTPException(status_code=404, detail=f"No part '{part_id}'.")
    return stock


@router.get("/{part_id}/usage", response_model=list[PartUsageOut])
def get_usage(part_id: str, db: Session = Depends(get_db)):
    """Every requirement raised against this part. The honest after-sales
    answer to "where is this used" — real machines that have needed it,
    rather than a bill of materials it belongs to."""
    if db.get(Part, part_id) is None:
        raise HTTPException(status_code=404, detail=f"No part '{part_id}'.")
    rows = (
        db.query(Requirement)
        .options(selectinload(Requirement.machine))
        .filter(Requirement.part_id == part_id)
        .order_by(Requirement.created_at.desc())
        .all()
    )
    return [
        PartUsageOut(
            requirement_id=r.id,
            machine_id=r.machine_id,
            machine_serial=r.machine_serial,
            machine_model=r.machine_model,
            quantity=r.quantity,
            stage=r.stage,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{part_id}/stock/adjust", response_model=StockOut)
def adjust_stock(part_id: str, body: StockAdjust, db: Session = Depends(get_db)):
    """Receive stock in, or take it out.

    The one thing this refuses to do is let a shelf go negative: a count that
    can be wrong in that direction is worse than no count at all, because
    every availability answer downstream is derived from it.
    """
    stock = db.get(StockLevel, part_id)
    if stock is None:
        raise HTTPException(status_code=404, detail=f"No part '{part_id}'.")
    if stock.qty_on_hand + body.delta < 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Only {stock.qty_on_hand} on hand; cannot remove {abs(body.delta)}."
            ),
        )
    stock.qty_on_hand += body.delta
    db.commit()
    db.refresh(stock)
    return stock
