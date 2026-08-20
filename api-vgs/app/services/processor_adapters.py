from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models import ProcessorAttemptStatus


@dataclass(frozen=True)
class CardDetails:
    number: str
    exp_month: int
    exp_year: int
    cvc: str

    @property
    def normalized_number(self) -> str:
        return "".join(character for character in self.number if character.isdigit())


@dataclass(frozen=True)
class ProcessorResult:
    processor: str
    status: ProcessorAttemptStatus
    processor_reference: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    hard_decline: bool = False


class ProcessorAdapter:
    name: str
    protocol: str
    supported_currencies: tuple[str, ...]

    def supports_currency(self, currency: str) -> bool:
        return currency.upper() in self.supported_currencies

    def charge(
        self,
        *,
        amount_minor: int,
        currency: str,
        card: CardDetails,
    ) -> ProcessorResult:
        raise NotImplementedError

    def refund(
        self,
        *,
        amount_minor: int,
        currency: str,
        processor_reference: str,
    ) -> ProcessorResult:
        raise NotImplementedError


class StripelyAdapter(ProcessorAdapter):
    name = "stripely"
    protocol = "REST"
    supported_currencies = ("USD", "GBP")

    def charge(
        self,
        *,
        amount_minor: int,
        currency: str,
        card: CardDetails,
    ) -> ProcessorResult:
        if not self.supports_currency(currency):
            return self._failed("unsupported_currency", "currency is not supported")

        behavior = self._behavior(card.normalized_number)
        if behavior is not None:
            return behavior

        return ProcessorResult(
            processor=self.name,
            status=ProcessorAttemptStatus.SUCCEEDED,
            processor_reference=f"ch_st_{uuid.uuid4().hex[:16]}",
        )

    def refund(
        self,
        *,
        amount_minor: int,
        currency: str,
        processor_reference: str,
    ) -> ProcessorResult:
        if not self.supports_currency(currency):
            return self._failed("unsupported_currency", "currency is not supported")
        if not processor_reference:
            return self._failed("missing_reference", "processor reference is required")

        return ProcessorResult(
            processor=self.name,
            status=ProcessorAttemptStatus.SUCCEEDED,
            processor_reference=f"re_st_{uuid.uuid4().hex[:16]}",
        )

    def _behavior(self, card_number: str) -> ProcessorResult | None:
        if card_number == "4000000000009995":
            return ProcessorResult(
                processor=self.name,
                status=ProcessorAttemptStatus.REFUSED,
                error_code="insufficient_funds",
                error_message="soft decline",
                retryable=True,
            )
        if card_number == "4000000000009979":
            return ProcessorResult(
                processor=self.name,
                status=ProcessorAttemptStatus.REFUSED,
                error_code="stolen_card",
                error_message="hard decline",
                hard_decline=True,
            )
        if card_number in {"4000000000000119", "4000000000005900"}:
            return self._failed(
                "processor_unavailable",
                "processor did not complete the authorization",
                retryable=True,
            )
        return None

    def _failed(
        self,
        error_code: str,
        error_message: str,
        *,
        retryable: bool = False,
    ) -> ProcessorResult:
        return ProcessorResult(
            processor=self.name,
            status=ProcessorAttemptStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
        )


class AdyentaAdapter(ProcessorAdapter):
    name = "adyenta"
    protocol = "SOAP"
    supported_currencies = ("USD", "EUR")

    def charge(
        self,
        *,
        amount_minor: int,
        currency: str,
        card: CardDetails,
    ) -> ProcessorResult:
        if not self.supports_currency(currency):
            return self._failed("05", "currency is not supported")

        behavior = self._behavior(card.normalized_number)
        if behavior is not None:
            return behavior

        return ProcessorResult(
            processor=self.name,
            status=ProcessorAttemptStatus.SUCCEEDED,
            processor_reference=f"ady_{uuid.uuid4().int % 10**16:016d}",
        )

    def refund(
        self,
        *,
        amount_minor: int,
        currency: str,
        processor_reference: str,
    ) -> ProcessorResult:
        if not self.supports_currency(currency):
            return self._failed("05", "currency is not supported")
        if not processor_reference:
            return self._failed("12", "processor reference is required")

        return ProcessorResult(
            processor=self.name,
            status=ProcessorAttemptStatus.SUCCEEDED,
            processor_reference=f"ady_rf_{uuid.uuid4().int % 10**16:016d}",
        )

    def _behavior(self, card_number: str) -> ProcessorResult | None:
        if card_number == "4000000000009995":
            return ProcessorResult(
                processor=self.name,
                status=ProcessorAttemptStatus.REFUSED,
                error_code="51",
                error_message="soft decline",
                retryable=True,
            )
        if card_number == "4000000000009979":
            return ProcessorResult(
                processor=self.name,
                status=ProcessorAttemptStatus.REFUSED,
                error_code="43",
                error_message="hard decline",
                hard_decline=True,
            )
        if card_number in {"4000000000000119", "4000000000005900"}:
            return self._failed(
                "91",
                "issuer or processor unavailable",
                retryable=True,
            )
        return None

    def _failed(
        self,
        error_code: str,
        error_message: str,
        *,
        retryable: bool = False,
    ) -> ProcessorResult:
        return ProcessorResult(
            processor=self.name,
            status=ProcessorAttemptStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
        )
