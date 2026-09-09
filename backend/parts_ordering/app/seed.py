"""
Seed data.

The ten parts are src/data/partsCatalogue.js verbatim — the same parts the
site's public Parts Showcase section shows — so this backend and the
marketing page it sits behind never disagree about what Hitachi sells.
Stock levels are invented (the project has no real inventory data), and
deliberately mixed: some parts sit above their reorder point, some below,
and one is at zero, so a fresh install demonstrates both paths through
`check-availability` — in stock, and on backorder — without needing to be
set up by hand first.
"""
from sqlalchemy.orm import Session

from .models import Part, PartDocument, PartFitment, StockLevel

# id, name, category, description — from src/data/partsCatalogue.js
PARTS: list[tuple[str, str, str, str]] = [
    (
        "hydraulic-cylinder",
        "Hydraulic Cylinder",
        "Hydraulics",
        "Delivers the boom, arm and bucket movement the machine works with, "
        "under demanding operating conditions.",
    ),
    (
        "hydraulic-pump",
        "Hydraulic Pump",
        "Hydraulics",
        "Supplies the flow that every hydraulic circuit on the machine depends on.",
    ),
    (
        "diesel-engine",
        "Diesel Engine",
        "Powertrain",
        "The complete engine assembly — the source of every kilowatt the machine puts to work.",
    ),
    (
        "reduction-gear",
        "Reduction Gear",
        "Drivetrain",
        "Turns motor speed into the torque the tracks and the upper structure need to move.",
    ),
    (
        "swing-bearing",
        "Swing Bearing",
        "Upper Structure",
        "The ring the whole upper structure turns on, carrying load in several directions at once.",
    ),
    (
        "bucket",
        "Bucket",
        "Front Attachment",
        "The working edge of the machine, where every cycle of digging force is finally delivered.",
    ),
    (
        "track-assembly",
        "Track Assembly",
        "Undercarriage",
        "Shoes, links, rollers and idler — the undercarriage that carries the machine over the ground.",
    ),
    (
        "filters",
        "Genuine Filters",
        "Maintenance Parts",
        "Fuel and oil filtration made to Hitachi specification — the simplest protection on the machine.",
    ),
    (
        "controller",
        "Machine Controller",
        "Electronics",
        "The control unit that coordinates the machine's systems and reports what it finds.",
    ),
    (
        "fuel-injection-pump",
        "Fuel Injection Pump",
        "Engine System",
        "Meters and delivers fuel to the engine on every stroke of its working cycle.",
    ),
    # The eleventh part, and the only one not in src/data/partsCatalogue.js:
    # the number the hydraulic pump above REPLACED.
    #
    # A superseded part has to exist as a row — supersedes_id is a foreign
    # key, and more importantly the old number has to go on resolving for as
    # long as machines in the field still carry it. It is deliberately kept
    # out of the catalogue listing (see list_parts) rather than deleted:
    # findable by number, not orderable.
    (
        "hydraulic-pump-911118002",
        "Hydraulic Pump",
        "Hydraulics",
        "The earlier hydraulic pump number, replaced by 911-118-004. Machines "
        "in the field still carry this number on their labels, so it goes on "
        "resolving; it is no longer supplied against new orders.",
    ),
]

# part_id -> (warehouse, qty_on_hand, reorder_point)
STOCK: dict[str, tuple[str, int, int]] = {
    "hydraulic-cylinder": ("Rotterdam Central", 6, 4),
    "hydraulic-pump": ("Rotterdam Central", 14, 6),
    "diesel-engine": ("Rotterdam Central", 1, 2),  # below reorder point
    "reduction-gear": ("Antwerp Regional", 9, 5),
    "swing-bearing": ("Antwerp Regional", 0, 2),  # on backorder
    "bucket": ("Rotterdam Central", 11, 4),
    "track-assembly": ("Antwerp Regional", 3, 4),  # at the edge
    "filters": ("Rotterdam Central", 48, 20),
    "controller": ("Rotterdam Central", 5, 3),
    "fuel-injection-pump": ("Antwerp Regional", 2, 3),  # below reorder point
}


# part_id -> (part_number, lead_time_days)
# Numbers follow Hitachi's own shape — a nine-digit figure grouped in threes
# — because a dealer quotes a part number, not a slug. They are invented:
# this project has no access to the real catalogue.
IDENTITY: dict[str, tuple[str, int]] = {
    "hydraulic-cylinder": ("911-204-001", 21),
    "hydraulic-pump": ("911-118-004", 28),
    "diesel-engine": ("902-001-010", 63),
    "reduction-gear": ("914-330-002", 35),
    "swing-bearing": ("913-507-006", 42),
    "bucket": ("921-880-014", 14),
    "track-assembly": ("918-644-003", 30),
    "filters": ("905-012-100", 3),
    "controller": ("930-770-021", 24),
    "fuel-injection-pump": ("902-455-009", 45),
    # Zero lead time because it cannot be ordered at all — see PARTS above.
    "hydraulic-pump-911118002": ("911-118-002", 0),
}

