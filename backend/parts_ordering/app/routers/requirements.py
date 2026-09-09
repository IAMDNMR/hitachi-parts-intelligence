from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..database import get_db
from ..models import Machine, Part, Requirement, Stage
from ..services import workflow

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


def _get_or_404(db: Session, requirement_id: int) -> Requirement:
    req = (
        db.query(Requirement)
        .options(
            selectinload(Requirement.part),
            selectinload(Requirement.events),
            selectinload(Requirement.machine),
        )
        .filter(Requirement.id == requirement_id)
        .first()
    )
    if req is None:
        raise HTTPException(status_code=404, detail=f"No requirement #{requirement_id}.")
    return req


def _to_detail(req: Requirement) -> schemas.RequirementDetail:
    return schemas.RequirementDetail.model_validate(
        {**schemas.RequirementOut.model_validate(req).model_dump(), "events": req.events,
         "next_stage": workflow.next_stage(req.stage)}
    )


@router.post("", response_model=schemas.RequirementDetail, status_code=201)
def create(body: schemas.RequirementCreate, db: Session = Depends(get_db)):
    part = db.get(Part, body.part_id)
    if part is None:
        raise HTTPException(status_code=404, detail=f"No part '{body.part_id}'.")
    machine = db.get(Machine, body.machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail=f"No machine '{body.machine_id}'.")
    try:
        req = workflow.create_requirement(
            db, machine, body.part_id, body.quantity, body.reason
        )
    except workflow.DoesNotFitError as exc:
        # 409, not 422: the request is well formed and the part is real. What
        # is wrong is the combination, and the message says which part and
        # which model so the caller can see which half to change.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_detail(_get_or_404(db, req.id))


@router.get("", response_model=list[schemas.RequirementOut])
def list_requirements(stage: Stage | None = None, db: Session = Depends(get_db)):
    q = db.query(Requirement).options(
        selectinload(Requirement.part), selectinload(Requirement.machine)
    )
    if stage is not None:
        q = q.filter(Requirement.stage == stage)
    return q.order_by(Requirement.created_at.desc()).all()


@router.get("/{requirement_id}", response_model=schemas.RequirementDetail)
def get_one(requirement_id: int, db: Session = Depends(get_db)):
    return _to_detail(_get_or_404(db, requirement_id))


def _run_action(db, requirement_id, fn, *args):
    req = _get_or_404(db, requirement_id)
    try:
        fn(db, req, *args)
    except workflow.WrongStageError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except workflow.InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_detail(_get_or_404(db, requirement_id))


@router.patch("/{requirement_id}", response_model=schemas.RequirementDetail)
def update(requirement_id: int, body: schemas.RequirementUpdate, db: Session = Depends(get_db)):
    req = _get_or_404(db, requirement_id)
    machine = None
    if body.machine_id is not None:
        machine = db.get(Machine, body.machine_id)
        if machine is None:
            raise HTTPException(status_code=404, detail=f"No machine '{body.machine_id}'.")
    try:
        workflow.update_requirement(db, req, machine, body.quantity, body.reason)
    except workflow.TooLateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except workflow.DoesNotFitError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_detail(_get_or_404(db, requirement_id))


@router.delete("/{requirement_id}", status_code=204)
def cancel(requirement_id: int, db: Session = Depends(get_db)):
    workflow.cancel_requirement(db, _get_or_404(db, requirement_id))
    return None


@router.post("/{requirement_id}/check-availability", response_model=schemas.RequirementDetail)
def check_availability(requirement_id: int, db: Session = Depends(get_db)):
    return _run_action(db, requirement_id, lambda d, r: workflow.check_availability(d, r))


@router.post("/{requirement_id}/order", response_model=schemas.RequirementDetail)
def order(requirement_id: int, body: schemas.OrderAction, db: Session = Depends(get_db)):
    return _run_action(db, requirement_id, workflow.place_order, body.supplier)


@router.post("/{requirement_id}/allocate", response_model=schemas.RequirementDetail)
def allocate(requirement_id: int, db: Session = Depends(get_db)):
    return _run_action(db, requirement_id, lambda d, r: workflow.allocate_inventory(d, r))


@router.post("/{requirement_id}/ship", response_model=schemas.RequirementDetail)
def ship(requirement_id: int, body: schemas.ShipAction, db: Session = Depends(get_db)):
    return _run_action(db, requirement_id, workflow.ship, body.carrier)


@router.post("/{requirement_id}/receive", response_model=schemas.RequirementDetail)
def receive(requirement_id: int, db: Session = Depends(get_db)):
    return _run_action(db, requirement_id, lambda d, r: workflow.receive(d, r))
