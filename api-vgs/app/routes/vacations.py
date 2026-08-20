import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_vacation_service
from app.schemas import (
    LedgerRead,
    TransactionRead,
    VacationCheckoutCreate,
    VacationCheckoutRead,
    VacationRead,
)
from app.services import (
    VacationCheckoutFailedError,
    VacationNotFoundError,
    VacationService,
)

router = APIRouter(prefix="/vacations", tags=["vacations"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=VacationCheckoutRead,
    summary="Create vacation checkout",
    response_description="Vacation package, payment transaction, and ledger entry.",
)
def create_vacation_checkout(
    payload: VacationCheckoutCreate,
    service: Annotated[VacationService, Depends(get_vacation_service)],
) -> VacationCheckoutRead:
    try:
        result = service.create_checkout(payload)
    except VacationCheckoutFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vacation checkout failed and was rolled back.",
        ) from exc

    return VacationCheckoutRead(
        vacation=VacationRead.model_validate(result.vacation),
        transaction=TransactionRead.model_validate(result.transaction),
        ledger=LedgerRead.model_validate(result.ledger),
    )


@router.get(
    "/{vacation_id}",
    response_model=VacationRead,
    summary="Read vacation package",
    response_description="Vacation package with flights and hotels.",
)
def read_vacation(
    vacation_id: uuid.UUID,
    service: Annotated[VacationService, Depends(get_vacation_service)],
) -> VacationRead:
    try:
        return service.get_vacation(vacation_id)
    except VacationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
