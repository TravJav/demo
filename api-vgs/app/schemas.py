import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    LedgerEntryType,
    PaymentOperation,
    ProcessorAttemptStatus,
    TransactionStatus,
)


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
    line_item: str
    line_item_id: uuid.UUID
    psp_ref: uuid.UUID
    processor: str | None = None
    processor_reference: str | None = None
    status: TransactionStatus
    created_at: datetime
    reconciled_at: datetime | None = None


class LedgerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    amount: Decimal
    currency: str
    entry_type: LedgerEntryType
    processor: str | None = None
    processor_reference: str | None = None
    created_at: datetime


class VacationCheckoutRead(BaseModel):
    vacation: VacationRead
    transaction: TransactionRead
    ledger: LedgerRead


class CardCreate(BaseModel):
    number: str = Field(min_length=12, max_length=23)
    exp_month: int = Field(ge=1, le=12)
    exp_year: int = Field(ge=2000, le=2100)
    cvc: str = Field(min_length=3, max_length=4)


class ChargeCreate(BaseModel):
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    line_item: str = Field(min_length=1, max_length=255)
    card: CardCreate

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class RefundCreate(BaseModel):
    transaction_id: uuid.UUID
    amount_minor: int | None = Field(default=None, gt=0)


class ProcessorAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    processor: str
    operation: PaymentOperation
    status: ProcessorAttemptStatus
    processor_reference: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime


class ChargeRead(BaseModel):
    transaction: TransactionRead
    ledger: LedgerRead | None = None
    attempts: list[ProcessorAttemptRead]
    line_item: str
    idempotency_key: str


class RefundRead(BaseModel):
    transaction: TransactionRead
    ledger: LedgerRead
    attempts: list[ProcessorAttemptRead]
    idempotency_key: str


class LedgerCurrencySummaryRead(BaseModel):
    currency: str
    charges_minor: int
    refunds_minor: int
    net_minor: int


class LedgerDailySummaryRead(BaseModel):
    date: date
    currencies: list[LedgerCurrencySummaryRead]


class TransactionReconcileUpdate(BaseModel):
    status: TransactionStatus
    processor: str | None = Field(default=None, min_length=1, max_length=64)
    processor_reference: str | None = Field(default=None, min_length=1, max_length=128)
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    ledger_entry_type: LedgerEntryType | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()

    @model_validator(mode="after")
    def ledger_movements_need_references(self) -> "TransactionReconcileUpdate":
        if self.ledger_entry_type is not None and (
            self.processor is None or self.processor_reference is None
        ):
            raise ValueError(
                "ledger movements require processor and processor_reference",
            )
        return self


class ReconcileTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction: TransactionRead
    ledger: LedgerRead | None
    updated: bool


class ProcessorOperationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    request_format: str
    success_statuses: tuple[str, ...]
    failure_statuses: tuple[str, ...]


class ProcessorProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    display_name: str
    protocol: str
    sandbox_url: str
    local_mock_url: str
    auth_model: str
    supported_currencies: tuple[str, ...]
    amount_unit: str
    token_prefix: str
    idempotency_supported: bool
    refund_supported: bool
    status_lookup_supported: bool
    pricing: str
    retry_notes: str
    soft_decline_codes: tuple[str, ...]
    hard_decline_codes: tuple[str, ...]
    system_error_codes: tuple[str, ...]
    operations: tuple[ProcessorOperationRead, ...]
    source_documents: tuple[str, ...]
