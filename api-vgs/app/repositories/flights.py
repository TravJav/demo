from sqlalchemy.orm import Session

from app.models import Flight


class FlightRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_all(self, flights: list[Flight]) -> list[Flight]:
        self.db.add_all(flights)
        return flights
