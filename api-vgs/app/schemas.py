import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FlightCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    flight_number: str = Field(min_length=1, max_length=64)
    reference_number: str = Field(min_length=1, max_length=128)
    seat: str = Field(min_length=1, max_length=32)


class HotelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    booking_number: str = Field(min_length=1, max_length=128)
    reference_number: str = Field(min_length=1, max_length=128)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def currency_must_be_usd(cls, value: str) -> str:
        currency = value.upper()
        if currency != "USD":
            raise ValueError("currency must be standardized to USD")
        return currency


class VacationCheckoutCreate(BaseModel):
    package_name: str = Field(min_length=1, max_length=255)
    payment: PaymentCreate
    flights: list[FlightCreate] = Field(default_factory=list)
    hotels: list[HotelCreate] = Field(default_factory=list)


class FlightRead(FlightCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vacation_id: uuid.UUID


class HotelRead(HotelCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vacation_id: uuid.UUID


class VacationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    package_name: str
    created_at: datetime
    flights: list[FlightRead]
    hotels: list[HotelRead]


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    currency: str
    line_item: uuid.UUID
    psp_ref: uuid.UUID
    status: str
    created_at: datetime


class LedgerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    amount: Decimal
    currency: str
    entry_type: str
    created_at: datetime


class VacationCheckoutRead(BaseModel):
    vacation: VacationRead
    transaction: TransactionRead
    ledger: LedgerRead
