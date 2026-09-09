"""
The state machine.

Every route that moves a requirement forward calls through here rather than
setting `.stage` itself, so there is exactly one place that decides what a
legal move is. A route cannot accidentally ship a requirement that was never
ordered — WrongStageError stops it, with the requirement's actual stage and
the stage the caller wanted, so the error is diagnosable from the response
alone rather than from reading the code.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..models import (
    STAGE_SEQUENCE,
    Machine,
    PartFitment,
    Requirement,
    Stage,
    StatusEvent,
    StockLevel,
)


class WrongStageError(Exception):
    def __init__(self, requirement_id: int, current: Stage, required: Stage):
        self.requirement_id = requirement_id
        self.current = current
        self.required = required
        super().__init__(
            f"Requirement {requirement_id} is at '{current.value}'; "
            f"this action needs '{required.value}'."
        )


class InsufficientStockError(Exception):
    def __init__(self, part_id: str, on_hand: int, requested: int):
        self.part_id = part_id
        self.on_hand = on_hand
        self.requested = requested
        super().__init__(
            f"Only {on_hand} of '{part_id}' on hand; {requested} requested. "
            "Order more before allocating."
        )


def next_stage(stage: Stage) -> Stage | None:
    i = STAGE_SEQUENCE.index(stage)
    return STAGE_SEQUENCE[i + 1] if i + 1 < len(STAGE_SEQUENCE) else None


def _require_stage(req: Requirement, expected: Stage) -> None:
    if req.stage != expected:
        raise WrongStageError(req.id, req.stage, expected)


def _advance(db: Session, req: Requirement, to: Stage, note: str | None = None) -> Requirement:
    req.stage = to
    db.add(StatusEvent(requirement_id=req.id, stage=to, note=note))
    db.commit()
    db.refresh(req)
    return req


class DoesNotFitError(Exception):
    """The part is not listed against this machine's model.

    Raised rather than warned about, and never resolved by quietly offering a
    different part: substituting one component for another on somebody else's
    machine is the one mistake a parts system must not make on its own
    initiative. The message names the model and what the part does fit, so the
    person raising it can see whether they picked the wrong part or the wrong
    machine.
    """

    def __init__(self, part_id: str, model: str, fits: list[str]):
        self.part_id = part_id
        self.model = model
        self.fits = fits
        listed = ", ".join(fits) if fits else "no machine model in this catalogue"
        super().__init__(
            f"Part '{part_id}' is not listed as fitting a {model}. It fits: {listed}."
        )


def assert_fits(db: Session, machine: Machine, part_id: str) -> None:
    """The rule that makes fitment data mean something.

    Fitment has always been stored and has never been enforced — twenty-eight
    rows used to draw a column and populate a filter. This is the whole of the
    change: a requirement may only name a part the catalogue lists against the
    machine's own model.
    """
    fits = [
        m
        for (m,) in db.query(PartFitment.machine_model)
        .filter(PartFitment.part_id == part_id)
        .distinct()
    ]
    if machine.model not in fits:
        raise DoesNotFitError(part_id, machine.model, sorted(fits))


@dataclass
class CreatedRequirement:
    requirement: Requirement


def create_requirement(
    db: Session, machine: Machine, part_id: str, quantity: int, reason: str
) -> Requirement:
    """Raising a requirement and identifying the part are one action here —
    see the module docstring in models.py for why. Two events are still
    recorded, because the timeline should read the way the graph does, one
    line per named stage, not one line that skips one of the seven names.

    The machine is passed as a record rather than a serial, so there is no
    path into this function that bypasses the fitment check below."""
    assert_fits(db, machine, part_id)
    req = Requirement(
        machine_id=machine.id,
        part_id=part_id,
        quantity=quantity,
        reason=reason,
        stage=Stage.IDENTIFIED,
    )
    db.add(req)
    db.flush()  # assigns req.id without ending the transaction
    db.add(StatusEvent(requirement_id=req.id, stage=Stage.REQUIREMENT_RAISED))
    db.add(StatusEvent(requirement_id=req.id, stage=Stage.IDENTIFIED, note=f"Part: {part_id}"))
    db.commit()
    db.refresh(req)
    return req


def check_availability(db: Session, req: Requirement) -> tuple[Requirement, StockLevel]:
    _require_stage(req, Stage.IDENTIFIED)
    stock = db.get(StockLevel, req.part_id)
    if stock is None:
        raise LookupError(f"No stock record for part '{req.part_id}'.")
    available = stock.qty_on_hand >= req.quantity
    req.available_at_check = available
    note = (
        f"{stock.qty_on_hand} on hand at {stock.warehouse}; "
        f"{'sufficient' if available else 'short'} for {req.quantity} requested."
    )
    return _advance(db, req, Stage.AVAILABILITY_CHECKED, note), stock


def place_order(db: Session, req: Requirement, supplier: str | None) -> Requirement:
    _require_stage(req, Stage.AVAILABILITY_CHECKED)
    req.supplier = supplier or ("Internal stock" if req.available_at_check else None)
    note = f"Ordered from {req.supplier}" if req.supplier else "Sales order raised."
    return _advance(db, req, Stage.ORDERED, note)


def allocate_inventory(db: Session, req: Requirement) -> Requirement:
    _require_stage(req, Stage.ORDERED)
    stock = db.get(StockLevel, req.part_id)
    if stock is None or stock.qty_on_hand < req.quantity:
        raise InsufficientStockError(
            req.part_id, stock.qty_on_hand if stock else 0, req.quantity
        )
    stock.qty_on_hand -= req.quantity
    note = f"{req.quantity} drawn down; {stock.qty_on_hand} remaining at {stock.warehouse}."
    return _advance(db, req, Stage.INVENTORY_ALLOCATED, note)


def ship(db: Session, req: Requirement, carrier: str | None) -> Requirement:
    _require_stage(req, Stage.INVENTORY_ALLOCATED)
    req.carrier = carrier
    note = f"Shipped via {carrier}" if carrier else "Shipped."
    return _advance(db, req, Stage.SHIPPED, note)


def receive(db: Session, req: Requirement) -> Requirement:
    _require_stage(req, Stage.SHIPPED)
    return _advance(db, req, Stage.RECEIVED, "Arrival confirmed against what was sent.")


class TooLateError(Exception):
    """Raised when an edit is attempted after the point where it would make
    the record disagree with what physically happened."""

    def __init__(self, requirement_id: int, stage: Stage):
        self.requirement_id = requirement_id
        self.stage = stage
        super().__init__(
            f"Requirement {requirement_id} is at '{stage.value}'. Stock has already been "
            "drawn down against it, so what was asked for can no longer be changed — "
            "cancel it and raise a new one."
        )


# Editing is allowed while the requirement is still only a statement of
# intent. Once inventory has been allocated the quantity has been physically
# taken off a shelf, and quietly changing the number here would leave the
# record and the warehouse disagreeing.
EDITABLE_STAGES = {Stage.IDENTIFIED, Stage.AVAILABILITY_CHECKED, Stage.ORDERED}


def update_requirement(
    db: Session,
    req: Requirement,
    machine: Machine | None,
    quantity: int | None,
    reason: str | None,
) -> Requirement:
    """Moving a requirement to a different machine is a machine change, not a
    text edit.

    The serial used to be editable as a string, which meant a requirement
    could be pointed at a machine that did not exist and — once fitment became
    a rule — at a machine the part does not fit. Re-pointing it now takes a
    real machine and is re-validated against it, so there is no way to edit
    around the check that creation enforces."""
    if req.stage not in EDITABLE_STAGES:
        raise TooLateError(req.id, req.stage)

    changed: list[str] = []
    if machine is not None and machine.id != req.machine_id:
        assert_fits(db, machine, req.part_id)
        changed.append(f"machine {req.machine.serial_number} → {machine.serial_number}")
        req.machine_id = machine.id
        req.machine = machine
    if quantity is not None and quantity != req.quantity:
        changed.append(f"quantity {req.quantity} → {quantity}")
        req.quantity = quantity
        # The old availability answer was about a different number, so it is
        # no longer an answer. Sending it back to be checked again is more
        # honest than leaving a stale "yes" attached to a bigger order.
        if req.stage != Stage.IDENTIFIED:
            req.available_at_check = None
            req.stage = Stage.IDENTIFIED
            changed.append("availability must be re-checked")
    if reason is not None and reason != req.reason:
        changed.append("reason amended")
        req.reason = reason

    if changed:
        db.add(
            StatusEvent(
                requirement_id=req.id, stage=req.stage, note="Edited: " + "; ".join(changed)
            )
        )
    db.commit()
    db.refresh(req)
    return req


def cancel_requirement(db: Session, req: Requirement) -> None:
    """Cancelling is not just deleting a row.

    If stock was allocated and the part never left, it goes back on the
    shelf — otherwise cancelling a requirement would quietly lose inventory.
    Once it has been received the part is on the machine, so there is nothing
    to give back and the stock is left alone.
    """
    allocated_not_received = req.stage in {Stage.INVENTORY_ALLOCATED, Stage.SHIPPED}
    if allocated_not_received:
        stock = db.get(StockLevel, req.part_id)
        if stock is not None:
            stock.qty_on_hand += req.quantity
    db.delete(req)
    db.commit()
