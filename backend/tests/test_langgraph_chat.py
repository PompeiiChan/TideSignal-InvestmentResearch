"""Chat API tests for LangGraph orchestration gate."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_session
from backend.src.db.models import Base
from backend.src.integrations.llm.service import LLMService
from backend.src.main import app


def _mock_llm_json_responses(responses: list[dict[str, Any]]) -> Any:
    queue = list(responses)

    async def _chat_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        payload = queue.pop(0)
        return {
            "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
            "usage": {},
        }

    return _chat_completion


@asynccontextmanager
async def api_client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Create an ASGI client backed by an isolated SQLite database."""
    db_path = tmp_path / "test_langgraph_chat.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            trust_env=False,
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data_payload: dict = {}
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_payload = json.loads(line.split(":", 1)[1].strip())
        events.append((event_name, data_payload))
    return events


@pytest.mark.asyncio
async def test_chat_stream_returns_done_when_langgraph_enabled(tmp_path: Path) -> None:
    """POST /api/chat/query/stream yields done when LANGGRAPH_ENV=local."""
    async with api_client(tmp_path) as client:
        create_response = await client.post("/api/sessions", json={"source": "client"})
        session_id = create_response.json()["data"]["id"]

        stream_response = await client.post(
            "/api/chat/query/stream",
            json={
                "session_id": session_id,
                "source": "client",
                "query": "今天半导体排行怎么样",
            },
        )
        assert stream_response.status_code == 200
        events = _parse_sse_events(stream_response.text)
        event_names = [name for name, _ in events]
        assert "done" in event_names
        done_payload = next(payload for name, payload in events if name == "done")
        assert done_payload["assistant_message"]["role"] == "assistant"
        assert done_payload["trace"]["id"]

        trace_response = await client.get(f"/api/traces/{done_payload['trace']['id']}")
        trace_steps = trace_response.json()["data"]["steps"]
        assert trace_steps[0]["node"] == "context_preprocess"


@pytest.mark.asyncio
async def test_clarification_stream_emits_response_stream_start_before_content_done(
    tmp_path: Path,
    mock_llm_service: LLMService,
) -> None:
    """Clarification non-streaming path must fold timeline before content_done."""
    mock_responses: list[dict[str, Any]] = [
        {
            "intent_id": "unknown",
            "intent_confidence": 0.4,
            "candidate_intents": [{"intent_id": "unknown", "confidence": 0.4}],
            "missing_slots": [],
        },
        {"slots": {}, "slot_confidence": {}, "missing_slots": [], "ambiguous_slots": []},
        {
            "final_response": "请说明您想查询的热点、个股还是数据指标？",
            "next_expected_slots": ["intent_scope"],
            "clarification_questions": ["您想了解哪类投研问题？"],
        },
    ]
    mock_llm_service._intent_call_count = 0
    mock_llm_service._intent_client = lambda: type(  # type: ignore[method-assign]
        "MockClient",
        (),
        {
            "chat_completion": _mock_llm_json_responses(mock_responses),
            "extract_message_content": staticmethod(
                lambda body: body["choices"][0]["message"]["content"]
            ),
        },
    )()
    async with api_client(tmp_path) as client:
        create_response = await client.post("/api/sessions", json={"source": "client"})
        session_id = create_response.json()["data"]["id"]

        stream_response = await client.post(
            "/api/chat/query/stream",
            json={"session_id": session_id, "source": "client", "query": "那个怎么样"},
        )
        assert stream_response.status_code == 200
        events = _parse_sse_events(stream_response.text)
        event_names = [name for name, _ in events]
        assert "response_stream_start" in event_names
        assert "content_done" in event_names
        assert "content_delta" not in event_names
        assert event_names.index("response_stream_start") < event_names.index("content_done")


@pytest.mark.asyncio
async def test_fallback_stream_emits_response_stream_start_before_content_done(
    tmp_path: Path,
    mock_llm_service: LLMService,
) -> None:
    """Fallback non-streaming path must fold timeline before content_done."""
    mock_responses: list[dict[str, Any]] = [
        {
            "intent_id": "prediction_request",
            "intent_confidence": 0.9,
            "candidate_intents": [{"intent_id": "prediction_request", "confidence": 0.9}],
            "missing_slots": [],
        },
        {"slots": {}, "slot_confidence": {}, "missing_slots": [], "ambiguous_slots": []},
    ]
    mock_llm_service._intent_call_count = 0
    mock_llm_service._intent_client = lambda: type(  # type: ignore[method-assign]
        "MockClient",
        (),
        {
            "chat_completion": _mock_llm_json_responses(mock_responses),
            "extract_message_content": staticmethod(
                lambda body: body["choices"][0]["message"]["content"]
            ),
        },
    )()
    async with api_client(tmp_path) as client:
        create_response = await client.post("/api/sessions", json={"source": "client"})
        session_id = create_response.json()["data"]["id"]

        stream_response = await client.post(
            "/api/chat/query/stream",
            json={
                "session_id": session_id,
                "source": "client",
                "query": "预测明天泸州老窖会涨到多少目标价？",
            },
        )
        assert stream_response.status_code == 200
        events = _parse_sse_events(stream_response.text)
        event_names = [name for name, _ in events]
        assert "response_stream_start" in event_names
        assert "content_done" in event_names
        assert "content_delta" not in event_names
        assert event_names.index("response_stream_start") < event_names.index("content_done")


@pytest.mark.asyncio
async def test_chat_query_returns_503_when_langgraph_disabled(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """POST /api/chat/query returns 503 when LANGGRAPH_ENV is not local."""
    monkeypatch.setattr(
        "backend.src.services.chat_service.is_langgraph_enabled",
        lambda settings=None: False,
    )

    async with api_client(tmp_path) as client:
        create_response = await client.post("/api/sessions", json={"source": "client"})
        session_id = create_response.json()["data"]["id"]

        chat_response = await client.post(
            "/api/chat/query",
            json={
                "session_id": session_id,
                "source": "client",
                "query": "今天半导体排行怎么样",
            },
        )
        assert chat_response.status_code == 503
        assert chat_response.json()["message"] == "LangGraph 未就绪，请设置 LANGGRAPH_ENV=local"
