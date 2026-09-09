"""
Service kits — a service as one orderable thing.

The rest of this API is reactive: something failed, someone raised a
requirement for the part. A kit is the other half of a parts operation, and
the half that can be planned — the parts a known job consumes, ordered
together, before anything has broken.

Raising one is the only endpoint here that writes. It creates a requirement
per line and nothing else: each one then travels the ordinary seven stages
under the ordinary rules, because a kit is a way of RAISING requirements, not
a second workflow beside them. Nothing about check-availability, allocation or
goods receipt needed changing to support this.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..database import get_db
from ..models import Part, ServiceKit, ServiceKitLine, StockLevel
from ..services import workflow

router = APIRouter(prefix="/api/kits", tags=["kits"])


def _load(db: Session, kit_id: str | None = None):
    q = db.query(ServiceKit).options(
        selectinload(ServiceKit.lines).selectinload(ServiceKitLine.part),
        selectinload(ServiceKit.models),
    )
    if kit_id is not None:
        return q.filter(ServiceKit.id == kit_id).first()
    return q.order_by(ServiceKit.name).all()


def _row(kit: ServiceKit, stock: dict[str, StockLevel]) -> dict:
    """The shared summary. `ready` and `longest_lead_days` are the two numbers
    a service date is committed against, so they are computed once here rather
    than re-derived by every caller."""
    covered = []
    leads = []
    for line in kit.lines:
        have = stock.get(line.part_id)
        covered.append(bool(have and have.qty_on_hand >= line.quantity))
        leads.append(line.part.lead_time_days)
    return {
        "id": kit.id,
        "code": kit.code,
        "name": kit.name,
        "description": kit.description,
        "interval_hours": kit.interval_hours,
        "machines": [m.machine_model for m in kit.models],
        "line_count": len(kit.lines),
        "ready": all(covered) if covered else False,
        "longest_lead_days": max(leads) if leads else 0,
    }


def _stock_for(db: Session, kits) -> dict[str, StockLevel]:
    ids = {line.part_id for kit in kits for line in kit.lines}
    if not ids:
        return {}
    rows = db.query(StockLevel).filter(StockLevel.part_id.in_(ids)).all()
    return {r.part_id: r for r in rows}


@router.get("", response_model=list[schemas.KitRow])
def list_kits(db: Session = Depends(get_db)):
    kits = _load(db)
    stock = _stock_for(db, kits)
    return [schemas.KitRow(**_row(k, stock)) for k in kits]


@router.get("/{kit_id}", response_model=schemas.KitDetail)
def get_kit(kit_id: str, db: Session = Depends(get_db)):
    kit = _load(db, kit_id)
    if kit is None:
        raise HTTPException(status_code=404, detail=f"No service kit '{kit_id}'.")
    stock = _stock_for(db, [kit])
    lines = [
        schemas.KitLineOut(
            part=schemas.PartOut.model_validate(line.part),
            quantity=line.quantity,
            lead_time_days=line.part.lead_time_days,
            stock=(
                schemas.StockOut.model_validate(stock[line.part_id])
                if line.part_id in stock
                else None
            ),
            covered=bool(
                line.part_id in stock and stock[line.part_id].qty_on_hand >= line.quantity
            ),
        )
        for line in kit.lines
    ]
    return schemas.KitDetail(**_row(kit, stock), lines=lines)


@router.post("/{kit_id}/raise", response_model=list[schemas.RequirementOut], status_code=201)
def raise_kit(kit_id: str, body: schemas.KitRaise, db: Session = Depends(get_db)):
    """Raise the whole kit against one machine.

    One requirement per line, each carrying the kit it came from, so five
    lines of a service can be told apart from five unrelated failures that
    happened to be raised the same afternoon.

    Availability is deliberately NOT checked here. A kit whose parts are not
    all on the shelf is still a service somebody has to plan — refusing to
    raise it would mean the one case where ordering ahead matters most is the
    one case the tool will not do. The shelf's answer is on the kit itself
    (`ready`), before the button is pressed.
    """
    kit = _load(db, kit_id)
    if kit is None:
        raise HTTPException(status_code=404, detail=f"No service kit '{kit_id}'.")
    if not kit.lines:
        raise HTTPException(status_code=409, detail=f"Kit '{kit_id}' has no parts in it.")

    missing = [l.part_id for l in kit.lines if db.get(Part, l.part_id) is None]
    if missing:
        raise HTTPException(
            status_code=409,
            detail=f"Kit '{kit_id}' calls for parts that are not in the catalogue: {', '.join(missing)}.",
        )

    reason = body.reason or f"{kit.name} ({kit.code})"
    raised = []
    for line in kit.lines:
        req = workflow.create_requirement(
            db,
            machine_serial=body.machine_serial,
            part_id=line.part_id,
            quantity=line.quantity,
            reason=reason,
        )
        req.kit_id = kit.id
        raised.append(req)
    db.commit()
    for req in raised:
        db.refresh(req)
    return raised
