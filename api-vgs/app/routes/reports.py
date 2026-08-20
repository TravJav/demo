from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_ledger_report_service
from app.schemas import LedgerDailySummaryRead
from app.services import LedgerReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/ledger/daily",
    response_model=LedgerDailySummaryRead,
    summary="Get daily ledger summary",
    response_description="Ledger totals grouped by currency for a UTC calendar day.",
)
def daily_ledger_summary(
    service: Annotated[
        LedgerReportService,
        Depends(get_ledger_report_service),
    ],
    report_date: Annotated[date | None, Query(alias="date")] = None,
) -> LedgerDailySummaryRead:
    target_date = report_date or datetime.now(UTC).date()
    return service.daily_summary(target_date)
