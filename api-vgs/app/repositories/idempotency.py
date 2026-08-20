from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IdempotencyRecord


class IdempotencyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, record: IdempotencyRecord) -> IdempotencyRecord:
        self.db.add(record)
        return record

    def get(self, idempotency_key: str) -> IdempotencyRecord | None:
        return self.db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.idempotency_key == idempotency_key,
            ),
        )
