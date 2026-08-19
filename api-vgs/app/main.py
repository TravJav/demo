import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import engine, get_db, init_db
from app.models import Flight, Hotel, Ledger, Transaction, Vacation
from app.schemas import (
    LedgerRead,
    TransactionRead,
    VacationCheckoutCreate,
    VacationCheckoutRead,
    VacationRead,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    _app.state.engine = engine
    init_db()
    yield

tags_metadata = [
    {
        "name": "system",
        "description": "Service status and basic application information.",
    },
    {
        "name": "vacations",
        "description": "Atomic vacation package checkout operations.",
    },
]

app = FastAPI(
    title=settings.app_name,
    summary="VGS demo backend API.",
    description=(
        "Basic FastAPI service for the VGS demo. Use the health endpoint "
        "to verify the API is running."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


@app.get(
    "/",
    tags=["system"],
    summary="Read service information",
    response_description="Current API status and environment.",
)
def read_root() -> dict[str, str]:
    return {
        "message": "api-vgs is running",
        "environment": settings.environment,
    }


@app.get(
    "/health",
    tags=["system"],
    summary="Health check",
    response_description="API health status.",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/vacations",
    tags=["vacations"],
    status_code=status.HTTP_201_CREATED,
    response_model=VacationCheckoutRead,
    summary="Create vacation checkout",
    response_description="Vacation package, payment transaction, and ledger entry.",
)
def create_vacation_checkout(
    payload: VacationCheckoutCreate,
    db: Annotated[Session, Depends(get_db)],
) -> VacationCheckoutRead:
    try:
        with db.begin():
            vacation = Vacation(package_name=payload.package_name)
            db.add(vacation)
            db.flush()

            vacation.flights = [
                Flight(vacation_id=vacation.id, **flight.model_dump())
                for flight in payload.flights
            ]
            vacation.hotels = [
                Hotel(vacation_id=vacation.id, **hotel.model_dump())
                for hotel in payload.hotels
            ]

            transaction = Transaction(
                amount=payload.payment.amount,
                currency=payload.payment.currency,
                line_item=vacation.id,
            )
            db.add(transaction)
            db.flush()

            ledger = Ledger(
                transaction_id=transaction.id,
                amount=transaction.amount,
                currency=transaction.currency,
                entry_type="charge",
            )
            db.add(ledger)

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vacation checkout failed and was rolled back.",
        ) from exc

    return VacationCheckoutRead(
        vacation=VacationRead.model_validate(vacation),
        transaction=TransactionRead.model_validate(transaction),
        ledger=LedgerRead.model_validate(ledger),
    )


@app.get(
    "/vacations/{vacation_id}",
    tags=["vacations"],
    response_model=VacationRead,
    summary="Read vacation package",
    response_description="Vacation package with flights and hotels.",
)
def read_vacation(
    vacation_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Vacation:
    vacation = db.scalar(
        select(Vacation)
        .options(selectinload(Vacation.flights), selectinload(Vacation.hotels))
        .where(Vacation.id == vacation_id)
    )

    if vacation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return vacation
