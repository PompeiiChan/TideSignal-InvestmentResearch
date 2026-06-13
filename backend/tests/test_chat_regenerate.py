"""Tests for POST /api/chat/regenerate/stream."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_session
from backend.src.db.models import Base
from backend.src.main import app


@asynccontextmanager
async def api_client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Create an ASGI client backed by an isolated SQLite database."""
    db_path = tmp_path / "test_regenerate.db"
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
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        event_name = "message"
        data_raw = ""
        for line in chunk.split("\n"):
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_raw += line[5:].strip()
        if data_raw:
            events.append((event_name, json.loads(data_raw)))
    return events


@pytest.mark.asyncio
async def test_regenerate_stream_replaces_assistant_without_new_user(tmp_path: Path) -> None:
    """Regenerate deletes old assistant, keeps user message, and returns a new assistant."""
    async with api_client(tmp_path) as client:
        create_response = await client.post("/api/sessions", json={"source": "client"})
        session_id = create_response.json()["data"]["id"]

        query = "15元买入未来预期回报率怎么算"
        chat_response = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "client", "query": query},
        )
        assert chat_response.status_code == 200
        first_data = chat_response.json()["data"]
        user_message_id = first_data["user_message"]["id"]
        old_assistant_id = first_data["assistant_message"]["id"]

        regenerate_response = await client.post(
            "/api/chat/regenerate/stream",
            json={
                "session_id": session_id,
                "assistant_message_id": old_assistant_id,
                "source": "client",
            },
        )
        assert regenerate_response.status_code == 200
        events = _parse_sse_events(regenerate_response.text)
        event_names = [name for name, _ in events]
        assert "message_removed" in event_names
        assert "done" in event_names

        removed = next(data for name, data in events if name == "message_removed")
        assert removed["assistant_message_id"] == old_assistant_id

        done = next(data for name, data in events if name == "done")
        assert done["user_message"]["id"] == user_message_id
        new_assistant_id = done["assistant_message"]["id"]
        assert new_assistant_id != old_assistant_id
        assert done["assistant_message"]["role"] == "assistant"

        detail_response = await client.get(f"/api/sessions/{session_id}")
        messages = detail_response.json()["data"]["messages"]
        assert [message["role"] for message in messages] == ["user", "assistant"]
        assert messages[0]["id"] == user_message_id
        assert messages[1]["id"] == new_assistant_id
        assert all(message["id"] != old_assistant_id for message in messages)


@pytest.mark.asyncio
async def test_regenerate_stream_rejects_non_assistant_message(tmp_path: Path) -> None:
    """Regenerate returns SSE error when target message is not an assistant reply."""
    async with api_client(tmp_path) as client:
        create_response = await client.post("/api/sessions", json={"source": "client"})
        session_id = create_response.json()["data"]["id"]

        chat_response = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "client", "query": "今天半导体排行怎么样"},
        )
        user_message_id = chat_response.json()["data"]["user_message"]["id"]

        regenerate_response = await client.post(
            "/api/chat/regenerate/stream",
            json={
                "session_id": session_id,
                "assistant_message_id": user_message_id,
                "source": "client",
            },
        )
        assert regenerate_response.status_code == 200
        events = _parse_sse_events(regenerate_response.text)
        error = next(data for name, data in events if name == "error")
        assert error["code"] == 422
