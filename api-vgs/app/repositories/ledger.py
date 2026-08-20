from sqlalchemy.orm import Session

from app.models import Ledger


class LedgerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, ledger: Ledger) -> Ledger:
        self.db.add(ledger)
        return ledger
