from __future__ import annotations

from app.models import ProcessorAttemptStatus
from app.services.processor_adapters import (
    AdyentaAdapter,
    CardDetails,
    ProcessorAdapter,
    ProcessorResult,
    StripelyAdapter,
)


class PaymentRoutingService:
    def __init__(
        self,
        adapters: tuple[ProcessorAdapter, ...] | None = None,
    ) -> None:
        self.adapters = adapters or (StripelyAdapter(), AdyentaAdapter())

    def charge(
        self,
        *,
        amount_minor: int,
        currency: str,
        card: CardDetails,
    ) -> list[ProcessorResult]:
        results: list[ProcessorResult] = []
        for adapter in self._charge_candidates(currency):
            result = adapter.charge(
                amount_minor=amount_minor,
                currency=currency,
                card=card,
            )
            results.append(result)
            if result.status == ProcessorAttemptStatus.SUCCEEDED:
                break
            if result.hard_decline or not result.retryable:
                break
        return results

    def refund(
        self,
        *,
        processor: str,
        amount_minor: int,
        currency: str,
        processor_reference: str,
    ) -> ProcessorResult:
        adapter = self.get_adapter(processor)
        return adapter.refund(
            amount_minor=amount_minor,
            currency=currency,
            processor_reference=processor_reference,
        )

    def get_adapter(self, processor: str) -> ProcessorAdapter:
        for adapter in self.adapters:
            if adapter.name == processor:
                return adapter
        raise ProcessorUnavailableError(processor)

    def _charge_candidates(self, currency: str) -> tuple[ProcessorAdapter, ...]:
        normalized_currency = currency.upper()
        return tuple(
            adapter
            for adapter in self.adapters
            if adapter.supports_currency(normalized_currency)
        )


class ProcessorUnavailableError(Exception):
    def __init__(self, processor: str) -> None:
        super().__init__(processor)
        self.processor = processor
