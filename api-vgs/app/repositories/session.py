from sqlalchemy.orm import Session

from app.repositories.flights import FlightRepository
from app.repositories.hotels import HotelRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.ledger import LedgerRepository
from app.repositories.line_items import LineItemRepository
from app.repositories.processor_attempts import ProcessorAttemptRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.vacations import VacationRepository


class Repositories:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.flights = FlightRepository(db)
        self.hotels = HotelRepository(db)
        self.idempotency = IdempotencyRepository(db)
        self.ledger = LedgerRepository(db)
        self.line_items = LineItemRepository(db)
        self.processor_attempts = ProcessorAttemptRepository(db)
        self.transactions = TransactionRepository(db)
        self.vacations = VacationRepository(db)

    def assert_shared_session(self) -> None:
        repositories = (
            self.flights,
            self.hotels,
            self.idempotency,
            self.ledger,
            self.line_items,
            self.processor_attempts,
            self.transactions,
            self.vacations,
        )
        if any(repository.db is not self.db for repository in repositories):
            raise RuntimeError("repositories must share one database session")
