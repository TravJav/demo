import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Transaction


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, transaction: Transaction) -> Transaction:
        self.db.add(transaction)
        return transaction

    def get(self, transaction_id: uuid.UUID) -> Transaction | None:
        return self.db.get(Transaction, transaction_id)

    def get_for_update(self, transaction_id: uuid.UUID) -> Transaction | None:
        return self.db.scalar(
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .with_for_update(),
        )
