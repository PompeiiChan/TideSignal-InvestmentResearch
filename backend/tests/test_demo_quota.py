"""Tests for demo daily question quota."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_session
from backend.src.db.models import Base
from backend.src.main import app
from backend.src.settings import AppSettings, get_settings


@asynccontextmanager
async def quota_client(
    tmp_path: Path,
    *,
    settings: AppSettings,
) -> AsyncGenerator[AsyncClient, None]:
    db_path = tmp_path / "test_demo_quota.db"
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


def _enable_demo_quota(monkeypatch: MonkeyPatch, *, daily_limit: int = 3) -> str:
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_quota_enabled", True)
    monkeypatch.setattr(settings, "demo_quota_daily_limit", daily_limit)
    monkeypatch.setattr(settings, "demo_quota_ip_daily_limit", 20)
    return str(uuid4())


@pytest.mark.asyncio
async def test_demo_quota_disabled_returns_full_remaining(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_quota_enabled", False)
    visitor_id = str(uuid4())

    async with quota_client(tmp_path, settings=settings) as client:
        response = await client.get(
            "/api/demo/quota",
            headers={"X-Demo-Visitor-Id": visitor_id},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["enabled"] is False
        assert data["remaining"] == data["limit"]


@pytest.mark.asyncio
async def test_demo_quota_consumes_and_blocks_at_limit(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    settings = get_settings()
    visitor_id = _enable_demo_quota(monkeypatch, daily_limit=2)

    async with quota_client(tmp_path, settings=settings) as client:
        create_session = await client.post("/api/sessions", json={"source": "client"})
        session_id = create_session.json()["data"]["id"]
        headers = {"X-Demo-Visitor-Id": visitor_id}

        first = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "client", "query": "机器人板块最近有哪些政策催化"},
            headers=headers,
        )
        assert first.status_code == 200

        quota_after_one = await client.get("/api/demo/quota", headers=headers)
        assert quota_after_one.json()["data"]["used"] == 1
        assert quota_after_one.json()["data"]["remaining"] == 1

        second = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "client", "query": "半导体板块涨幅排行"},
            headers=headers,
        )
        assert second.status_code == 200

        quota_after_two = await client.get("/api/demo/quota", headers=headers)
        assert quota_after_two.json()["data"]["remaining"] == 0

        third = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "client", "query": "宁德时代基本面怎么样"},
            headers=headers,
        )
        assert third.status_code == 429
        assert "额度" in third.json()["message"]


@pytest.mark.asyncio
async def test_demo_quota_rejects_invalid_visitor_id(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    settings = get_settings()
    _enable_demo_quota(monkeypatch, daily_limit=2)

    async with quota_client(tmp_path, settings=settings) as client:
        create_session = await client.post("/api/sessions", json={"source": "client"})
        session_id = create_session.json()["data"]["id"]

        response = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "client", "query": "测试"},
            headers={"X-Demo-Visitor-Id": "not-a-valid-uuid"},
        )
        assert response.status_code == 400
