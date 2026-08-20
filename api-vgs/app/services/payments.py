from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.models import (
    IdempotencyRecord,
    Ledger,
    LedgerEntryType,
    LineItem,
    PaymentOperation,
    ProcessorAttempt,
    ProcessorAttemptStatus,
    Transaction,
    TransactionStatus,
)
from app.repositories import Repositories
from app.schemas import (
    CardCreate,
    ChargeCreate,
    ChargeRead,
    LedgerRead,
    ProcessorAttemptRead,
    RefundCreate,
    RefundRead,
    TransactionRead,
)
from app.services.payment_routing import (
    PaymentRoutingService,
    ProcessorUnavailableError,
)
from app.services.processor_adapters import CardDetails, ProcessorResult


@dataclass(frozen=True)
class PaymentServiceResponse:
    status_code: int
    body: dict[str, object]


class IdempotencyConflictError(Exception):
    pass


class PaymentFailedError(Exception):
    pass


class PaymentTransactionNotFoundError(Exception):
    pass


class RefundAmountError(Exception):
    pass


class RefundNotAllowedError(Exception):
    pass


class UnsupportedCurrencyError(Exception):
    def __init__(self, currency: str) -> None:
        super().__init__(currency)
        self.currency = currency


class PaymentsService:
    def __init__(
        self,
        repositories: Repositories,
        routing: PaymentRoutingService | None = None,
    ) -> None:
        repositories.assert_shared_session()
        self.repositories = repositories
        self.routing = routing or PaymentRoutingService()

    def create_charge(
        self,
        payload: ChargeCreate,
        idempotency_key: str,
    ) -> PaymentServiceResponse:
        request_path = "/charges"
        request_hash = self._request_hash(payload.model_dump(mode="json"))
        existing = self._get_idempotency_record(idempotency_key)
        if existing is not None:
            return self._replay_idempotent_response(
                existing,
                request_path=request_path,
                request_hash=request_hash,
            )

        results = self.routing.charge(
            amount_minor=payload.amount_minor,
            currency=payload.currency,
            card=self._card_details(payload.card),
        )
        if not results:
            raise UnsupportedCurrencyError(payload.currency)

        amount = self._minor_to_decimal(payload.amount_minor)
        winning_result = self._winning_result(results)
        processor = winning_result.processor if winning_result else results[-1].processor

        try:
            with self.repositories.db.begin():
                line_item = self.repositories.line_items.add(
                    LineItem(
                        external_reference=payload.line_item,
                        source="payment_api",
                        description=payload.line_item,
                    ),
                )
                self.repositories.db.flush()

                transaction = self.repositories.transactions.add(
                    Transaction(
                        amount=amount,
                        currency=payload.currency,
                        line_item_record=line_item,
                        processor=processor,
                        processor_reference=(
                            winning_result.processor_reference if winning_result else None
                        ),
                        status=self._transaction_status(results),
                    ),
                )
                self.repositories.db.flush()

                attempts = [
                    self._add_attempt(
                        transaction_id=transaction.id,
                        result=result,
                        operation=PaymentOperation.CHARGE,
                    )
                    for result in results
                ]

                ledger = None
                if winning_result is not None:
                    ledger = self.repositories.ledger.add(
                        Ledger(
                            transaction_id=transaction.id,
                            amount=transaction.amount,
                            currency=transaction.currency,
                            entry_type=LedgerEntryType.CHARGE,
                            processor=winning_result.processor,
                            processor_reference=winning_result.processor_reference,
                        ),
                    )

                self.repositories.db.flush()
                body = self._charge_body(
                    transaction=transaction,
                    ledger=ledger,
                    attempts=attempts,
                    line_item=payload.line_item,
                    idempotency_key=idempotency_key,
                )
                self._store_idempotent_response(
                    idempotency_key=idempotency_key,
                    request_path=request_path,
                    request_hash=request_hash,
                    status_code=201,
                    response_body=body,
                    transaction_id=transaction.id,
                )
        except SQLAlchemyError as exc:
            raise PaymentFailedError from exc

        return PaymentServiceResponse(status_code=201, body=body)

    def get_charge(self, transaction_id: uuid.UUID) -> dict[str, object]:
        transaction = self.repositories.transactions.get(transaction_id)
        if transaction is None:
            raise PaymentTransactionNotFoundError

        return self._charge_body(
            transaction=transaction,
            ledger=self.repositories.ledger.charge_for_transaction(transaction.id),
            attempts=self.repositories.processor_attempts.list_for_transaction(
                transaction.id,
            ),
            line_item=transaction.line_item,
            idempotency_key="",
        )

    def refund(
        self,
        payload: RefundCreate,
        idempotency_key: str,
    ) -> PaymentServiceResponse:
        request_path = "/refunds"
        request_hash = self._request_hash(payload.model_dump(mode="json"))
        existing = self._get_idempotency_record(idempotency_key)
        if existing is not None:
            return self._replay_idempotent_response(
                existing,
                request_path=request_path,
                request_hash=request_hash,
            )

        try:
            with self.repositories.db.begin():
                transaction = self.repositories.transactions.get_for_update(
                    payload.transaction_id,
                )
                if transaction is None:
                    raise PaymentTransactionNotFoundError

                self._assert_refundable(transaction)
                remaining = transaction.amount - self.repositories.ledger.refunded_total(
                    transaction.id,
                )
                if remaining <= 0:
                    raise RefundAmountError

                refund_amount_minor = payload.amount_minor or self._decimal_to_minor(
                    remaining,
                )
                refund_amount = self._minor_to_decimal(refund_amount_minor)
                if refund_amount > remaining:
                    raise RefundAmountError

                result = self.routing.refund(
                    processor=transaction.processor or "",
                    amount_minor=refund_amount_minor,
                    currency=transaction.currency,
                    processor_reference=transaction.processor_reference or "",
                )
                attempt = self._add_attempt(
                    transaction_id=transaction.id,
                    result=result,
                    operation=PaymentOperation.REFUND,
                )

                if result.status != ProcessorAttemptStatus.SUCCEEDED:
                    raise RefundNotAllowedError

                ledger = self.repositories.ledger.add(
                    Ledger(
                        transaction_id=transaction.id,
                        amount=-refund_amount,
                        currency=transaction.currency,
                        entry_type=LedgerEntryType.REFUND,
                        processor=result.processor,
                        processor_reference=result.processor_reference,
                    ),
                )
                transaction.status = (
                    TransactionStatus.REFUNDED
                    if refund_amount == remaining
                    else TransactionStatus.PARTIALLY_REFUNDED
                )
                self.repositories.db.flush()

                body = self._refund_body(
                    transaction=transaction,
                    ledger=ledger,
                    attempts=[attempt],
                    idempotency_key=idempotency_key,
                )
                self._store_idempotent_response(
                    idempotency_key=idempotency_key,
                    request_path=request_path,
                    request_hash=request_hash,
                    status_code=201,
                    response_body=body,
                    transaction_id=transaction.id,
                )
        except ProcessorUnavailableError as exc:
            raise RefundNotAllowedError from exc
        except SQLAlchemyError as exc:
            raise PaymentFailedError from exc

        return PaymentServiceResponse(status_code=201, body=body)

    def _assert_refundable(self, transaction: Transaction) -> None:
        if transaction.status not in {
            TransactionStatus.SUCCEEDED,
            TransactionStatus.PARTIALLY_REFUNDED,
        }:
            raise RefundNotAllowedError
        if transaction.processor is None or transaction.processor_reference is None:
            raise RefundNotAllowedError

    def _get_idempotency_record(
        self,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        with self.repositories.db.begin():
            return self.repositories.idempotency.get(idempotency_key)

    def _add_attempt(
        self,
        *,
        transaction_id: uuid.UUID,
        result: ProcessorResult,
        operation: PaymentOperation,
    ) -> ProcessorAttempt:
        return self.repositories.processor_attempts.add(
            ProcessorAttempt(
                transaction_id=transaction_id,
                processor=result.processor,
                operation=operation,
                status=result.status,
                processor_reference=result.processor_reference,
                error_code=result.error_code,
                error_message=result.error_message,
            ),
        )

    def _winning_result(
        self,
        results: list[ProcessorResult],
    ) -> ProcessorResult | None:
        return next(
            (
                result
                for result in results
                if result.status == ProcessorAttemptStatus.SUCCEEDED
            ),
            None,
        )

    def _transaction_status(self, results: list[ProcessorResult]) -> TransactionStatus:
        if self._winning_result(results) is not None:
            return TransactionStatus.SUCCEEDED
        if any(result.hard_decline for result in results):
            return TransactionStatus.REFUSED
        if all(result.status == ProcessorAttemptStatus.REFUSED for result in results):
            return TransactionStatus.REFUSED
        return TransactionStatus.FAILED

    def _charge_body(
        self,
        *,
        transaction: Transaction,
        ledger: Ledger | None,
        attempts: list[ProcessorAttempt],
        line_item: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        response = ChargeRead(
            transaction=TransactionRead.model_validate(transaction),
            ledger=LedgerRead.model_validate(ledger) if ledger else None,
            attempts=[
                ProcessorAttemptRead.model_validate(attempt) for attempt in attempts
            ],
            line_item=line_item,
            idempotency_key=idempotency_key,
        )
        return response.model_dump(mode="json")

    def _refund_body(
        self,
        *,
        transaction: Transaction,
        ledger: Ledger,
        attempts: list[ProcessorAttempt],
        idempotency_key: str,
    ) -> dict[str, object]:
        response = RefundRead(
            transaction=TransactionRead.model_validate(transaction),
            ledger=LedgerRead.model_validate(ledger),
            attempts=[
                ProcessorAttemptRead.model_validate(attempt) for attempt in attempts
            ],
            idempotency_key=idempotency_key,
        )
        return response.model_dump(mode="json")

    def _store_idempotent_response(
        self,
        *,
        idempotency_key: str,
        request_path: str,
        request_hash: str,
        status_code: int,
        response_body: dict[str, object],
        transaction_id: uuid.UUID,
    ) -> None:
        self.repositories.idempotency.add(
            IdempotencyRecord(
                idempotency_key=idempotency_key,
                request_path=request_path,
                request_hash=request_hash,
                status_code=status_code,
                response_body=response_body,
                transaction_id=transaction_id,
            ),
        )

    def _replay_idempotent_response(
        self,
        existing: IdempotencyRecord,
        *,
        request_path: str,
        request_hash: str,
    ) -> PaymentServiceResponse:
        if (
            existing.request_path != request_path
            or existing.request_hash != request_hash
        ):
            raise IdempotencyConflictError
        return PaymentServiceResponse(
            status_code=existing.status_code,
            body=existing.response_body,
        )

    def _request_hash(self, body: dict[str, object]) -> str:
        normalized_body = json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(normalized_body.encode("utf-8")).hexdigest()

    def _card_details(self, card: CardCreate) -> CardDetails:
        return CardDetails(
            number=card.number,
            exp_month=card.exp_month,
            exp_year=card.exp_year,
            cvc=card.cvc,
        )

    def _minor_to_decimal(self, amount_minor: int) -> Decimal:
        return (Decimal(amount_minor) / Decimal(100)).quantize(Decimal("0.01"))

    def _decimal_to_minor(self, amount: Decimal) -> int:
        return int(amount * Decimal(100))
