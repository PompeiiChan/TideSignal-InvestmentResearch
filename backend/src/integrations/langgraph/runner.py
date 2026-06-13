"""LangGraph runner for chat orchestration."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from itertools import count
from typing import Any, Literal, cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import MessageRecord, SessionRecord
from ...integrations.llm.client import LLMClientError
from ...integrations.llm.service import LLMService
from ...models.chat import ChatQueryResponse
from ...models.session import MessageRead, MessageRole, SessionRead, SessionSource, TitleSource
from ...repositories.session_repository import SessionRepository
from ...services.message_sanitizer import sanitize_assistant_content, sanitize_rich_blocks
from ...services.rag.service import RagService
from ...services.session_service import _iso, _now
from ...services.trace_service import TraceService
from ...settings import AppSettings, get_settings
from .graph import GraphDeps, build_graph
from .state import AgentState
from .status_phases import build_status_event
from .trace_recorder import TraceRecorder

_runner_id_counter = count(1)


def is_langgraph_enabled(settings: AppSettings | None = None) -> bool:
    """Return True when LANGGRAPH_ENV is set to local."""
    active = settings or get_settings()
    return active.langgraph_env.strip() == "local"


def _next_id(prefix: str, suffix: str) -> str:
    now = _now()
    return f"{prefix}_{now.strftime('%Y%m%d_%H%M%S')}_{next(_runner_id_counter):03d}_{suffix}"


def _preview_text(content: str, max_len: int = 255) -> str:
    trimmed = content.strip()
    if len(trimmed) <= max_len:
        return trimmed
    return trimmed[: max_len - 1] + "…"


class LangGraphRunner:
    """Execute the compiled LangGraph workflow."""

    def __init__(
        self,
        llm: LLMService,
        rag: RagService,
        db: AsyncSession,
        *,
        settings: AppSettings | None = None,
    ) -> None:
        self.llm = llm
        self.rag = rag
        self.db = db
        self.settings = settings or get_settings()
        self._graph = build_graph(
            GraphDeps(llm=self.llm, rag=self.rag, settings=self.settings)
        )
        self._repo = SessionRepository(db)

    def _build_chat_history(self, session: SessionRecord, *, limit: int = 10) -> list[dict[str, str]]:
        messages = sorted(session.messages or [], key=lambda item: item.created_at)
        recent = messages[-limit:]
        return [{"role": str(message.role), "content": message.content} for message in recent]

    @staticmethod
    def _drain_stream_queue(queue: asyncio.Queue[dict[str, Any]]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while not queue.empty():
            events.append(queue.get_nowait())
        return events

    async def _run_graph_loop(
        self,
        initial_state: AgentState,
        *,
        event_queue: asyncio.Queue[dict[str, Any]],
        emitted_status_nodes: set[str],
    ) -> dict[str, Any]:
        """Execute the graph; node entry statuses are pushed via stream_callback."""
        _ = emitted_status_nodes
        final_state: dict[str, Any] | None = None
        async for state_snapshot in self._graph.astream(initial_state, stream_mode="values"):
            final_state = dict(state_snapshot)
        if final_state is None:
            return {}
        return final_state

    @staticmethod
    async def _yield_events_during_task(
        event_queue: asyncio.Queue[dict[str, Any]],
        graph_task: asyncio.Task[dict[str, Any]],
        *,
        poll_interval_s: float = 0.02,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield queued stream events while a graph task is still running."""
        while True:
            drained = False
            for event in LangGraphRunner._drain_stream_queue(event_queue):
                yield event
                drained = True

            if graph_task.done():
                for event in LangGraphRunner._drain_stream_queue(event_queue):
                    yield event
                break

            if not drained:
                await asyncio.sleep(poll_interval_s)

    def _normalize_rich_blocks(
        self,
        content: str,
        blocks: list[dict[str, Any]],
        response_kind: str,
    ) -> list[dict[str, Any]]:
        normalized_blocks: list[dict[str, Any]] = []
        for index, block in enumerate(blocks):
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
            normalized_blocks.append(normalized)

        _ = content, response_kind
        if not normalized_blocks:
            normalized_blocks = []
            for index, block in enumerate(normalized_blocks):
                block.setdefault("id", _next_id("block", f"{index:03d}"))
        return normalized_blocks

    def _to_session_read(self, session: SessionRecord) -> SessionRead:
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

    def _append_end_step(self, final_state: dict[str, Any]) -> dict[str, Any]:
        trace_steps = list(final_state.get("trace_steps") or [])
        end_step = TraceRecorder.record(
            node="END",
            step_index=len(trace_steps) + 1,
            status="success",
            latency_ms=0,
            input_data={"user_query": final_state.get("user_query", "")},
            output_data={
                "response": final_state.get("final_response", ""),
                "trace_id": final_state.get("trace_id", ""),
            },
            summary="流程结束",
        )
        final_state["trace_steps"] = trace_steps + [end_step]
        final_state["current_node"] = "END"
        return final_state

    async def run_stream(
        self,
        session: SessionRecord,
        user_message: MessageRecord,
        normalized_query: str,
        source: Literal["client", "admin"],
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream SSE events while executing the LangGraph workflow."""
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        streamed_content = False
        writing_status_emitted = False

        def stream_callback(event: dict[str, Any]) -> None:
            nonlocal streamed_content, writing_status_emitted
            if event.get("event") == "content_delta":
                streamed_content = True
                if not writing_status_emitted:
                    event_queue.put_nowait(build_status_event("writing", "Writing"))
                    writing_status_emitted = True
            event_queue.put_nowait(event)

        if hasattr(self.llm, "_intent_call_count"):
            self.llm._intent_call_count = 0

        trace_id = _next_id("trace", "local")
        assistant_message_id = _next_id("msg", "assistant")
        chat_history = self._build_chat_history(session)

        initial_state: AgentState = {
            "session_id": session.id,
            "message_id": assistant_message_id,
            "trace_id": trace_id,
            "user_query": normalized_query,
            "chat_history": chat_history,
            "request_meta": {"source": source},
            "stream_callback": stream_callback,
            "trace_steps": [],
        }

        event_queue.put_nowait(build_status_event("thinking", "Thinking"))

        graph_task = asyncio.create_task(
            self._run_graph_loop(
                initial_state,
                event_queue=event_queue,
                emitted_status_nodes=set(),
            )
        )

        try:
            async for event in self._yield_events_during_task(event_queue, graph_task):
                yield event
            final_state = await graph_task
        except LLMClientError as exc:
            graph_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await graph_task
            yield {"event": "error", "data": {"message": str(exc), "code": 502}}
            return
        except Exception as exc:
            graph_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await graph_task
            yield {"event": "error", "data": {"message": str(exc), "code": 500}}
            return

        if not final_state:
            yield {"event": "error", "data": {"message": "LangGraph 执行未完成", "code": 500}}
            return

        final_state = self._append_end_step(final_state)
        content = str(final_state.get("final_response", "")).strip()
        response_kind = str(final_state.get("response_kind", "data"))
        raw_blocks = final_state.get("rich_blocks") or []
        rich_blocks = sanitize_rich_blocks(
            "assistant",
            self._normalize_rich_blocks(
                content,
                raw_blocks if isinstance(raw_blocks, list) else [],
                response_kind,
            ),
        )

        if not streamed_content:
            if content:
                yield {"event": "content_done", "data": {"content": content}}
        if rich_blocks:
            yield {"event": "rich_blocks", "data": {"rich_blocks": rich_blocks}}

        assistant_created_at = _now()
        assistant_message = MessageRecord(
            id=assistant_message_id,
            session_id=session.id,
            role="assistant",
            content=content,
            rich_blocks=rich_blocks,
            trace_id=trace_id,
            created_at=assistant_created_at,
        )

        session.source = source
        session.updated_at = assistant_created_at
        session.last_message_preview = _preview_text(content)
        session.last_trace_id = trace_id

        await self._repo.create_message(assistant_message)
        trace = await TraceService(self.db).create_langgraph_trace(
            trace_id=trace_id,
            session_id=session.id,
            message_id=assistant_message.id,
            user_query=normalized_query,
            steps=list(final_state.get("trace_steps") or []),
        )
        await self.db.commit()
        await self.db.refresh(session)

        response = ChatQueryResponse(
            session=self._to_session_read(session),
            user_message=self._to_message_read(user_message),
            assistant_message=self._to_message_read(assistant_message),
            trace=TraceService(self.db).to_summary(trace),
        )
        yield {"event": "done", "data": response.model_dump()}

    async def ainvoke(
        self,
        initial_state: AgentState | None = None,
        *,
        user_query: str | None = None,
        session_id: str | None = None,
        chat_history: list[dict[str, str]] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Run the graph to completion and return final state with trace_steps."""
        state: AgentState = {**(initial_state or {})}
        if user_query is not None:
            state["user_query"] = user_query
        if session_id is not None:
            state["session_id"] = session_id
        if chat_history is not None:
            state["chat_history"] = chat_history

        if "user_query" not in state:
            state["user_query"] = ""
        if "session_id" not in state:
            state["session_id"] = session_id or ""
        if "chat_history" not in state:
            state["chat_history"] = chat_history or []
        if "trace_id" not in state:
            state["trace_id"] = f"trace_{uuid4().hex[:12]}"
        if "message_id" not in state:
            state["message_id"] = f"msg_{uuid4().hex[:12]}"
        for key, value in extra.items():
            state[key] = value  # type: ignore[literal-required]

        result = await self._graph.ainvoke(state)
        final_state = dict(result)
        return self._append_end_step(final_state)
