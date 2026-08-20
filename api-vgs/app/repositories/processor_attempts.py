import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProcessorAttempt


class ProcessorAttemptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, attempt: ProcessorAttempt) -> ProcessorAttempt:
        self.db.add(attempt)
        return attempt

    def list_for_transaction(self, transaction_id: uuid.UUID) -> list[ProcessorAttempt]:
        return list(
            self.db.scalars(
                select(ProcessorAttempt)
                .where(ProcessorAttempt.transaction_id == transaction_id)
                .order_by(ProcessorAttempt.created_at),
            ),
        )
