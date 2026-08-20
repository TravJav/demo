import uuid
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError

from app.models import Flight, Hotel, Ledger, Transaction, Vacation
from app.repositories import Repositories
from app.schemas import VacationCheckoutCreate


class VacationCheckoutFailedError(Exception):
    pass


class VacationNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class VacationCheckoutResult:
    vacation: Vacation
    transaction: Transaction
    ledger: Ledger


class VacationService:
    def __init__(self, repositories: Repositories) -> None:
        repositories.assert_shared_session()
        self.repositories = repositories

    def create_checkout(
        self,
        payload: VacationCheckoutCreate,
    ) -> VacationCheckoutResult:
        try:
            with self.repositories.db.begin():
                vacation = self.repositories.vacations.add(
                    Vacation(package_name=payload.package_name),
                )
                self.repositories.db.flush()

                vacation.flights = self.repositories.flights.add_all(
                    [
                        Flight(vacation_id=vacation.id, **flight.model_dump())
                        for flight in payload.flights
                    ],
                )
                vacation.hotels = self.repositories.hotels.add_all(
                    [
                        Hotel(vacation_id=vacation.id, **hotel.model_dump())
                        for hotel in payload.hotels
                    ],
                )

                transaction = self.repositories.transactions.add(
                    Transaction(
                        amount=payload.payment.amount,
                        currency=payload.payment.currency,
                        line_item=vacation.id,
                    ),
                )
                self.repositories.db.flush()

                ledger = self.repositories.ledger.add(
                    Ledger(
                        transaction_id=transaction.id,
                        amount=transaction.amount,
                        currency=transaction.currency,
                        entry_type="charge",
                    ),
                )

        except SQLAlchemyError as exc:
            raise VacationCheckoutFailedError from exc

        return VacationCheckoutResult(
            vacation=vacation,
            transaction=transaction,
            ledger=ledger,
        )

    def get_vacation(self, vacation_id: uuid.UUID) -> Vacation:
        vacation = self.repositories.vacations.get_with_details(vacation_id)
        if vacation is None:
            raise VacationNotFoundError
        return vacation