# The Zaxis-7 range. ZX350LC-7 is the machine the site's own hero identifies
# (src/data/machineData.js); the rest of the range is around it.
MODELS = ["ZX210-7", "ZX250LC-7", "ZX350LC-7", "ZX490LCH-7"]

# part_id -> (assembly it sits in, models it fits)
FITMENT: dict[str, tuple[str, list[str]]] = {
    "hydraulic-cylinder": ("Front attachment — boom", ["ZX250LC-7", "ZX350LC-7", "ZX490LCH-7"]),
    "hydraulic-pump": ("Hydraulic system — main pump", MODELS),
    "diesel-engine": ("Powertrain — engine assembly", ["ZX350LC-7", "ZX490LCH-7"]),
    "reduction-gear": ("Travel drive", ["ZX250LC-7", "ZX350LC-7"]),
    "swing-bearing": ("Upper structure — swing circle", ["ZX350LC-7", "ZX490LCH-7"]),
    "bucket": ("Front attachment — bucket", MODELS),
    "track-assembly": ("Undercarriage", ["ZX250LC-7", "ZX350LC-7", "ZX490LCH-7"]),
    "filters": ("Maintenance — filtration", MODELS),
    "controller": ("Electrical — control unit", ["ZX350LC-7", "ZX490LCH-7"]),
    "fuel-injection-pump": ("Engine — fuel system", ["ZX350LC-7", "ZX490LCH-7"]),
}

# part_id -> [(title, doc_type, reference)]
DOCUMENTS: dict[str, list[tuple[str, str, str]]] = {
    "swing-bearing": [
        ("Swing bearing bolt torque sequence", "Fitting instruction", "FI-913-507-A"),
        ("Swing bearing wear check interval", "Service bulletin", "SB-2024-118"),
    ],
    "filters": [("Filter change — 500 hour service", "Fitting instruction", "FI-905-012-C")],
    "hydraulic-pump": [
        ("Pump commissioning and bleed procedure", "Fitting instruction", "FI-911-118-B"),
    ],
    "controller": [
        ("Controller software level check", "Service bulletin", "SB-2025-004"),
    ],
    "fuel-injection-pump": [
        ("Injection pump timing on refit", "Fitting instruction", "FI-902-455-A"),
    ],
}

# Supersession: the newer part id -> the older one it replaces. One pair,
# because one is enough to show the behaviour honestly and inventing a
# catalogue full of them would be inventing history.
SUPERSEDES: dict[str, str] = {
    "hydraulic-pump": "hydraulic-pump-911118002",
}


def seed(db: Session) -> None:
    """Idempotent: safe to call every startup. Never overwrites what is
    already there, so restarting the server does not reset stock that has
    been drawn down.

    Each table is checked SEPARATELY, and that matters. Gating all of this
    on `parts` being empty — the obvious way to write it — meant an existing
    database never received seed data added later: fitment and documents
    arrived in a subsequent migration, and every install that already had
    parts in it silently skipped them, leaving part records that claimed to
    fit nothing at all.

    `parts` itself is now checked ROW BY ROW rather than table by table,
    because the same lesson applied to it one level down. A superseded
    predecessor and its supersession link were added to this file after ten
    parts were already on disk, and "is the parts table empty" is false the
    moment there is one part in it — so every existing install would have
    gone on showing ten parts and an empty Supersedes row for ever, exactly
    the failure this docstring already describes. Adding a part here now
    reaches databases that already exist.
    """
    _seed_parts(db)
    if db.query(StockLevel).first() is None:
        _seed_stock(db)
    if db.query(PartFitment).first() is None:
        _seed_fitment(db)
    if db.query(PartDocument).first() is None:
        _seed_documents(db)
    # Row by row, for the same reason parts are — kits were added to this file
    # long after databases existed in the wild.
    _seed_kits(db)
    db.commit()


