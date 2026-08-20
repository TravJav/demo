import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Ledger, LedgerEntryType


class LedgerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, ledger: Ledger) -> Ledger:
        self.db.add(ledger)
        return ledger

    def list_for_transaction(self, transaction_id: uuid.UUID) -> list[Ledger]:
        return list(
            self.db.scalars(
                select(Ledger)
                .where(Ledger.transaction_id == transaction_id)
                .order_by(Ledger.created_at),
            ),
        )

    def charge_for_transaction(self, transaction_id: uuid.UUID) -> Ledger | None:
        return self.db.scalar(
            select(Ledger)
            .where(
                Ledger.transaction_id == transaction_id,
                Ledger.entry_type == LedgerEntryType.CHARGE,
            )
            .order_by(Ledger.created_at)
            .limit(1),
        )

    def refunded_total(self, transaction_id: uuid.UUID) -> Decimal:
        value = self.db.scalar(
            select(func.sum(Ledger.amount)).where(
                Ledger.transaction_id == transaction_id,
                Ledger.entry_type == LedgerEntryType.REFUND,
            ),
        )
        return abs(Decimal(str(value or "0.00")))

    def totals_by_currency(
        self,
        start_at: datetime,
        end_at: datetime,
    ) -> list[tuple[str, str, Decimal]]:
        rows = self.db.execute(
            select(Ledger.currency, Ledger.entry_type, func.sum(Ledger.amount))
            .where(Ledger.created_at >= start_at, Ledger.created_at < end_at)
            .group_by(Ledger.currency, Ledger.entry_type),
        ).all()
        return [
            (currency, entry_type, Decimal(str(total or "0.00")))
            for currency, entry_type, total in rows
        ]
