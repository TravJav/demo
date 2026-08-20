from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now
from app.models.enums import TransactionStatus

if TYPE_CHECKING:
    from app.models.ledger import Ledger
    from app.models.line_item import LineItem
    from app.models.processor_attempt import ProcessorAttempt


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_transactions_currency_iso_upper",
        ),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refused', "
            "'partially_refunded', 'refunded', 'unknown')",
            name="ck_transactions_status_known",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    line_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("line_items.id"),
        nullable=False,
        index=True,
    )
    psp_ref: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
        unique=True,
        index=True,
    )
    processor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processor_reference: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TransactionStatus.SUCCEEDED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    line_item_record: Mapped[LineItem] = relationship(
        "LineItem",
        back_populates="transactions",
    )
    ledger_entries: Mapped[list[Ledger]] = relationship(
        "Ledger",
        back_populates="transaction",
        order_by="Ledger.created_at",
    )
    processor_attempts: Mapped[list[ProcessorAttempt]] = relationship(
        "ProcessorAttempt",
        back_populates="transaction",
        order_by="ProcessorAttempt.created_at",
    )

    @property
    def line_item(self) -> str:
        return self.line_item_record.external_reference
