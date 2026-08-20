from sqlalchemy.orm import Session

from app.repositories.flights import FlightRepository
from app.repositories.hotels import HotelRepository
from app.repositories.ledger import LedgerRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.vacations import VacationRepository


class Repositories:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.flights = FlightRepository(db)
        self.hotels = HotelRepository(db)
        self.ledger = LedgerRepository(db)
        self.transactions = TransactionRepository(db)
        self.vacations = VacationRepository(db)

    def assert_shared_session(self) -> None:
        repositories = (
            self.flights,
            self.hotels,
            self.ledger,
            self.transactions,
            self.vacations,
        )
        if any(repository.db is not self.db for repository in repositories):
            raise RuntimeError("repositories must share one database session")