def _seed_parts(db: Session) -> None:
    """Inserts the parts that are not there yet, and leaves the ones that are
    alone — this never overwrites a row, so nothing a running system has
    changed is reset by a restart."""
    existing = {pid for (pid,) in db.query(Part.id)}
    for part_id, name, category, description in PARTS:
        if part_id in existing:
            continue
        part_number, lead_time = IDENTITY[part_id]
        db.add(
            Part(
                id=part_id,
                part_number=part_number,
                name=name,
                category=category,
                description=description,
                lead_time_days=lead_time,
            )
        )
    db.flush()

    # Applied every time for the same reason, and only where it is not
    # already set: the link is what makes the old number resolve, and it was
    # authored after the rows it joins.
    for newer, older in SUPERSEDES.items():
        part = db.get(Part, newer)
        if part is not None and part.supersedes_id is None and db.get(Part, older) is not None:
            part.supersedes_id = older


def _seed_stock(db: Session) -> None:
    for part_id, (warehouse, qty, reorder) in STOCK.items():
        db.add(
            StockLevel(
                part_id=part_id, warehouse=warehouse, qty_on_hand=qty, reorder_point=reorder
            )
        )


def _seed_fitment(db: Session) -> None:
    for part_id, (assembly, models) in FITMENT.items():
        for model in models:
            db.add(PartFitment(part_id=part_id, machine_model=model, assembly=assembly))


def _seed_documents(db: Session) -> None:
    for part_id, docs in DOCUMENTS.items():
        for title, doc_type, reference in docs:
            db.add(
                PartDocument(part_id=part_id, title=title, doc_type=doc_type, reference=reference)
            )


# ---------------------------------------------------------------- service kits
#
# id, code, name, interval_hours, description
#
# INVENTED, like the stock levels and the part numbers above — this project
# has no access to Hitachi's real service schedules. What is NOT invented is
# what each one is built from: every kit below is composed only of parts this
# catalogue actually holds, fits only models those parts have real fitment
# records against, and is anchored on a fitting instruction or service
# bulletin already attached to one of its own lines. A kit calling for a part
# nobody stocks, or for a machine the part does not fit, would be a lie the
# rest of the system could not catch.
#
# One is scheduled and three are repairs. That mix is the honest shape of a
# parts operation: the interval work is what can be forecast, and the job
# kits are what stops an engineer ordering four things one at a time and
# discovering the fifth on the day.
KITS: list[tuple[str, str, str, int | None, str]] = [
    (
        "svc-500h",
        "SVC-500",
        "500-hour service",
        500,
        "Scheduled filtration change. The interval service every machine in the "
        "range reaches first, and the one most often let slip.",
    ),
    (
        "kit-swing-bearing",
        "KIT-913-507",
        "Swing bearing overhaul",
        None,
        "Replacing the ring the upper structure turns on. Carries a filter change "
        "because the swing circuit is opened during the work.",
    ),
    (
        "kit-hydraulic-pump",
        "KIT-911-118",
        "Hydraulic pump replacement",
        None,
        "Main pump replacement and recommissioning. Twice the filtration, because "
        "the system is drained and bled on refit.",
    ),
    (
        "kit-undercarriage",
        "KIT-918-644",
        "Undercarriage rebuild",
        None,
        "Both track assemblies together — replacing one side alone leaves the "
        "machine tracking unevenly and wears the new side early.",
    ),
]

# kit_id -> [(part_id, quantity)]
KIT_LINES: dict[str, list[tuple[str, int]]] = {
    "svc-500h": [("filters", 1)],
    "kit-swing-bearing": [("swing-bearing", 1), ("filters", 1)],
    "kit-hydraulic-pump": [("hydraulic-pump", 1), ("filters", 2)],
    "kit-undercarriage": [("track-assembly", 2), ("filters", 1)],
}

# kit_id -> the models it applies to. Every one of these is a model the kit's
# own parts carry a real fitment record against — see FITMENT above.
KIT_MODELS: dict[str, list[str]] = {
    "svc-500h": MODELS,
    "kit-swing-bearing": ["ZX350LC-7", "ZX490LCH-7"],
    "kit-hydraulic-pump": MODELS,
    "kit-undercarriage": ["ZX250LC-7", "ZX350LC-7", "ZX490LCH-7"],
}


def _seed_kits(db: Session) -> None:
    from .models import ServiceKit, ServiceKitLine, ServiceKitModel

    existing = {kid for (kid,) in db.query(ServiceKit.id)}
    for kit_id, code, name, interval, description in KITS:
        if kit_id in existing:
            continue
        db.add(
            ServiceKit(
                id=kit_id,
                code=code,
                name=name,
                description=description,
                interval_hours=interval,
            )
        )
        for part_id, qty in KIT_LINES[kit_id]:
            db.add(ServiceKitLine(kit_id=kit_id, part_id=part_id, quantity=qty))
        for model in KIT_MODELS[kit_id]:
            db.add(ServiceKitModel(kit_id=kit_id, machine_model=model))
