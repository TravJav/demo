from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.flight import Flight
    from app.models.hotel import Hotel
    from app.models.line_item import LineItem


class Vacation(Base):
    __tablename__ = "vacations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    flights: Mapped[list[Flight]] = relationship(
        "Flight",
        back_populates="vacation",
        cascade="all, delete-orphan",
    )
    hotels: Mapped[list[Hotel]] = relationship(
        "Hotel",
        back_populates="vacation",
        cascade="all, delete-orphan",
    )
    line_items: Mapped[list[LineItem]] = relationship(
        "LineItem",
        back_populates="vacation",
    )
