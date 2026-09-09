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


class Requirement(Base):
    """One parts requirement, from being raised to goods receipt."""

    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_serial: Mapped[str] = mapped_column(String, nullable=False)
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

    # Set when this line came from a service kit rather than from someone
    # noticing a failure. Worth recording because it is the difference between
    # planned and reactive demand — and because five requirements raised from
    # one service belong to each other and should be able to say so.
    kit_id: Mapped[str | None] = mapped_column(
        ForeignKey("service_kits.id"), nullable=True
    )

    part: Mapped["Part"] = relationship()
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


class ServiceKit(Base):
    """A service as one orderable thing.

    A five-hundred-hour service is not a part, it is a job — and the parts it
    consumes are ordered together, against a schedule, before anything has
    failed. Ordering them one at a time is how the tool worked until now, and
    it is both slower and wrong: the five lines of a service belong to each
    other, and a service that arrives four-fifths complete has not arrived.

    This is also the difference between the two halves of a parts operation.
    Everything else in this database is reactive — something broke, someone
    raised a requirement. A kit is planned demand: it is known in advance,
    it can be forecast, and it is most of what a healthy after-sales parts
    business actually sells.

    `interval_hours` is what separates the two kinds. A kit with one is
    scheduled maintenance and recurs for the life of the machine; a kit
    without one is a repair — the parts a particular job needs, gathered so
    nobody has to remember the list.
    """

    __tablename__ = "service_kits"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Set for scheduled maintenance, null for a repair kit. Machine hours are
    # what a service interval is counted in — not dates — because a machine
    # that works two shifts reaches its service twice as fast.
    interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    lines: Mapped[list["ServiceKitLine"]] = relationship(
        back_populates="kit", cascade="all, delete-orphan"
    )
    models: Mapped[list["ServiceKitModel"]] = relationship(
        back_populates="kit", cascade="all, delete-orphan"
    )


class ServiceKitLine(Base):
    """One part, and how many of it the service needs."""

    __tablename__ = "service_kit_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kit_id: Mapped[str] = mapped_column(ForeignKey("service_kits.id"), nullable=False)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    kit: Mapped["ServiceKit"] = relationship(back_populates="lines")
    part: Mapped["Part"] = relationship()


class ServiceKitModel(Base):
    """Which machines a kit is for.

    Kept separate from the parts' own fitment records on purpose. A part can
    fit a machine without the machine's service calling for it — the kit says
    what the SERVICE needs, which is a different statement from what the part
    will bolt on to.
    """

    __tablename__ = "service_kit_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kit_id: Mapped[str] = mapped_column(ForeignKey("service_kits.id"), nullable=False)
    machine_model: Mapped[str] = mapped_column(String, nullable=False)

    kit: Mapped["ServiceKit"] = relationship(back_populates="models")
