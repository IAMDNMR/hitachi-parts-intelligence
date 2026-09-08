"""part record: number, lead time, fitment, documents, supersession

Autogenerate's first draft added `part_number` and `lead_time_days` as NOT
NULL in one step, which fails the moment the table has a row in it — there
is no value to put in the existing ones. It also emitted unnamed constraints,
which SQLite cannot add to an existing table at all.

So the columns arrive nullable, are backfilled from the same numbers
app/seed.py uses, and are tightened to NOT NULL afterwards inside a batch
operation (SQLite's only way to alter a column: rebuild the table). The
result runs against a populated database, which is the only kind that will
ever matter once this is deployed.

Revision ID: 1c8aa85f0226
Revises: 25cee08f34a5
Create Date: 2026-09-07 15:48:00.218057
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "1c8aa85f0226"
down_revision: Union[str, Sequence[str], None] = "25cee08f34a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Kept in step with IDENTITY in app/seed.py. Duplicated deliberately: a
# migration has to describe the database as it was at this point in history,
# and must not start importing application code that will keep changing
# underneath it.
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
}


def upgrade() -> None:
    op.create_table(
        "part_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("part_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("doc_type", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], name="fk_part_documents_part"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "part_fitments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("part_id", sa.String(), nullable=False),
        sa.Column("machine_model", sa.String(), nullable=False),
        sa.Column("assembly", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], name="fk_part_fitments_part"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 1. Nullable, so existing rows are legal while they are still empty.
    op.add_column("parts", sa.Column("part_number", sa.String(), nullable=True))
    op.add_column("parts", sa.Column("lead_time_days", sa.Integer(), nullable=True))
    op.add_column("parts", sa.Column("supersedes_id", sa.String(), nullable=True))

    # 2. Backfill. Anything not in IDENTITY — a part added by hand — still
    #    gets a value, so step 3 cannot fail on it.
    parts = sa.table(
        "parts",
        sa.column("id", sa.String),
        sa.column("part_number", sa.String),
        sa.column("lead_time_days", sa.Integer),
    )
    for part_id, (number, lead_time) in IDENTITY.items():
        op.execute(
            parts.update()
            .where(parts.c.id == op.inline_literal(part_id))
            .values(part_number=number, lead_time_days=lead_time)
        )
    op.execute(
        parts.update()
        .where(parts.c.part_number.is_(None))
        .values(part_number=parts.c.id, lead_time_days=0)
    )

    # 3. Tighten, and add the constraints — batch mode because SQLite has to
    #    rebuild the table to do any of this.
    with op.batch_alter_table("parts") as batch:
        batch.alter_column("part_number", existing_type=sa.String(), nullable=False)
        batch.alter_column("lead_time_days", existing_type=sa.Integer(), nullable=False)
        batch.create_unique_constraint("uq_parts_part_number", ["part_number"])
        batch.create_foreign_key("fk_parts_supersedes", "parts", ["supersedes_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("parts") as batch:
        batch.drop_constraint("fk_parts_supersedes", type_="foreignkey")
        batch.drop_constraint("uq_parts_part_number", type_="unique")
        batch.drop_column("supersedes_id")
        batch.drop_column("lead_time_days")
        batch.drop_column("part_number")
    op.drop_table("part_fitments")
    op.drop_table("part_documents")
