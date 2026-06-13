"""Layout preference API routes."""

from typing import cast

from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter
from pycore.api.responses import APIResponse, success_response

from ...api.deps import get_session
from ...models.layout import LayoutPreferencesRead, LayoutPreferencesUpdate
from ...services.layout_service import LayoutService

router = APIRouter(prefix="/api/layout", tags=["layout"])
DB_SESSION_DEPENDENCY = Depends(get_session)


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": message, "data": None},
    )


@router.get("/preferences", response_model=APIResponse[LayoutPreferencesRead])
async def get_layout_preferences(
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[LayoutPreferencesRead]:
    """Return persisted layout preferences."""
    data = await LayoutService(db).get_preferences()
    return cast(APIResponse[LayoutPreferencesRead], success_response(data=data.model_dump()))


@router.patch("/preferences", response_model=APIResponse[LayoutPreferencesRead])
async def patch_layout_preferences(
    payload: LayoutPreferencesUpdate,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[LayoutPreferencesRead] | JSONResponse:
    """Update persisted layout preferences."""
    try:
        data = await LayoutService(db).update_preferences(
            sidebar_width=payload.sidebar_width,
            trace_panel_width=payload.trace_panel_width,
        )
    except ValueError as exc:
        return _error(str(exc), 422)
    return cast(APIResponse[LayoutPreferencesRead], success_response(data=data.model_dump()))
