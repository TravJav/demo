import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


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

    flights: Mapped[list["Flight"]] = relationship(
        back_populates="vacation",
        cascade="all, delete-orphan",
    )
    hotels: Mapped[list["Hotel"]] = relationship(
        back_populates="vacation",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="vacation")


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

    vacation: Mapped[Vacation] = relationship(back_populates="flights")


class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    booking_number: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_number: Mapped[str] = mapped_column(String(128), nullable=False)
    vacation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vacations.id"),
        nullable=False,
        index=True,
    )

    vacation: Mapped[Vacation] = relationship(back_populates="hotels")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    line_item: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vacations.id"),
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
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="succeeded")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    vacation: Mapped[Vacation] = relationship(back_populates="transactions")
    ledger_entries: Mapped[list["Ledger"]] = relationship(back_populates="transaction")


class Ledger(Base):
    __tablename__ = "ledger"

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
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False, default="charge")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    transaction: Mapped[Transaction] = relationship(back_populates="ledger_entries")


@event.listens_for(Ledger, "before_update")
@event.listens_for(Ledger, "before_delete")
def prevent_ledger_mutation(*_args: object) -> None:
    raise ValueError("ledger entries are append-only")
