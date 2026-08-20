from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["system"])


@router.get(
    "/",
    summary="Read service information",
    response_description="Current API status and environment.",
)
def read_root() -> dict[str, str]:
    settings = get_settings()
    return {
        "message": "api-vgs is running",
        "environment": settings.environment,
    }


@router.get(
    "/health",
    summary="Health check",
    response_description="API health status.",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}
