"""Request and response shapes. Kept separate from the ORM models (models.py)
so a column can be renamed internally without silently changing the API, and
so a response can include things — like `next_actions` — that are computed,
not stored."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import Stage


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
    machine_serial: str
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
    machine_serial: str = Field(min_length=1, max_length=64)
    part_id: str
    quantity: int = Field(gt=0, le=999)
    reason: str = Field(min_length=1, max_length=500)


class RequirementUpdate(BaseModel):
    """Every field optional: a PATCH says what changed, not what the record
    should now consist of. Omitting a field leaves it alone; that is the
    difference between editing the quantity and accidentally blanking the
    reason because the form did not send it."""

    machine_serial: str | None = Field(default=None, min_length=1, max_length=64)
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
    machine_serial: str
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


class KitLineOut(BaseModel):
    """One part in a kit, with what the shelf says about covering it."""

    part: PartOut
    quantity: int
    lead_time_days: int
    stock: "StockOut | None"
    # Whether the shelf can cover THIS line's quantity — not whether the part
    # exists in stock at all. A kit calling for two of something with one on
    # hand is short, and saying "in stock" would be true of the part and
    # useless about the service.
    covered: bool


class KitRow(BaseModel):
    """A kit as the list shows it."""

    id: str
    code: str
    name: str
    description: str
    interval_hours: int | None
    machines: list[str]
    line_count: int
    # Every line coverable from stock today. The one number a planner wants
    # before committing to a service date.
    ready: bool
    # The longest lead time in the kit. A service is not available until its
    # slowest line is — an average would flatter it.
    longest_lead_days: int


class KitDetail(KitRow):
    lines: list[KitLineOut]


class KitRaise(BaseModel):
    machine_serial: str = Field(min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=500)
