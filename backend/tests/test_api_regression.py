"""Full-chain API regression smoke tests (isolated DB, no browser)."""

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
    db_path = tmp_path / "test_api_regression.db"
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


@pytest.mark.asyncio
async def test_full_api_regression_chain(tmp_path: Path) -> None:
    """Exercise health, sessions, chat, trace, layout, data sources and config APIs."""
    async with api_client(tmp_path) as client:
        health = await client.get("/api/health")
        assert health.status_code == 200
        health_body = health.json()
        assert health_body["code"] == 200
        assert health_body["data"]["status"] == "ok"

        layout_get = await client.get("/api/layout/preferences")
        assert layout_get.status_code == 200

        create_session = await client.post("/api/sessions", json={"source": "client"})
        assert create_session.status_code == 200
        session_payload = create_session.json()["data"]
        session_id = session_payload["id"]

        list_sessions = await client.get("/api/sessions")
        assert list_sessions.status_code == 200
        assert any(item["id"] == session_id for item in list_sessions.json()["data"]["items"])

        chat = await client.post(
            "/api/chat/query",
            json={
                "session_id": session_id,
                "source": "client",
                "query": "机器人板块最近有哪些政策催化",
            },
        )
        assert chat.status_code == 200
        chat_data = chat.json()["data"]
        trace_id = chat_data["trace"]["id"]
        assert chat_data["assistant_message"]["role"] == "assistant"

        detail = await client.get(f"/api/sessions/{session_id}")
        assert detail.status_code == 200
        detail_data = detail.json()["data"]
        assert detail_data["session"]["id"] == session_id
        assert len(detail_data["messages"]) >= 2

        trace = await client.get(f"/api/traces/{trace_id}")
        assert trace.status_code == 200
        trace_data = trace.json()["data"]
        assert trace_data["steps"]
        assert any(step["node"] == "intent_recognition" for step in trace_data["steps"])
        assert any(step["node"] == "context_preprocess" for step in trace_data["steps"])

        first_step_id = trace_data["steps"][0]["step_id"]
        raw = await client.get(f"/api/traces/{trace_id}/steps/{first_step_id}/raw")
        assert raw.status_code == 200
        assert raw.json()["data"]["step_id"] == first_step_id

        layout_patch = await client.patch(
            "/api/layout/preferences",
            json={"sidebar_width": 336, "trace_panel_width": 520},
        )
        assert layout_patch.status_code == 200

        data_sources = await client.get("/api/data-sources/status")
        assert data_sources.status_code == 200
        ds_data = data_sources.json()["data"]
        assert ds_data["mock_data"]
        assert ds_data["rag"]["status"] in {"mocked", "fallback", "ready"}

        config_status = await client.get("/api/config/status")
        assert config_status.status_code == 200
        cfg_data = config_status.json()["data"]
        assert cfg_data["models"]
        page_text = str(cfg_data)
        assert "sk-" not in page_text
        assert "Bearer " not in page_text

        delete_session = await client.delete(f"/api/sessions/{session_id}")
        assert delete_session.status_code == 200

        after_delete = await client.get("/api/sessions")
        assert all(item["id"] != session_id for item in after_delete.json()["data"]["items"])
