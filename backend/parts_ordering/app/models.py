"""
The schema.

STAGES ARE THE GRAPH'S OWN SEVEN NODES
---------------------------------------
The Ground (src/ground/data/graph.ts) already names this process precisely:
Parts Requirement, Part Identification, Parts Availability, Parts Ordering,
Inventory, Shipment, Goods Receipt. `Stage` below is that same sequence, so
a requirement's stage is always one of the words the graph already uses —
the working tool and the diagram that explains it never disagree on what to
call a step.

Requirement and Identification happen together: a reader raises a
requirement by picking a specific cataloged part, so there is nothing left
to "identify" as a separate action. Every other stage is a distinct step the
reader takes deliberately, enforced by PartsRequirementService — see
services/workflow.py for what is and is not a legal transition.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Stage(str, enum.Enum):
    REQUIREMENT_RAISED = "requirement_raised"
    IDENTIFIED = "identified"
    AVAILABILITY_CHECKED = "availability_checked"
    ORDERED = "ordered"
    INVENTORY_ALLOCATED = "inventory_allocated"
    SHIPPED = "shipped"
    RECEIVED = "received"


# The order the stages happen in — also the order they appear on screen.
STAGE_SEQUENCE: list[Stage] = [
    Stage.REQUIREMENT_RAISED,
    Stage.IDENTIFIED,
    Stage.AVAILABILITY_CHECKED,
    Stage.ORDERED,
    Stage.INVENTORY_ALLOCATED,
    Stage.SHIPPED,
    Stage.RECEIVED,
]


class Part(Base):
    """The catalogue. Seeded from src/data/partsCatalogue.js — the same ten
    parts the site's own Parts Showcase section shows, so a part picked here
    is a part a visitor has already seen on the public site.

    The fields beyond name and description are the ones an after-sales parts
    record actually turns on: the part NUMBER a dealer quotes, how long it
    takes to get, which machines it fits, and what it replaced. Engineering
    PLM's own answers to "what is this part" — EBOM/MBOM membership, CAD
    source, design revision — are deliberately absent: they describe
    designing the machine, not keeping one working."""

    __tablename__ = "parts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    part_number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Supersession: after-sales' version of a revision. A part number is not
    # revised in place — a new one replaces it, and the old number has to go
    # on resolving to the new one for as long as machines in the field still
    # carry it.
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("parts.id"), nullable=True
    )
    supersedes: Mapped["Part | None"] = relationship(remote_side=[id])

    stock: Mapped["StockLevel"] = relationship(back_populates="part", uselist=False)
    fitments: Mapped[list["PartFitment"]] = relationship(
        back_populates="part", cascade="all, delete-orphan"
    )
    documents: Mapped[list["PartDocument"]] = relationship(
        back_populates="part", cascade="all, delete-orphan"
    )


class PartFitment(Base):
    """Which machine models a part fits — "where used", asked the way a
    service engineer asks it. The question in the field is never "which
    assembly is this in", it is "will this fit the machine in front of me"."""

    __tablename__ = "part_fitments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), nullable=False)
    machine_model: Mapped[str] = mapped_column(String, nullable=False)
    # Where the part sits on the machine — the nearest thing after-sales has
    # to an assembly, and the words a workshop would use for it.
    assembly: Mapped[str] = mapped_column(String, nullable=False)

    part: Mapped["Part"] = relationship(back_populates="fitments")


class PartDocument(Base):
    """Service bulletins and fitting instructions — the documents that exist
    because a part is being replaced in the field, not because it was
    designed."""

    __tablename__ = "part_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    reference: Mapped[str] = mapped_column(String, nullable=False)

    part: Mapped["Part"] = relationship(back_populates="documents")


class StockLevel(Base):
    """One warehouse row per part. A real multi-warehouse network would make
    this a list; the graph's own Parts Warehouses node is one node, not a
    fleet of them, so one row per part matches what it claims."""

    __tablename__ = "stock_levels"

    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), primary_key=True)
    warehouse: Mapped[str] = mapped_column(String, nullable=False)
    qty_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    part: Mapped["Part"] = relationship(back_populates="stock")


class Customer(Base):
    """The party a machine belongs to.

    Deliberately three fields. A customer here exists so a machine has an
    owner and a fleet can be filtered — not so anyone can manage a customer.
    Contacts, addresses, opportunities and activities are the beginning of a
    CRM, and this is not one.
    """

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)

    machines: Mapped[list["Machine"]] = relationship(back_populates="customer")


