"""Request and response shapes. Kept separate from the ORM models (models.py)
so a column can be renamed internally without silently changing the API, and
so a response can include things — like `next_actions` — that are computed,
not stored."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import MachineStatus, Stage


class PartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    part_number: str
    name: str
    category: str
    description: str


class FitmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    machine_model: str
    assembly: str


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    doc_type: str
    reference: str


class PartUsageOut(BaseModel):
    """One requirement this part has been raised against — the after-sales
    reading of "where used": not which assembly contains it, but which
    machines have actually needed it."""

    requirement_id: int
    # The machine as a record, so "machines that needed it" on a part record
    # is a link back to Machine 360 rather than a serial printed as text.
    # This is the second half of the first real bidirectional relationship in
    # the product: Machine → Parts, and Part → Machines.
    machine_id: str
    machine_serial: str
    machine_model: str
    quantity: int
    stage: "Stage"
    created_at: datetime


class PartRow(PartOut):
    """A part as the catalogue table shows it.

    Wider than PartOut and narrower than PartDetail, because the two
    questions a catalogue row has to answer beyond "what is it" — what does
    it fit, and can I have one — cannot be answered from PartOut, and
    answering them by fetching the full record of every part on the page is
    ten round trips to render one table.

    `machines` is the distinct machine models this part is listed against,
    in the order they are stored; the assembly each fitment names is left to
    the part record, where there is room to say it.
    """

    lead_time_days: int
    machines: list[str]
    stock: "StockOut | None"


class PartDetail(PartOut):
    lead_time_days: int
    stock: "StockOut | None"
    fitments: list[FitmentOut]
    documents: list[DocumentOut]
    supersedes: PartOut | None = None
    # The other direction, and the one that matters when the record being
    # read IS the dead number. `supersedes` answers "what did this replace";
    # this answers "what do I order instead", which is the only question
    # someone holding a superseded label actually has. Computed, not stored —
    # it is the same single foreign key read backwards.
    superseded_by: PartOut | None = None


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    warehouse: str
    qty_on_hand: int
    reorder_point: int


class RequirementCreate(BaseModel):
    # A machine, not a serial. There is no path that creates a requirement
    # against a machine the system does not know about.
    machine_id: str
    part_id: str
    quantity: int = Field(gt=0, le=999)
    reason: str = Field(min_length=1, max_length=500)


class RequirementUpdate(BaseModel):
    """Every field optional: a PATCH says what changed, not what the record
    should now consist of. Omitting a field leaves it alone; that is the
    difference between editing the quantity and accidentally blanking the
    reason because the form did not send it."""

    # Re-pointing at a different machine is allowed while the requirement is
    # still only a statement of intent, and is re-validated against fitment.
    machine_id: str | None = None
    quantity: int | None = Field(default=None, gt=0, le=999)
    reason: str | None = Field(default=None, min_length=1, max_length=500)


class StockAdjust(BaseModel):
    delta: int = Field(description="Positive receives stock in, negative takes it out.")
    note: str | None = Field(default=None, max_length=200)


class OrderAction(BaseModel):
    supplier: str | None = Field(default=None, max_length=120)


class ShipAction(BaseModel):
    carrier: str | None = Field(default=None, max_length=120)


class StatusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: Stage
    at: datetime
    note: str | None = None


class AvailabilityResult(BaseModel):
    """What `check-availability` reports, distinct from the requirement
    record itself: this is the answer to "is there enough", the requirement
    is the thing being asked about."""

    part_id: str
    warehouse: str
    qty_on_hand: int
    quantity_requested: int
    available: bool


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: str
    # Derived from the machine — see the property on the model. Kept because
    # the interface reads it in several places and a requirement without a
    # serial on screen is unrecognisable.
    machine_serial: str
    machine_model: str
    part: PartOut
    quantity: int
    reason: str
    stage: Stage
    created_at: datetime
    available_at_check: bool | None = None
    supplier: str | None = None
    carrier: str | None = None


class RequirementDetail(RequirementOut):
    events: list[StatusEventOut]
    # The stage this requirement can legally move to next, or none if it has
    # reached Goods Receipt. The frontend uses this to decide which single
    # action button to offer — the state machine's rules live in one place
    # (services/workflow.py) rather than being duplicated in the UI.
    next_stage: Stage | None


# --------------------------------------------------------------- machines


class CustomerOut(BaseModel):
    """Context, not a customer record. Three fields on purpose."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    region: str


class DealerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    region: str


class MachineRow(BaseModel):
    """A machine as the fleet list shows it.

    Carries `open_requirements` because the question a list of machines has to
    answer at a glance is which ones are waiting on something — and counting
    it here is one query against many, rather than one request per row.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    serial_number: str
    model: str
    status: MachineStatus
    commissioned_at: datetime
    warranty_end: datetime | None
    customer: CustomerOut
    dealer: DealerOut
    open_requirements: int = 0
    # Derived from warranty_end against today, so the list can be filtered on
    # the state rather than on a date every reader has to compare themselves.
    in_warranty: bool = False


class MachineDetail(MachineRow):
    """Machine 360. Everything Release 1 can honestly say about one machine.

    No service history, no alerts, no orders — those belong to entities that
    do not exist yet, and a panel headed "Service history" over an empty list
    promises a capability rather than reporting one.
    """

    fitting_parts: int = 0


class MachineCreate(BaseModel):
    serial_number: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=64)
    customer_id: str
    dealer_id: str
    commissioned_at: datetime | None = None
    warranty_end: datetime | None = None
    status: MachineStatus = MachineStatus.WORKING


class MachineUpdate(BaseModel):
    """Only what an operator legitimately changes after commissioning.

    Serial and model are absent deliberately: a machine's identity and what it
    is are not editable attributes, and the model is what fitment is validated
    against — letting it be changed would let somebody edit their way around
    the rule on requirements already raised.
    """

    status: MachineStatus | None = None
    dealer_id: str | None = None
    warranty_end: datetime | None = None


class MachinePartRow(PartOut):
    """A part that fits this machine, with the two facts that decide whether
    it can be had."""

    lead_time_days: int
    assembly: str
    stock: "StockOut | None"


class MachineRequirementRow(BaseModel):
    """One line of a machine's parts history — derived from requirements, not
    from a separate history table."""

    id: int
    part: PartOut
    quantity: int
    stage: Stage
    reason: str
    created_at: datetime
