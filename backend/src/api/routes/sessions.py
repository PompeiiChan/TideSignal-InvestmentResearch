"""Session history API routes."""

from typing import cast

from fastapi import Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter
from pycore.api.responses import APIResponse, success_response

from ...api.deps import get_session
from ...models.session import (
    DeleteSessionRead,
    SessionCreate,
    SessionDetailRead,
    SessionPageRead,
    SessionRead,
)
from ...services.session_service import SessionNotFoundError, SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
DB_SESSION_DEPENDENCY = Depends(get_session)


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": message, "data": None},
    )


@router.get("", response_model=APIResponse[SessionPageRead])
async def list_sessions(
    keyword: str = "",
    page: int = Query(default=1),
    page_size: int = Query(default=20),
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[SessionPageRead] | JSONResponse:
    """List sessions with keyword filtering."""
    try:
        data = await SessionService(db).list_sessions(keyword, page, page_size)
    except ValueError as exc:
        return _error(str(exc), 400)
    return cast(APIResponse[SessionPageRead], success_response(data=data.model_dump()))


@router.post("", response_model=APIResponse[SessionRead])
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[SessionRead]:
    """Create a draft session."""
    data = await SessionService(db).create_session(payload.source)
    return cast(APIResponse[SessionRead], success_response(data=data.model_dump()))


@router.get("/{session_id}", response_model=APIResponse[SessionDetailRead])
async def get_session_detail(
    session_id: str,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[SessionDetailRead] | JSONResponse:
    """Return a session detail and its messages."""
    try:
        data = await SessionService(db).get_detail(session_id)
    except SessionNotFoundError as exc:
        return _error(str(exc), 404)
    return cast(APIResponse[SessionDetailRead], success_response(data=data.model_dump()))


@router.delete("/{session_id}", response_model=APIResponse[DeleteSessionRead])
async def delete_session(
    session_id: str,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[DeleteSessionRead] | JSONResponse:
    """Delete a session."""
    try:
        data = await SessionService(db).delete_session(session_id)
    except SessionNotFoundError as exc:
        return _error(str(exc), 404)
    return cast(APIResponse[DeleteSessionRead], success_response(data=data.model_dump()))
