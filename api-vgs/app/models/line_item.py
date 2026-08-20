from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.vacation import Vacation


class LineItem(Base):
    __tablename__ = "line_items"
    __table_args__ = (
        Index(
            "ix_line_items_source_external_reference",
            "source",
            "external_reference",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_reference: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vacation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vacations.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    vacation: Mapped[Vacation | None] = relationship(
        "Vacation",
        back_populates="line_items",
    )
    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction",
        back_populates="line_item_record",
    )
