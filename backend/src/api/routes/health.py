"""Health check route."""

from datetime import datetime
from typing import cast
from zoneinfo import ZoneInfo

from pycore.api import APIRouter
from pycore.api.responses import APIResponse, success_response

from ...settings import get_settings

router = APIRouter(prefix="/api", tags=["health"])


def build_health_payload() -> dict[str, str]:
    """Build the contract-aligned health payload."""
    settings = get_settings()
    timestamp = datetime.now(ZoneInfo(settings.timezone)).isoformat(timespec="seconds")
    return {
        "status": "ok",
        "service": settings.app_name,
        "timestamp": timestamp,
    }


@router.get("/health", response_model=APIResponse[dict[str, str]])
async def health_check() -> APIResponse[dict[str, str]]:
    """Return service health using the PyCore unified response shape."""
    return cast(
        APIResponse[dict[str, str]],
        success_response(data=build_health_payload()),
    )
