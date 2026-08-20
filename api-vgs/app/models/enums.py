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
    REFUNDED = "refunded"
    UNKNOWN = "unknown"
