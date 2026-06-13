"""Trace detail API routes."""

from typing import cast

from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter
from pycore.api.responses import APIResponse, success_response

from ...api.deps import get_session
from ...models.trace import RawTraceStepRead, TraceRead
from ...services.trace_service import TraceNotFoundError, TraceService, TraceStepNotFoundError

router = APIRouter(prefix="/api/traces", tags=["traces"])
DB_SESSION_DEPENDENCY = Depends(get_session)


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": message, "data": None},
    )


@router.get("/{trace_id}", response_model=APIResponse[TraceRead])
async def get_trace_detail(
    trace_id: str,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[TraceRead] | JSONResponse:
    """Return the full Trace timeline."""
    try:
        data = await TraceService(db).get_trace(trace_id)
    except TraceNotFoundError as exc:
        return _error(str(exc), 404)
    return cast(APIResponse[TraceRead], success_response(data=data.model_dump()))


@router.get("/{trace_id}/steps/{step_id}/raw", response_model=APIResponse[RawTraceStepRead])
async def get_trace_step_raw(
    trace_id: str,
    step_id: str,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[RawTraceStepRead] | JSONResponse:
    """Return one Trace step raw JSON payload."""
    try:
        data = await TraceService(db).get_step_raw(trace_id, step_id)
    except TraceStepNotFoundError as exc:
        return _error(str(exc), 404)
    except TraceNotFoundError as exc:
        return _error(str(exc), 404)
    return cast(APIResponse[RawTraceStepRead], success_response(data=data.model_dump()))
