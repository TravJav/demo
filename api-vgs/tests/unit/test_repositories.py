import pytest
from sqlalchemy.orm import Session

from app.database import engine
from app.repositories import Repositories
from app.services import (
    LedgerReportService,
    PaymentsService,
    ReconcileService,
    VacationService,
)


def test_repository_bundle_shares_one_database_session() -> None:
    with Session(engine) as db:
        repositories = Repositories(db)

        assert repositories.db is db
        assert repositories.flights.db is db
        assert repositories.hotels.db is db
        assert repositories.idempotency.db is db
        assert repositories.ledger.db is db
        assert repositories.processor_attempts.db is db
        assert repositories.transactions.db is db
        assert repositories.vacations.db is db


def test_services_share_repository_session_when_using_same_bundle() -> None:
    with Session(engine) as db:
        repositories = Repositories(db)
        vacation_service = VacationService(repositories)
        reconcile_service = ReconcileService(repositories)
        payments_service = PaymentsService(repositories)
        report_service = LedgerReportService(repositories)

        assert vacation_service.repositories is repositories
        assert reconcile_service.repositories is repositories
        assert payments_service.repositories is repositories
        assert report_service.repositories is repositories
        assert vacation_service.repositories.db is reconcile_service.repositories.db
        assert payments_service.repositories.db is report_service.repositories.db


def test_repository_bundle_rejects_mixed_sessions() -> None:
    with Session(engine) as first_db, Session(engine) as second_db:
        repositories = Repositories(first_db)
        repositories.ledger.db = second_db

        with pytest.raises(RuntimeError, match="share one database session"):
            repositories.assert_shared_session()
