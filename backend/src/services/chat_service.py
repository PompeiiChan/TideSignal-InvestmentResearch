"""Chat query service backed by SiliconFlow LLM."""

from collections.abc import AsyncIterator
from itertools import count
from typing import Any, Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import MessageRecord, SessionRecord
from ..integrations.langgraph.runner import LangGraphRunner, is_langgraph_enabled
from ..integrations.llm import LLMNotConfiguredError, LLMService
from ..integrations.llm.models import AnswerResult
from ..models.chat import ChatQueryResponse
from ..models.session import MessageRead, MessageRole, SessionRead, SessionSource, TitleSource
from ..repositories.session_repository import SessionRepository
from ..settings import get_settings
from .message_sanitizer import sanitize_assistant_content, sanitize_rich_blocks
from .rag.service import RagService
from .session_service import SessionNotFoundError, _iso, _now

_chat_id_counter = count(1)


class EmptyQueryError(ValueError):
    """Raised when the query is empty after trimming."""


class LLMUnavailableError(RuntimeError):
    """Raised when the configured LLM provider cannot complete the request."""


def _next_id(prefix: str, suffix: str) -> str:
    now = _now()
    return f"{prefix}_{now.strftime('%Y%m%d_%H%M%S')}_{next(_chat_id_counter):03d}_{suffix}"


def _preview_text(content: str, max_len: int = 255) -> str:
    trimmed = content.strip()
    if len(trimmed) <= max_len:
        return trimmed
    return trimmed[: max_len - 1] + "…"


