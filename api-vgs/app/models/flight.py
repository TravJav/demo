from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.vacation import Vacation


class Flight(Base):
    __tablename__ = "flights"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    flight_number: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_number: Mapped[str] = mapped_column(String(128), nullable=False)
    seat: Mapped[str] = mapped_column(String(32), nullable=False)
    vacation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vacations.id"),
        nullable=False,
        index=True,
    )

    vacation: Mapped[Vacation] = relationship("Vacation", back_populates="flights")
