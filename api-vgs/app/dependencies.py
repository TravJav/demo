from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import Repositories
from app.services import KnowledgeBaseService, ReconcileService, VacationService


def get_repositories(
    db: Annotated[Session, Depends(get_db)],
) -> Repositories:
    return Repositories(db)


def get_vacation_service(
    repositories: Annotated[Repositories, Depends(get_repositories)],
) -> VacationService:
    return VacationService(repositories)


def get_reconcile_service(
    repositories: Annotated[Repositories, Depends(get_repositories)],
) -> ReconcileService:
    return ReconcileService(repositories)


def get_knowledge_base_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()
