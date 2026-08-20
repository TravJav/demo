from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now
from app.models.enums import LedgerEntryType

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class Ledger(Base):
    __tablename__ = "ledger"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('charge', 'refund', 'adjustment')",
            name="ck_ledger_entry_type_known",
        ),
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_ledger_currency_iso_upper",
        ),
        CheckConstraint(
            "("
            "entry_type = 'charge' AND amount > 0"
            ") OR ("
            "entry_type = 'refund' AND amount < 0"
            ") OR ("
            "entry_type = 'adjustment' AND amount != 0"
            ")",
            name="ck_ledger_amount_direction",
        ),
        UniqueConstraint(
            "processor",
            "processor_reference",
            name="uq_ledger_processor_reference",
        ),
        Index("ix_ledger_created_at", "created_at"),
        Index("ix_ledger_currency_created_at", "currency", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    entry_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=LedgerEntryType.CHARGE.value,
    )
    processor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processor_reference: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    transaction: Mapped[Transaction] = relationship(
        "Transaction",
        back_populates="ledger_entries",
    )


@event.listens_for(Ledger, "before_update")
@event.listens_for(Ledger, "before_delete")
def prevent_ledger_mutation(*_args: object) -> None:
    raise ValueError("ledger entries are append-only")
