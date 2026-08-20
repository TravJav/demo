import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_reconcile_service
from app.schemas import ReconcileTransactionRead, TransactionReconcileUpdate
from app.services import ReconcileService, TransactionNotFoundError

router = APIRouter(prefix="/reconcile", tags=["reconcile"])


@router.post(
    "/transactions/{transaction_id}",
    response_model=ReconcileTransactionRead,
    summary="Reconcile transaction",
    response_description="Updated transaction and optional appended ledger entry.",
)
def reconcile_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionReconcileUpdate,
    service: Annotated[ReconcileService, Depends(get_reconcile_service)],
) -> ReconcileTransactionRead:
    try:
        return service.reconcile_transaction(transaction_id, payload)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
