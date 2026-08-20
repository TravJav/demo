import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.models import Ledger, LedgerEntryType, Transaction, utc_now
from app.repositories import Repositories
from app.schemas import TransactionReconcileUpdate


class TransactionNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class ReconcileResult:
    transaction: Transaction
    ledger: Ledger | None
    updated: bool


class ReconcileService:
    def __init__(self, repositories: Repositories) -> None:
        repositories.assert_shared_session()
        self.repositories = repositories

    def reconcile_transaction(
        self,
        transaction_id: uuid.UUID,
        payload: TransactionReconcileUpdate,
    ) -> ReconcileResult:
        ledger: Ledger | None = None

        with self.repositories.db.begin():
            transaction = self.repositories.transactions.get_for_update(transaction_id)
            if transaction is None:
                raise TransactionNotFoundError

            updated = self._update_transaction(transaction, payload)

            if payload.ledger_entry_type is not None:
                amount = payload.amount if payload.amount is not None else transaction.amount
                currency = payload.currency if payload.currency is not None else transaction.currency
                ledger = self.repositories.ledger.add(
                    Ledger(
                        transaction_id=transaction.id,
                        amount=self._ledger_amount(payload.ledger_entry_type, amount),
                        currency=currency,
                        entry_type=payload.ledger_entry_type,
                        processor=payload.processor,
                        processor_reference=payload.processor_reference,
                    ),
                )
                updated = True

            self.repositories.db.flush()

        return ReconcileResult(transaction=transaction, ledger=ledger, updated=updated)

    def _update_transaction(
        self,
        transaction: Transaction,
        payload: TransactionReconcileUpdate,
    ) -> bool:
        for field in ("status", "processor"):
            value = getattr(payload, field)
            if value is not None and getattr(transaction, field) != value:
                setattr(transaction, field, value)

        if (
            payload.processor_reference is not None
            and (
                payload.ledger_entry_type is None
                or payload.ledger_entry_type == LedgerEntryType.CHARGE
            )
            and transaction.processor_reference != payload.processor_reference
        ):
            transaction.processor_reference = payload.processor_reference

        transaction.reconciled_at = utc_now()
        return True

    def _ledger_amount(self, entry_type: str, amount: Decimal) -> Decimal:
        if entry_type == LedgerEntryType.REFUND and amount > 0:
            return -amount
        return amount
