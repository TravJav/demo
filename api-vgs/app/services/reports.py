from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from app.models import LedgerEntryType
from app.repositories import Repositories
from app.schemas import LedgerCurrencySummaryRead, LedgerDailySummaryRead


class LedgerReportService:
    def __init__(self, repositories: Repositories) -> None:
        repositories.assert_shared_session()
        self.repositories = repositories

    def daily_summary(self, report_date: date) -> LedgerDailySummaryRead:
        start_at = datetime.combine(report_date, time.min, tzinfo=UTC)
        end_at = datetime.combine(
            report_date + timedelta(days=1),
            time.min,
            tzinfo=UTC,
        )
        totals = self.repositories.ledger.totals_by_currency(start_at, end_at)

        by_currency: dict[str, dict[str, Decimal]] = {}
        for currency, entry_type, amount in totals:
            bucket = by_currency.setdefault(
                currency,
                {
                    LedgerEntryType.CHARGE.value: Decimal("0.00"),
                    LedgerEntryType.REFUND.value: Decimal("0.00"),
                    LedgerEntryType.ADJUSTMENT.value: Decimal("0.00"),
                },
            )
            bucket[entry_type] += amount

        currencies = [
            LedgerCurrencySummaryRead(
                currency=currency,
                charges_minor=self._decimal_to_minor(
                    buckets[LedgerEntryType.CHARGE.value],
                ),
                refunds_minor=abs(
                    self._decimal_to_minor(buckets[LedgerEntryType.REFUND.value]),
                ),
                net_minor=self._decimal_to_minor(sum(buckets.values())),
            )
            for currency, buckets in sorted(by_currency.items())
        ]

        return LedgerDailySummaryRead(date=report_date, currencies=currencies)

    def _decimal_to_minor(self, amount: Decimal) -> int:
        return int(amount * Decimal(100))