class ChatService:
    """Business logic for POST /api/chat/query using real LLM output."""

    def __init__(
        self,
        db: AsyncSession,
        llm_service: LLMService | None = None,
        rag_service: RagService | None = None,
    ):
        self.db = db
        self.repo = SessionRepository(db)
        self.llm = llm_service or LLMService()
        self.rag = rag_service or RagService()

    async def query(self, session_id: str, source: Literal["client", "admin"], query: str) -> ChatQueryResponse:
        """Persist one user query and one LLM-generated assistant response."""
        result: ChatQueryResponse | None = None
        async for event in self.query_stream(session_id, source, query):
            if event["event"] == "done":
                result = ChatQueryResponse.model_validate(event["data"])
            if event["event"] == "error":
                error_data = cast(dict[str, Any], event["data"])
                message = str(error_data.get("message", "LLM 请求失败"))
                code = int(error_data.get("code", 502))
                if code == 422:
                    raise EmptyQueryError(message)
                if code == 404:
                    raise SessionNotFoundError(message)
                if code == 503:
                    raise LLMNotConfiguredError(message)
                raise LLMUnavailableError(message)
        if result is None:
            raise LLMUnavailableError("LLM 请求未完成")
        return result

    async def query_stream(
        self,
        session_id: str,
        source: Literal["client", "admin"],
        query: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream chat lifecycle events for SSE clients."""
        normalized_query = query.strip()
        if not normalized_query:
            yield {"event": "error", "data": {"message": "query 不能为空", "code": 422}}
            return

        if not self.llm.is_configured():
            yield {"event": "error", "data": {"message": "LLM 配置不完整", "code": 503}}
            return

        session = await self.repo.get_session(session_id)
        if session is None:
            yield {"event": "error", "data": {"message": "会话不存在", "code": 404}}
            return

        user_created_at = _now()
        user_message = MessageRecord(
            id=_next_id("msg", "user"),
            session_id=session.id,
            role="user",
            content=normalized_query,
            rich_blocks=[],
            trace_id=None,
            created_at=user_created_at,
        )
        await self.repo.create_message(user_message)

        if session.is_draft or session.title_source == "system":
            session.title = normalized_query
            session.title_source = "first_query"
            session.is_draft = False
        session.source = source
        session.updated_at = user_created_at
        await self.db.commit()
        await self.db.refresh(session)

        yield {
            "event": "user_message",
            "data": self._to_message_read(user_message).model_dump(),
        }
        yield {
            "event": "session",
            "data": self._to_session_read(session).model_dump(),
        }

        async for event in self._stream_assistant_reply(session, user_message, normalized_query, source):
            yield event

    async def regenerate_stream(
        self,
        session_id: str,
        assistant_message_id: str,
        source: Literal["client", "admin"],
    ) -> AsyncIterator[dict[str, Any]]:
        """Regenerate one assistant reply without creating a new user message."""
        if not self.llm.is_configured():
            yield {"event": "error", "data": {"message": "LLM 配置不完整", "code": 503}}
            return

        session = await self.repo.get_session(session_id)
        if session is None:
            yield {"event": "error", "data": {"message": "会话不存在", "code": 404}}
            return

        assistant_message = await self.repo.get_message(assistant_message_id)
        if assistant_message is None or assistant_message.session_id != session_id:
            yield {"event": "error", "data": {"message": "消息不存在", "code": 404}}
            return
        if assistant_message.role != "assistant":
            yield {"event": "error", "data": {"message": "仅支持重新生成助手消息", "code": 422}}
            return

        user_message = await self.repo.get_previous_user_message(session_id, assistant_message.created_at)
        if user_message is None:
            yield {"event": "error", "data": {"message": "找不到配对的用户消息", "code": 422}}
            return

        normalized_query = user_message.content.strip()
        if not normalized_query:
            yield {"event": "error", "data": {"message": "用户消息内容为空", "code": 422}}
            return

        previous_assistant = await self.repo.get_previous_assistant_message(
            session_id,
            assistant_message.created_at,
        )
        deleted = await self.repo.delete_message(assistant_message_id)
        if not deleted:
            yield {"event": "error", "data": {"message": "消息不存在", "code": 404}}
            return

        session.source = source
        session.updated_at = _now()
        session.last_message_preview = _preview_text(user_message.content)
        session.last_trace_id = previous_assistant.trace_id if previous_assistant else None
        await self.db.commit()
        await self.db.refresh(session)

        yield {
            "event": "user_message",
            "data": self._to_message_read(user_message).model_dump(),
        }
        yield {
            "event": "session",
            "data": self._to_session_read(session).model_dump(),
        }
        yield {
            "event": "message_removed",
            "data": {"assistant_message_id": assistant_message_id},
        }

        async for event in self._stream_assistant_reply(session, user_message, normalized_query, source):
            yield event

    async def _stream_assistant_reply(
        self,
        session: SessionRecord,
        user_message: MessageRecord,
        normalized_query: str,
        source: Literal["client", "admin"],
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream assistant reply via LangGraph orchestration only."""
        if not is_langgraph_enabled(get_settings()):
            yield {
                "event": "error",
                "data": {
                    "message": "LangGraph 未就绪，请设置 LANGGRAPH_ENV=local",
                    "code": 503,
                },
            }
            return

        if not self.llm.is_configured():
            yield {"event": "error", "data": {"message": "LLM 配置不完整", "code": 503}}
            return

        runner = LangGraphRunner(self.llm, self.rag, self.db, settings=get_settings())
        async for event in runner.run_stream(session, user_message, normalized_query, source):
            yield event

    def _normalize_rich_blocks(self, answer: AnswerResult) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for index, block in enumerate(answer.rich_blocks):
            if not isinstance(block, dict):
                continue
            normalized = dict(block)
            normalized.setdefault("id", _next_id("block", f"{index:03d}"))
            normalized.setdefault("title", "回答内容")
            normalized.setdefault("payload", {})
            normalized.setdefault("sources", [])
            normalized.setdefault(
                "risk_notice",
                "以上内容仅为信息整理，不构成投资建议。",
            )
            blocks.append(normalized)

        return blocks

    def _to_session_read(self, session: Any) -> SessionRead:
        return SessionRead(
            id=session.id,
            title=session.title,
            title_source=cast(TitleSource, session.title_source),
            is_draft=session.is_draft,
            source=cast(SessionSource, session.source),
            created_at=_iso(session.created_at),
            updated_at=_iso(session.updated_at),
            last_message_preview=sanitize_assistant_content("assistant", session.last_message_preview),
            last_trace_id=session.last_trace_id,
        )

    def _to_message_read(self, message: MessageRecord) -> MessageRead:
        role = cast(MessageRole, message.role)
        return MessageRead(
            id=message.id,
            session_id=message.session_id,
            role=role,
            content=sanitize_assistant_content(message.role, message.content),
            rich_blocks=sanitize_rich_blocks(message.role, message.rich_blocks),
            trace_id=message.trace_id,
            created_at=_iso(message.created_at),
        )
