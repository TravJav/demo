import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Vacation


class VacationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, vacation: Vacation) -> Vacation:
        self.db.add(vacation)
        return vacation

    def get_with_details(self, vacation_id: uuid.UUID) -> Vacation | None:
        return self.db.scalar(
            select(Vacation)
            .options(selectinload(Vacation.flights), selectinload(Vacation.hotels))
            .where(Vacation.id == vacation_id)
        )