class Dealer(Base):
    """Who supports the machine and does the work.

    Same discipline as Customer: enough to attribute a machine and filter a
    list, and no more. The dealer is arrived at from both directions in the
    business — the parts chain delivers to it, the service network staffs it —
    but neither of those needs anything beyond a name today.
    """

    __tablename__ = "dealers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)

    machines: Mapped[list["Machine"]] = relationship(back_populates="dealer")


class MachineStatus(str, enum.Enum):
    """What the machine is doing. Not telemetry — a state somebody sets.

    Recorded now because uptime is what all of after-sales is for, and a
    system that cannot say whether a machine is running cannot say anything
    about it. Nothing in this release changes it automatically.
    """

    WORKING = "working"
    DOWN = "down"
    IN_WORKSHOP = "in_workshop"


class Machine(Base):
    """A machine in the field. The central operational context.

    THE POINT OF THIS ENTITY
    ------------------------
    A requirement used to carry `machine_serial` as free text, and nothing
    validated it. The database still contains "AXZ120", which is not a
    Hitachi model and matches nothing — typed once and never questioned. That
    is the failure this table exists to end.

    `model` is the field that earns it. Part fitment has always been stored
    against a machine model and used only to draw a column; matching
    `Machine.model` to `PartFitment.machine_model` turns twenty-eight rows of
    reference data into a rule the software enforces.

    WHAT IS DELIBERATELY ABSENT
    ---------------------------
    Operating hours, site, configuration, fleet grouping. Hours in particular
    would be the obvious next field and it is not here: it exists to schedule
    preventive maintenance, and no service capability exists yet to schedule.
    A field with nothing reading it is a promise, not a feature.
    """

    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # What is stencilled on the machine, and what a dealer quotes. Unique
    # because two machines with one serial is not a data problem, it is two
    # machines nobody can tell apart.
    serial_number: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    # Matches PartFitment.machine_model. The authority for fitment.
    model: Mapped[str] = mapped_column(String, nullable=False, index=True)

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    dealer_id: Mapped[str] = mapped_column(ForeignKey("dealers.id"), nullable=False)

    # Handover. Where the after-sales relationship starts and warranty runs
    # from.
    commissioned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[MachineStatus] = mapped_column(
        Enum(MachineStatus, native_enum=False), nullable=False, default=MachineStatus.WORKING
    )
    # One date, not a warranty module. It answers "who pays", which is the
    # only question warranty asks of a parts operation.
    warranty_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="machines")
    dealer: Mapped["Dealer"] = relationship(back_populates="machines")
    requirements: Mapped[list["Requirement"]] = relationship(back_populates="machine")


class Requirement(Base):
    """One parts requirement, from being raised to goods receipt."""

    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ONE authoritative relationship to the machine.
    #
    # This was `machine_serial`, a free-text column that nothing validated and
    # nothing joined on. It is gone rather than kept alongside this, because
    # two sources of truth for "which machine" is how a serial and a machine
    # record drift apart — and the serial is still available, derived, through
    # the `machine_serial` property below.
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[Stage] = mapped_column(
        Enum(Stage, native_enum=False), nullable=False, default=Stage.REQUIREMENT_RAISED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Set once availability has actually been checked; None beforehand, so
    # "never checked" and "checked, none on hand" are never confused.
    available_at_check: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    supplier: Mapped[str | None] = mapped_column(String, nullable=True)
    carrier: Mapped[str | None] = mapped_column(String, nullable=True)

    part: Mapped["Part"] = relationship()
    machine: Mapped["Machine"] = relationship(back_populates="requirements")

    @property
    def machine_serial(self) -> str:
        """The serial, read from the machine rather than stored beside it.

        Kept because the interface reads it in five places and a requirement
        without a serial on screen is unrecognisable. Derived, so it cannot
        disagree with the machine it belongs to."""
        return self.machine.serial_number

    @property
    def machine_model(self) -> str:
        return self.machine.model

    events: Mapped[list["StatusEvent"]] = relationship(
        back_populates="requirement", order_by="StatusEvent.at", cascade="all, delete-orphan"
    )


class StatusEvent(Base):
    """One row per stage transition — the timeline a detail view renders.
    Kept separate from `Requirement.stage` (which is always the CURRENT
    stage) so the history survives even though the current stage is a single
    column: the two answer different questions, "where is it now" and "how
    did it get here", and neither can be derived from the other alone."""

    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), nullable=False)
    stage: Mapped[Stage] = mapped_column(Enum(Stage, native_enum=False), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    requirement: Mapped["Requirement"] = relationship(back_populates="events")
