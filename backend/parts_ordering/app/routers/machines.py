"""
Machines — the central operational context.

A requirement used to name a machine as free text and nothing checked it; the
database still holds "AXZ120", which is not a Hitachi model and matches
nothing. These endpoints exist so that stops being possible, and so the two
questions an after-sales operation actually asks about a machine can be
answered: what has it needed, and what fits it.

Deliberately narrow. There is no create-customer or create-dealer endpoint
here, no fleet management and no bulk import — Customer and Dealer exist to
attribute a machine and filter a list, and nothing in this release manages
them.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..database import get_db
from ..models import (
    Customer,
    Dealer,
    Machine,
    MachineStatus,
    Part,
    PartFitment,
    Requirement,
    Stage,
    StockLevel,
)

router = APIRouter(prefix="/api/machines", tags=["machines"])


def _open_counts(db: Session, machine_ids: list[str]) -> dict[str, int]:
    """How many requirements each machine is still waiting on.

    One grouped query for the whole page rather than one per row — the number
    a fleet list exists to show at a glance should not cost a request each.
    """
    if not machine_ids:
        return {}
    rows = (
        db.query(Requirement.machine_id, func.count(Requirement.id))
        .filter(Requirement.machine_id.in_(machine_ids), Requirement.stage != Stage.RECEIVED)
        .group_by(Requirement.machine_id)
        .all()
    )
    return {mid: n for mid, n in rows}


def _in_warranty(machine: Machine) -> bool:
    """Whether cover is still running, judged now rather than stored.

    A stored flag is wrong the day after it is written. This is one date
    comparison and it is always right.
    """
    if machine.warranty_end is None:
        return False
    end = machine.warranty_end
    if end.tzinfo is not None:
        end = end.astimezone(timezone.utc).replace(tzinfo=None)
    return end >= datetime.now(timezone.utc).replace(tzinfo=None)


def _row(machine: Machine, open_count: int) -> dict:
    return {
        "id": machine.id,
        "serial_number": machine.serial_number,
        "model": machine.model,
        "status": machine.status,
        "commissioned_at": machine.commissioned_at,
        "warranty_end": machine.warranty_end,
        "customer": machine.customer,
        "dealer": machine.dealer,
        "open_requirements": open_count,
        "in_warranty": _in_warranty(machine),
    }


def _get(db: Session, machine_id: str) -> Machine:
    machine = (
        db.query(Machine)
        .options(selectinload(Machine.customer), selectinload(Machine.dealer))
        .filter(Machine.id == machine_id)
        .first()
    )
    if machine is None:
        raise HTTPException(status_code=404, detail=f"No machine '{machine_id}'.")
    return machine


@router.get("", response_model=list[schemas.MachineRow])
def list_machines(
    search: str | None = None,
    model: str | None = None,
    status: MachineStatus | None = None,
    dealer_id: str | None = None,
    warranty: str | None = Query(default=None, pattern="^(in|out)$"),
    db: Session = Depends(get_db),
):
    """The fleet.

    Searched on serial, model and customer name — the three things somebody
    has in hand when looking for a machine. Warranty is filtered last and in
    Python because it is derived from a date rather than stored, and a
    column that does not exist cannot be filtered in SQL.
    """
    q = db.query(Machine).options(
        selectinload(Machine.customer), selectinload(Machine.dealer)
    )
    if search:
        like = f"%{search}%"
        # `has()` matches on the related customer without joining, so the
        # filter composes with everything below it and cannot duplicate rows.
        q = q.filter(
            or_(
                Machine.serial_number.ilike(like),
                Machine.model.ilike(like),
                Machine.customer.has(Customer.name.ilike(like)),
            )
        )
    if model:
        q = q.filter(Machine.model == model)
    if status is not None:
        q = q.filter(Machine.status == status)
    if dealer_id:
        q = q.filter(Machine.dealer_id == dealer_id)

    machines = q.order_by(Machine.serial_number).all()

    if warranty:
        want = warranty == "in"
        machines = [m for m in machines if _in_warranty(m) is want]

    counts = _open_counts(db, [m.id for m in machines])
    return [schemas.MachineRow(**_row(m, counts.get(m.id, 0))) for m in machines]


@router.get("/{machine_id}", response_model=schemas.MachineDetail)
def get_machine(machine_id: str, db: Session = Depends(get_db)):
    machine = _get(db, machine_id)
    counts = _open_counts(db, [machine.id])
    fitting = (
        db.query(func.count(func.distinct(PartFitment.part_id)))
        .filter(PartFitment.machine_model == machine.model)
        .scalar()
    )
    return schemas.MachineDetail(
        **_row(machine, counts.get(machine.id, 0)), fitting_parts=fitting or 0
    )


@router.get("/{machine_id}/requirements", response_model=list[schemas.MachineRequirementRow])
def machine_requirements(machine_id: str, db: Session = Depends(get_db)):
    """What this machine has needed — its parts history.

    Derived from the requirements already stored. There is deliberately no
    parts-history table: a second record of the same events is a second thing
    to keep in step.
    """
    _get(db, machine_id)
    rows = (
        db.query(Requirement)
        .options(selectinload(Requirement.part))
        .filter(Requirement.machine_id == machine_id)
        .order_by(Requirement.created_at.desc())
        .all()
    )
    return [
        schemas.MachineRequirementRow(
            id=r.id,
            part=schemas.PartOut.model_validate(r.part),
            quantity=r.quantity,
            stage=r.stage,
            reason=r.reason,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{machine_id}/parts", response_model=list[schemas.MachinePartRow])
def machine_parts(machine_id: str, db: Session = Depends(get_db)):
    """What fits this machine.

    Twenty-eight fitment rows have been in the database since the beginning,
    used to draw a column and populate a filter. This is the first endpoint
    that reads them as an answer to a question somebody asks.

    Superseded parts are excluded on the same rule the catalogue uses: an old
    number still resolves, but it is not offered.
    """
    machine = _get(db, machine_id)
    superseded = db.query(Part.supersedes_id).filter(Part.supersedes_id.isnot(None))
    rows = (
        db.query(Part, PartFitment.assembly)
        .join(PartFitment, PartFitment.part_id == Part.id)
        .filter(PartFitment.machine_model == machine.model)
        .filter(Part.id.notin_(superseded))
        .order_by(Part.name)
        .all()
    )
    stock = {
        s.part_id: s
        for s in db.query(StockLevel).filter(
            StockLevel.part_id.in_([p.id for p, _ in rows])
        )
    }
    return [
        schemas.MachinePartRow(
            id=p.id,
            part_number=p.part_number,
            name=p.name,
            category=p.category,
            description=p.description,
            lead_time_days=p.lead_time_days,
            assembly=assembly,
            stock=(
                schemas.StockOut.model_validate(stock[p.id]) if p.id in stock else None
            ),
        )
        for p, assembly in rows
    ]


@router.post("", response_model=schemas.MachineDetail, status_code=201)
def create_machine(body: schemas.MachineCreate, db: Session = Depends(get_db)):
    """Commission a machine.

    The serial is unique, and the model must be one the catalogue has fitment
    records for — a machine whose model nothing fits cannot be ordered parts
    against, so accepting it would create a record that looks fine and cannot
    be used.
    """
    if db.query(Machine).filter(Machine.serial_number == body.serial_number).first():
        raise HTTPException(
            status_code=409, detail=f"Serial '{body.serial_number}' is already registered."
        )
    if db.get(Customer, body.customer_id) is None:
        raise HTTPException(status_code=404, detail=f"No customer '{body.customer_id}'.")
    if db.get(Dealer, body.dealer_id) is None:
        raise HTTPException(status_code=404, detail=f"No dealer '{body.dealer_id}'.")

    known = {m for (m,) in db.query(PartFitment.machine_model).distinct()}
    if body.model not in known:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No part in this catalogue is listed as fitting a {body.model}. "
                f"Known models: {', '.join(sorted(known))}."
            ),
        )

    machine = Machine(
        id=body.serial_number.lower().replace(" ", "-"),
        serial_number=body.serial_number,
        model=body.model,
        customer_id=body.customer_id,
        dealer_id=body.dealer_id,
        commissioned_at=body.commissioned_at or datetime.now(timezone.utc).replace(tzinfo=None),
        warranty_end=body.warranty_end,
        status=body.status,
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return get_machine(machine.id, db)


@router.patch("/{machine_id}", response_model=schemas.MachineDetail)
def update_machine(machine_id: str, body: schemas.MachineUpdate, db: Session = Depends(get_db)):
    """Status, dealer and warranty end. Not serial, not model — see
    MachineUpdate for why."""
    machine = _get(db, machine_id)
    if body.dealer_id is not None:
        if db.get(Dealer, body.dealer_id) is None:
            raise HTTPException(status_code=404, detail=f"No dealer '{body.dealer_id}'.")
        machine.dealer_id = body.dealer_id
    if body.status is not None:
        machine.status = body.status
    if body.warranty_end is not None:
        machine.warranty_end = body.warranty_end
    db.commit()
    return get_machine(machine_id, db)
