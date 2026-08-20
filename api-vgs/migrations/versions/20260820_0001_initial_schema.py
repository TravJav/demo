"""initial schema

Revision ID: 202608200001
Revises:
Create Date: 2026-08-20 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202608200001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vacations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "flights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("flight_number", sa.String(length=64), nullable=False),
        sa.Column("reference_number", sa.String(length=128), nullable=False),
        sa.Column("seat", sa.String(length=32), nullable=False),
        sa.Column("vacation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["vacation_id"], ["vacations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_flights_vacation_id"), "flights", ["vacation_id"])
    op.create_table(
        "hotels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("booking_number", sa.String(length=128), nullable=False),
        sa.Column("reference_number", sa.String(length=128), nullable=False),
        sa.Column("vacation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["vacation_id"], ["vacations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_hotels_vacation_id"), "hotels", ["vacation_id"])
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("line_item", sa.Uuid(), nullable=False),
        sa.Column("psp_ref", sa.Uuid(), nullable=False),
        sa.Column("processor", sa.String(length=64), nullable=True),
        sa.Column("processor_reference", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_transactions_currency_iso_upper",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refused', "
            "'partially_refunded', 'refunded', 'unknown')",
            name="ck_transactions_status_known",
        ),
        sa.ForeignKeyConstraint(["line_item"], ["vacations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_line_item"), "transactions", ["line_item"])
    op.create_index(
        op.f("ix_transactions_processor_reference"),
        "transactions",
        ["processor_reference"],
        unique=True,
    )
    op.create_index(
        op.f("ix_transactions_psp_ref"),
        "transactions",
        ["psp_ref"],
        unique=True,
    )
    op.create_table(
        "ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("processor", sa.String(length=64), nullable=True),
        sa.Column("processor_reference", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('charge', 'refund', 'adjustment')",
            name="ck_ledger_entry_type_known",
        ),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_ledger_currency_iso_upper",
        ),
        sa.CheckConstraint(
            "("
            "entry_type = 'charge' AND amount > 0"
            ") OR ("
            "entry_type = 'refund' AND amount < 0"
            ") OR ("
            "entry_type = 'adjustment' AND amount != 0"
            ")",
            name="ck_ledger_amount_direction",
        ),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processor",
            "processor_reference",
            name="uq_ledger_processor_reference",
        ),
    )
    op.create_index(op.f("ix_ledger_created_at"), "ledger", ["created_at"])
    op.create_index(
        op.f("ix_ledger_currency_created_at"),
        "ledger",
        ["currency", "created_at"],
    )
    op.create_index(
        op.f("ix_ledger_processor_reference"),
        "ledger",
        ["processor_reference"],
    )
    op.create_index(
        op.f("ix_ledger_transaction_id"),
        "ledger",
        ["transaction_id"],
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_path", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_idempotency_records_idempotency_key"),
        "idempotency_records",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_idempotency_records_transaction_id"),
        "idempotency_records",
        ["transaction_id"],
    )
    op.create_table(
        "processor_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("processor", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("processor_reference", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "operation IN ('charge', 'refund')",
            name="ck_processor_attempts_operation_known",
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'refused')",
            name="ck_processor_attempts_status_known",
        ),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_processor_attempts_processor"),
        "processor_attempts",
        ["processor"],
    )
    op.create_index(
        op.f("ix_processor_attempts_transaction_id"),
        "processor_attempts",
        ["transaction_id"],
    )
    install_ledger_append_only_trigger()


def downgrade() -> None:
    uninstall_ledger_append_only_trigger()
    op.drop_index(op.f("ix_processor_attempts_transaction_id"), "processor_attempts")
    op.drop_index(op.f("ix_processor_attempts_processor"), "processor_attempts")
    op.drop_table("processor_attempts")
    op.drop_index(op.f("ix_idempotency_records_transaction_id"), "idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_idempotency_key"), "idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index(op.f("ix_ledger_transaction_id"), "ledger")
    op.drop_index(op.f("ix_ledger_processor_reference"), "ledger")
    op.drop_index(op.f("ix_ledger_currency_created_at"), "ledger")
    op.drop_index(op.f("ix_ledger_created_at"), "ledger")
    op.drop_table("ledger")
    op.drop_index(op.f("ix_transactions_psp_ref"), "transactions")
    op.drop_index(op.f("ix_transactions_processor_reference"), "transactions")
    op.drop_index(op.f("ix_transactions_line_item"), "transactions")
    op.drop_table("transactions")
    op.drop_index(op.f("ix_hotels_vacation_id"), "hotels")
    op.drop_table("hotels")
    op.drop_index(op.f("ix_flights_vacation_id"), "flights")
    op.drop_table("flights")
    op.drop_table("vacations")


def install_ledger_append_only_trigger() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_ledger_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'ledger entries are append-only';
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute("DROP TRIGGER IF EXISTS prevent_ledger_update ON ledger")
    op.execute(
        """
        CREATE TRIGGER prevent_ledger_update
        BEFORE UPDATE OR DELETE ON ledger
        FOR EACH ROW
        EXECUTE FUNCTION prevent_ledger_mutation()
        """,
    )


def uninstall_ledger_append_only_trigger() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("DROP TRIGGER IF EXISTS prevent_ledger_update ON ledger")
    op.execute("DROP FUNCTION IF EXISTS prevent_ledger_mutation()")
