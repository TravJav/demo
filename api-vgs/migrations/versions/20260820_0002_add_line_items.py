"""add line items

Revision ID: 202608200002
Revises: 202608200001
Create Date: 2026-08-20 00:02:00.000000
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "202608200002"
down_revision: str | Sequence[str] | None = "202608200001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "line_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("vacation_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vacation_id"], ["vacations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_line_items_external_reference"),
        "line_items",
        ["external_reference"],
    )
    op.create_index(
        "ix_line_items_source_external_reference",
        "line_items",
        ["source", "external_reference"],
    )
    op.create_index(op.f("ix_line_items_vacation_id"), "line_items", ["vacation_id"])

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("line_item_id", sa.Uuid(), nullable=True))

    backfill_line_items_from_transactions()

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_index(op.f("ix_transactions_line_item"))
        batch_op.alter_column(
            "line_item_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_transactions_line_item_id_line_items",
            "line_items",
            ["line_item_id"],
            ["id"],
        )
        batch_op.create_index(
            op.f("ix_transactions_line_item_id"),
            ["line_item_id"],
        )
        batch_op.drop_column("line_item")


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("line_item", sa.Uuid(), nullable=True))

    backfill_transactions_from_line_items()

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_index(op.f("ix_transactions_line_item_id"))
        batch_op.drop_constraint(
            "fk_transactions_line_item_id_line_items",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "line_item",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_transactions_line_item_vacations",
            "vacations",
            ["line_item"],
            ["id"],
        )
        batch_op.create_index(op.f("ix_transactions_line_item"), ["line_item"])
        batch_op.drop_column("line_item_id")

    op.drop_index(op.f("ix_line_items_vacation_id"), "line_items")
    op.drop_index("ix_line_items_source_external_reference", "line_items")
    op.drop_index(op.f("ix_line_items_external_reference"), "line_items")
    op.drop_table("line_items")


def backfill_line_items_from_transactions() -> None:
    connection = op.get_bind()
    transactions = transactions_table()
    vacations = vacations_table()
    line_items = line_items_table()
    rows = connection.execute(
        sa.select(
            transactions.c.id.label("transaction_id"),
            transactions.c.line_item.label("vacation_id"),
            vacations.c.package_name.label("package_name"),
        ).select_from(
            transactions.outerjoin(
                vacations,
                transactions.c.line_item == vacations.c.id,
            ),
        ),
    ).mappings()

    for row in rows:
        line_item_id = uuid.uuid4()
        connection.execute(
            line_items.insert(),
            {
                "id": line_item_id,
                "external_reference": str(row["vacation_id"]),
                "source": "legacy_vacation_fk",
                "description": row["package_name"],
                "vacation_id": row["vacation_id"],
                "created_at": datetime.now(UTC),
            },
        )
        connection.execute(
            transactions.update()
            .where(transactions.c.id == row["transaction_id"])
            .values(line_item_id=line_item_id),
        )


def backfill_transactions_from_line_items() -> None:
    connection = op.get_bind()
    transactions = transactions_table()
    line_items = line_items_table()
    rows = connection.execute(
        sa.select(
            transactions.c.id.label("transaction_id"),
            line_items.c.external_reference.label("external_reference"),
            line_items.c.description.label("description"),
            line_items.c.vacation_id.label("vacation_id"),
        ).select_from(
            transactions.join(
                line_items,
                transactions.c.line_item_id == line_items.c.id,
            ),
        ),
    ).mappings()

    for row in rows:
        vacation_id = row["vacation_id"] or parse_uuid(row["external_reference"])
        if vacation_id is None:
            vacation_id = uuid.uuid4()

        ensure_vacation(
            vacation_id,
            row["description"] or row["external_reference"],
        )
        connection.execute(
            transactions.update()
            .where(transactions.c.id == row["transaction_id"])
            .values(line_item=vacation_id),
        )


def ensure_vacation(vacation_id: uuid.UUID, package_name: str) -> None:
    connection = op.get_bind()
    vacations = vacations_table()
    exists = connection.execute(
        sa.select(vacations.c.id).where(vacations.c.id == vacation_id),
    ).first()
    if exists is not None:
        return

    connection.execute(
        vacations.insert(),
        {
            "id": vacation_id,
            "package_name": package_name,
            "created_at": datetime.now(UTC),
        },
    )


def parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def line_items_table():
    return sa.table(
        "line_items",
        sa.column("id", sa.Uuid()),
        sa.column("external_reference", sa.String()),
        sa.column("source", sa.String()),
        sa.column("description", sa.String()),
        sa.column("vacation_id", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )


def transactions_table():
    return sa.table(
        "transactions",
        sa.column("id", sa.Uuid()),
        sa.column("line_item", sa.Uuid()),
        sa.column("line_item_id", sa.Uuid()),
    )


def vacations_table():
    return sa.table(
        "vacations",
        sa.column("id", sa.Uuid()),
        sa.column("package_name", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
