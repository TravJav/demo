from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now
from app.models.enums import PaymentOperation, ProcessorAttemptStatus

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class ProcessorAttempt(Base):
    __tablename__ = "processor_attempts"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('charge', 'refund')",
            name="ck_processor_attempts_operation_known",
        ),
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'refused')",
            name="ck_processor_attempts_status_known",
        ),
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
    processor: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PaymentOperation.CHARGE.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProcessorAttemptStatus.SUCCEEDED.value,
    )
    processor_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    transaction: Mapped[Transaction] = relationship(
        "Transaction",
        back_populates="processor_attempts",
    )
