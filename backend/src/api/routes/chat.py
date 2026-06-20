"""Chat query API routes."""

import json
from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import Depends, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter
from pycore.api.responses import APIResponse, success_response

from ...api.demo_quota_deps import VISITOR_HEADER, enforce_demo_quota
from ...api.deps import get_session
from ...integrations.llm import LLMNotConfiguredError
from ...models.chat import ChatQueryRequest, ChatQueryResponse, ChatRegenerateRequest
from ...services.chat_service import ChatService, EmptyQueryError, LLMUnavailableError
from ...services.demo_quota import DemoQuotaExceededError
from ...services.session_service import SessionNotFoundError

router = APIRouter(prefix="/api/chat", tags=["chat"])
DB_SESSION_DEPENDENCY = Depends(get_session)


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": message, "data": None},
    )


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/query", response_model=APIResponse[ChatQueryResponse])
async def post_chat_query(
    payload: ChatQueryRequest,
    request: Request,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
    x_demo_visitor_id: str | None = Header(default=None, alias=VISITOR_HEADER),
) -> APIResponse[ChatQueryResponse] | JSONResponse:
    """Persist a user query and return an LLM-generated assistant response."""
    try:
        await enforce_demo_quota(db, request=request, visitor_id=x_demo_visitor_id)
        await db.commit()
        data = await ChatService(db).query(payload.session_id, payload.source, payload.query)
    except DemoQuotaExceededError as exc:
        await db.rollback()
        return _error(str(exc), 429)
    except ValueError as exc:
        await db.rollback()
        return _error(str(exc), 400)
    except EmptyQueryError as exc:
        return _error(str(exc), 422)
    except SessionNotFoundError as exc:
        return _error(str(exc), 404)
    except LLMNotConfiguredError as exc:
        return _error(str(exc), 503)
    except LLMUnavailableError as exc:
        return _error(str(exc), 502)
    return cast(APIResponse[ChatQueryResponse], success_response(data=data.model_dump()))


@router.post("/query/stream", response_model=None)
async def post_chat_query_stream(
    payload: ChatQueryRequest,
    request: Request,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
    x_demo_visitor_id: str | None = Header(default=None, alias=VISITOR_HEADER),
) -> StreamingResponse | JSONResponse:
    """Stream chat query lifecycle as Server-Sent Events."""
    try:
        await enforce_demo_quota(db, request=request, visitor_id=x_demo_visitor_id)
        await db.commit()
    except DemoQuotaExceededError as exc:
        await db.rollback()
        return _error(str(exc), 429)
    except ValueError as exc:
        await db.rollback()
        return _error(str(exc), 400)

    async def event_generator() -> AsyncIterator[str]:
        async for item in ChatService(db).query_stream(payload.session_id, payload.source, payload.query):
            yield _sse(str(item["event"]), item["data"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/regenerate/stream", response_model=None)
async def post_chat_regenerate_stream(
    payload: ChatRegenerateRequest,
    request: Request,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
    x_demo_visitor_id: str | None = Header(default=None, alias=VISITOR_HEADER),
) -> StreamingResponse | JSONResponse:
    """Stream assistant regeneration lifecycle as Server-Sent Events."""
    try:
        await enforce_demo_quota(db, request=request, visitor_id=x_demo_visitor_id)
        await db.commit()
    except DemoQuotaExceededError as exc:
        await db.rollback()
        return _error(str(exc), 429)
    except ValueError as exc:
        await db.rollback()
        return _error(str(exc), 400)

    async def event_generator() -> AsyncIterator[str]:
        async for item in ChatService(db).regenerate_stream(
            payload.session_id,
            payload.assistant_message_id,
            payload.source,
        ):
            yield _sse(str(item["event"]), item["data"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
