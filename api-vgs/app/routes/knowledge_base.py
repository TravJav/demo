from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_knowledge_base_service
from app.schemas import ProcessorProfileRead
from app.services import KnowledgeBaseService, ProcessorNotFoundError, ProcessorProfile

router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


@router.get(
    "/processors",
    response_model=list[ProcessorProfileRead],
    summary="List processor knowledge profiles",
    response_description="Known processor capabilities and integration constraints.",
)
def list_processors(
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)],
    currency: Annotated[
        str | None,
        Query(min_length=3, max_length=3),
    ] = None,
) -> list[ProcessorProfile]:
    return service.list_processors(currency=currency)


@router.get(
    "/processors/{processor_name}",
    response_model=ProcessorProfileRead,
    summary="Read processor knowledge profile",
    response_description="Processor capabilities and integration constraints.",
)
def read_processor(
    processor_name: str,
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)],
) -> ProcessorProfile:
    try:
        return service.get_processor(processor_name)
    except ProcessorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
