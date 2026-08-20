from enum import StrEnum


class LedgerEntryType(StrEnum):
    CHARGE = "charge"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUSED = "refused"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    UNKNOWN = "unknown"


class PaymentOperation(StrEnum):
    CHARGE = "charge"
    REFUND = "refund"


class ProcessorAttemptStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUSED = "refused"
