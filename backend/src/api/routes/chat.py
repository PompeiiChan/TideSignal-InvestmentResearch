"""Chat query API routes."""

import json
from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter
from pycore.api.responses import APIResponse, success_response

from ...api.deps import get_session
from ...integrations.llm import LLMNotConfiguredError
from ...models.chat import ChatQueryRequest, ChatQueryResponse, ChatRegenerateRequest
from ...services.chat_service import ChatService, EmptyQueryError, LLMUnavailableError
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
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> APIResponse[ChatQueryResponse] | JSONResponse:
    """Persist a user query and return an LLM-generated assistant response."""
    try:
        data = await ChatService(db).query(payload.session_id, payload.source, payload.query)
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
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> StreamingResponse:
    """Stream chat query lifecycle as Server-Sent Events."""

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
    db: AsyncSession = DB_SESSION_DEPENDENCY,
) -> StreamingResponse:
    """Stream assistant regeneration lifecycle as Server-Sent Events."""

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
