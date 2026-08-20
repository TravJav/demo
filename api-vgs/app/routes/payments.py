import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.dependencies import get_payments_service
from app.schemas import ChargeCreate, ChargeRead, RefundCreate, RefundRead
from app.services import (
    IdempotencyConflictError,
    PaymentFailedError,
    PaymentsService,
    PaymentTransactionNotFoundError,
    RefundAmountError,
    RefundNotAllowedError,
    UnsupportedCurrencyError,
)

router = APIRouter(tags=["payments"])

IdempotencyHeader = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=255),
]


@router.post(
    "/charges",
    response_model=ChargeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create charge",
    response_description="Charge transaction with processor attempts and ledger entry.",
)
def create_charge(
    payload: ChargeCreate,
    idempotency_key: IdempotencyHeader,
    service: Annotated[PaymentsService, Depends(get_payments_service)],
) -> JSONResponse:
    try:
        response = service.create_charge(payload, idempotency_key)
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency key was reused with a different request",
        ) from exc
    except UnsupportedCurrencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"currency {exc.currency} is not supported by available processors",
        ) from exc
    except PaymentFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="charge could not be persisted",
        ) from exc

    return JSONResponse(status_code=response.status_code, content=response.body)


@router.get(
    "/charges/{transaction_id}",
    response_model=ChargeRead,
    summary="Get charge",
    response_description="Charge transaction with its processor attempts and ledger entry.",
)
def get_charge(
    transaction_id: uuid.UUID,
    service: Annotated[PaymentsService, Depends(get_payments_service)],
) -> dict[str, object]:
    try:
        return service.get_charge(transaction_id)
    except PaymentTransactionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.post(
    "/refunds",
    response_model=RefundRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create refund",
    response_description="Refund ledger entry and processor attempt.",
)
def create_refund(
    payload: RefundCreate,
    idempotency_key: IdempotencyHeader,
    service: Annotated[PaymentsService, Depends(get_payments_service)],
) -> JSONResponse:
    try:
        response = service.refund(payload, idempotency_key)
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency key was reused with a different request",
        ) from exc
    except PaymentTransactionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except (RefundAmountError, RefundNotAllowedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="refund cannot be applied to this transaction",
        ) from exc
    except PaymentFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="refund could not be persisted",
        ) from exc

    return JSONResponse(status_code=response.status_code, content=response.body)
