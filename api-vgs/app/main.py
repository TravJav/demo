from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import engine, init_db
from app.routes import knowledge_base, reconcile, system, vacations

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
    {
        "name": "knowledge-base",
        "description": "Processor capability profiles derived from integration specs.",
    },
    {
        "name": "reconcile",
        "description": "Record reconciliation and append-only ledger adjustments.",
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

app.include_router(system.router)
app.include_router(vacations.router)
app.include_router(knowledge_base.router)
app.include_router(reconcile.router)
