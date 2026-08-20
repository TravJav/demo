from sqlalchemy.orm import Session

from app.models import Hotel


class HotelRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_all(self, hotels: list[Hotel]) -> list[Hotel]:
        self.db.add_all(hotels)
        return hotels
