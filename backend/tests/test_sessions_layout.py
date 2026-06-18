"""Tests for session history and layout preference APIs."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_session
from backend.src.db.models import Base
from backend.src.main import app
from backend.src.services.message_sanitizer import sanitize_assistant_content, sanitize_rich_blocks


@asynccontextmanager
async def api_client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Create an ASGI client backed by an isolated SQLite database."""
    db_path = tmp_path / "test_sessions.db"
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
async def test_session_history_create_detail_search_and_delete(tmp_path: Path) -> None:
    """Session endpoints provide a complete history CRUD loop."""
    async with api_client(tmp_path) as client:
        list_response = await client.get("/api/sessions")
        assert list_response.status_code == 200
        list_body = list_response.json()
        assert list_body["code"] == 200
        assert list_body["data"]["total"] >= 4
        first_session_id = list_body["data"]["items"][0]["id"]

        detail_response = await client.get(f"/api/sessions/{first_session_id}")
        assert detail_response.status_code == 200
        detail_body = detail_response.json()
        assert detail_body["data"]["session"]["id"] == first_session_id
        assert len(detail_body["data"]["messages"]) == 2

        search_response = await client.get("/api/sessions", params={"keyword": "半导体"})
        assert search_response.status_code == 200
        search_items = search_response.json()["data"]["items"]
        assert len(search_items) == 1
        assert "半导体" in search_items[0]["title"]

        create_response = await client.post("/api/sessions", json={"source": "client"})
        assert create_response.status_code == 200
        created = create_response.json()["data"]
        assert created["title"] == "新对话"
        assert created["is_draft"] is True

        created_detail_response = await client.get(f"/api/sessions/{created['id']}")
        assert created_detail_response.status_code == 200
        assert created_detail_response.json()["data"]["messages"] == []

        delete_response = await client.delete(f"/api/sessions/{created['id']}")
        assert delete_response.status_code == 200
        assert delete_response.json()["data"] == {"id": created["id"], "deleted": True}

        missing_response = await client.get(f"/api/sessions/{created['id']}")
        assert missing_response.status_code == 404
        assert missing_response.json() == {"code": 404, "message": "会话不存在", "data": None}


@pytest.mark.asyncio
async def test_session_page_size_returns_contract_error(tmp_path: Path) -> None:
    """Invalid page size returns the documented unified error shape."""
    async with api_client(tmp_path) as client:
        response = await client.get("/api/sessions", params={"page_size": 101})

    assert response.status_code == 400
    assert response.json() == {
        "code": 400,
        "message": "page_size 必须在 1 到 100 之间",
        "data": None,
    }


@pytest.mark.asyncio
async def test_chat_query_persists_messages_and_updates_draft_title(tmp_path: Path) -> None:
    """POST /api/chat/query closes the fallback chat loop and persists messages."""
    async with api_client(tmp_path) as client:
        create_response = await client.post("/api/sessions", json={"source": "client"})
        assert create_response.status_code == 200
        session_id = create_response.json()["data"]["id"]

        query = "15元买入未来预期回报率怎么算"
        chat_response = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "client", "query": query},
        )

        assert chat_response.status_code == 200
        body = chat_response.json()
        assert body["code"] == 200
        data = body["data"]
        assert data["session"]["id"] == session_id
        assert data["session"]["title"] == query
        assert data["session"]["title_source"] == "first_query"
        assert data["session"]["is_draft"] is False
        assert data["session"]["last_trace_id"] == data["trace"]["id"]
        assert data["session"]["last_message_preview"] == data["assistant_message"]["content"]
        assert data["user_message"]["role"] == "user"
        assert data["assistant_message"]["role"] == "assistant"
        assert data["assistant_message"]["trace_id"] == data["trace"]["id"]
        rich_types = {block["type"] for block in data["assistant_message"]["rich_blocks"]}
        assert "calculator" in rich_types
        assert "citation_list" not in rich_types
        assert "risk_notice" not in rich_types
        assert "不构成投资建议" in data["assistant_message"]["content"]
        assert data["trace"]["metadata"]["quality_check_result"] == "PASS"
        assert data["trace"]["metadata"]["tool_calls_count"] == 1

        detail_response = await client.get(f"/api/sessions/{session_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()["data"]
        assert detail_data["session"]["title"] == query
        assert detail_data["session"]["last_trace_id"] == data["trace"]["id"]
        assert [message["role"] for message in detail_data["messages"]] == ["user", "assistant"]
        assert detail_data["messages"][1]["rich_blocks"] == data["assistant_message"]["rich_blocks"]


@pytest.mark.asyncio
async def test_trace_detail_and_raw_json_api(tmp_path: Path) -> None:
    """T-005 Trace endpoints return full fallback timelines and raw step JSON."""
    async with api_client(tmp_path) as client:
        create_response = await client.post("/api/sessions", json={"source": "admin"})
        session_id = create_response.json()["data"]["id"]

        query = "今天半导体排行怎么样"
        chat_response = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "admin", "query": query},
        )
        assert chat_response.status_code == 200
        trace_id = chat_response.json()["data"]["trace"]["id"]

        trace_response = await client.get(f"/api/traces/{trace_id}")
        assert trace_response.status_code == 200
        trace_body = trace_response.json()
        assert trace_body["code"] == 200
        trace = trace_body["data"]
        assert trace["id"] == trace_id
        assert trace["session_id"] == session_id
        assert trace["message_id"] == chat_response.json()["data"]["assistant_message"]["id"]
        assert trace["user_query"] == query
        assert trace["status"] == "success"
        node_names = [step["node"] for step in trace["steps"]]
        assert trace["steps"][0]["node"] == "context_preprocess"
        assert "intent_recognition" in node_names
        assert "routing_decision" in node_names
        assert "tool_call" in node_names
        assert "quality_check" in node_names
        assert "response_assembly" in node_names
        assert node_names[-1] == "END"
        intent_step = next(step for step in trace["steps"] if step["node"] == "intent_recognition")
        assert intent_step["raw_json"]["output"]["intent_id"] == "data_query"
        tool_step = next(step for step in trace["steps"] if step["node"] == "tool_call")
        assert tool_step["name"] == "工具调用"
        quality_step = next(step for step in trace["steps"] if step["node"] == "quality_check")
        assert quality_step["name"] == "质检合规"
        assert trace["metadata"]["tool_calls_count"] == 1
        assert trace["metadata"]["quality_check_result"] == "PASS"

        raw_response = await client.get(f"/api/traces/{trace_id}/steps/{intent_step['step_id']}/raw")
        assert raw_response.status_code == 200
        raw = raw_response.json()["data"]
        assert raw["trace_id"] == trace_id
        assert raw["step_id"] == intent_step["step_id"]
        assert raw["raw_json"]["node"] == "intent_recognition"
        assert raw["raw_json"]["output"]["intent_id"] == "data_query"

        missing_step_response = await client.get(f"/api/traces/{trace_id}/steps/step_missing/raw")
        assert missing_step_response.status_code == 404
        assert missing_step_response.json() == {"code": 404, "message": "Trace 节点不存在", "data": None}

        missing_trace_response = await client.get("/api/traces/trace_missing")
        assert missing_trace_response.status_code == 404
        assert missing_trace_response.json() == {"code": 404, "message": "Trace 不存在", "data": None}

        delete_response = await client.delete(f"/api/sessions/{session_id}")
        assert delete_response.status_code == 200
        deleted_trace_response = await client.get(f"/api/traces/{trace_id}")
        assert deleted_trace_response.status_code == 404


@pytest.mark.asyncio
async def test_chat_query_returns_ranking_fallback_and_contract_errors(tmp_path: Path) -> None:
    """Fallback chat query returns ranking blocks and documented errors."""
    async with api_client(tmp_path) as client:
        list_response = await client.get("/api/sessions")
        session_id = list_response.json()["data"]["items"][0]["id"]

        chat_response = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "admin", "query": "今天半导体排行怎么样"},
        )
        assert chat_response.status_code == 200
        rich_types = {block["type"] for block in chat_response.json()["data"]["assistant_message"]["rich_blocks"]}
        assert "ranking_table" in rich_types
        assert "citation_list" not in rich_types
        assert "risk_notice" not in rich_types
        assert chat_response.json()["data"]["trace"]["metadata"]["tool_calls_count"] == 1

        empty_response = await client.post(
            "/api/chat/query",
            json={"session_id": session_id, "source": "client", "query": "   "},
        )
        assert empty_response.status_code == 422
        assert empty_response.json() == {"code": 422, "message": "query 不能为空", "data": None}

        missing_response = await client.post(
            "/api/chat/query",
            json={"session_id": "sess_missing", "source": "client", "query": "半导体"},
        )
        assert missing_response.status_code == 404
        assert missing_response.json() == {"code": 404, "message": "会话不存在", "data": None}


@pytest.mark.asyncio
async def test_showcase_sessions_pinned_to_top_without_keyword(tmp_path: Path) -> None:
    async with api_client(tmp_path) as client:
        created = await client.post("/api/sessions", json={"source": "client"})
        assert created.status_code == 200

        list_response = await client.get("/api/sessions", params={"page": 1, "page_size": 20})
        assert list_response.status_code == 200
        items = list_response.json()["data"]["items"]
        assert items[0]["id"] == "sess_20260608_001"
        assert items[1]["id"] == "sess_20260608_002"
        assert items[2]["id"] == "sess_20260608_004"
        assert items[2]["rich_block_types"] == ["sector_heatmap"]


@pytest.mark.asyncio
async def test_session_list_includes_rich_block_types(tmp_path: Path) -> None:
    """Session list exposes rich block types from the latest assistant message."""
    async with api_client(tmp_path) as client:
        list_response = await client.get("/api/sessions", params={"keyword": "测算"})
        assert list_response.status_code == 200
        items = list_response.json()["data"]["items"]
        calc = next(item for item in items if item["id"] == "sess_20260608_002")
        assert calc["rich_block_types"] == ["calculator"]

        heatmap_response = await client.get("/api/sessions", params={"keyword": "热力图"})
        heatmap = heatmap_response.json()["data"]["items"][0]
        assert heatmap["rich_block_types"] == ["sector_heatmap"]


@pytest.mark.asyncio
async def test_client_showcase_sessions_seed_when_db_not_empty(tmp_path: Path) -> None:
    """Showcase sessions with rich blocks are created even if other sessions already exist."""
    async with api_client(tmp_path) as client:
        created = await client.post("/api/sessions", json={"source": "client"})
        assert created.status_code == 200

        list_response = await client.get("/api/sessions", params={"page": 1, "page_size": 50})
        assert list_response.status_code == 200
        titles = {item["title"] for item in list_response.json()["data"]["items"]}
        assert "今天涨幅靠前的半导体股票有哪些" in titles
        assert "15元买入未来预期回报率怎么算" in titles
        assert "帮我看一下今天A股行业板块热力图" in titles

        calc_detail = await client.get("/api/sessions/sess_20260608_002")
        assert calc_detail.status_code == 200
        assistant = calc_detail.json()["data"]["messages"][1]
        rich_types = {block["type"] for block in assistant["rich_blocks"]}
        assert rich_types == {"calculator"}


@pytest.mark.asyncio
async def test_heatmap_demo_session_is_seeded(tmp_path: Path) -> None:
    """Heatmap showcase session is created with sector_heatmap rich block."""
    async with api_client(tmp_path) as client:
        list_response = await client.get("/api/sessions", params={"keyword": "热力图"})
        assert list_response.status_code == 200
        items = list_response.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["id"] == "sess_20260608_004"
        assert items[0]["title"] == "帮我看一下今天A股行业板块热力图"

        detail_response = await client.get("/api/sessions/sess_20260608_004")
        assert detail_response.status_code == 200
        messages = detail_response.json()["data"]["messages"]
        assert len(messages) == 2
        assistant = messages[1]
        assert assistant["role"] == "assistant"
        rich_types = {block["type"] for block in assistant["rich_blocks"]}
        assert rich_types == {"sector_heatmap"}
        heatmap = assistant["rich_blocks"][0]
        assert heatmap["title"] == "行业板块热力图"
        assert len(heatmap["payload"]["tiles"]) >= 10


def test_legacy_agent_fallback_summary_is_not_ui_visible() -> None:
    """Old persisted rich blocks are sanitized before they can reach the UI."""
    legacy_content = "已根据本地模拟数据生成个股基本面信息卡，并附上引用来源和风险提示。"
    legacy_blocks = [
        {
            "id": "block_old_text",
            "type": "text",
            "title": "Agent fallback 回答摘要",
            "payload": {
                "paragraphs": [
                    "问题：宁德时代基本面怎么样",
                    "当前回答由演示级 Agent fallback 链路生成，用于验证路由、工具调用、RAG 命中、质检和富响应闭环。",
                ]
            },
            "sources": [{"type": "knowledge", "label": "本地 fallback 规则", "time": "2026-06-08"}],
            "risk_notice": "以上内容来自本地模拟数据和 fallback 规则，仅用于产品验证，不构成投资建议。真实 LLM 与 LangGraph 流转尚未接入。",
        },
        {
            "id": "block_old_stock",
            "type": "stock_card",
            "title": "个股基本面信息卡",
            "payload": {
                "name": "宁德时代",
                "code": "300750",
                "price": "185.42",
                "change_pct": "+2.18%",
                "tags": ["动力电池", "新能源车", "创业板"],
                "metrics": {
                    "columns": ["指标", "当前值", "报告期", "解读"],
                    "rows": [
                        {"metric": "营业收入", "value": "4009.2亿", "period": "2025年报", "note": "规模保持行业领先"},
                    ],
                },
            },
            "sources": [{"type": "financial", "label": "本地财务模拟数据", "time": "2025年报"}],
            "risk_notice": "以上内容来自本地模拟数据和 fallback 规则，仅用于产品验证，不构成投资建议。",
        },
    ]

    content = sanitize_assistant_content("assistant", legacy_content)
    combined_content = sanitize_assistant_content(
        "assistant",
        "已根据本地模拟数据生成个股基本面信息卡，并附上引用来源和风险提示。\n"
        "Agent fallback 回答摘要\n"
        "当前回答由演示级 Agent fallback 链路生成，用于验证路由、工具调用、RAG 命中、质检和富响应闭环。",
    )
    blocks = sanitize_rich_blocks("assistant", legacy_blocks)
    rendered = str({"content": content, "blocks": blocks})

    assert content == ""
    assert combined_content == ""
    assert blocks == []
    assert "Agent fallback 回答摘要" not in rendered
    assert "当前回答由演示级 Agent fallback 链路生成" not in rendered
    assert "真实 LLM" not in rendered


@pytest.mark.asyncio
async def test_agent_rag_quality_fallback_for_hotspot_data_and_stock_queries(tmp_path: Path) -> None:
    """T-007 fallback chain exposes Agent routing, RAG hits, and quality details."""
    async with api_client(tmp_path) as client:
        cases = [
            ("机器人板块最近有哪些政策催化", "hotspot_agent", "热点归因", "market", set()),
            ("今天半导体涨幅排行怎么样", "data_agent", "行情查询", "market", {"ranking_table"}),
            ("宁德时代基本面怎么样", "stock_agent", "个股分析", "financial", set()),
        ]

        for query, sub_agent, _intent, source_type, expected_blocks in cases:
            create_response = await client.post("/api/sessions", json={"source": "admin"})
            session_id = create_response.json()["data"]["id"]
            chat_response = await client.post(
                "/api/chat/query",
                json={"session_id": session_id, "source": "admin", "query": query},
            )
            assert chat_response.status_code == 200
            chat_data = chat_response.json()["data"]
            rich_types = {block["type"] for block in chat_data["assistant_message"]["rich_blocks"]}
            assert expected_blocks.issubset(rich_types)
            rendered = str(chat_data["assistant_message"])
            assert "不构成投资建议" in rendered
            assert "Agent fallback 回答摘要" not in rendered
            assert "fallback 规则" not in rendered
            assert "真实 LLM" not in rendered
            if sub_agent == "stock_agent":
                assert chat_data["assistant_message"]["rich_blocks"] == []
                assert "宁德" in chat_data["assistant_message"]["content"] or "300750" in chat_data["assistant_message"]["content"]

            trace_id = chat_data["trace"]["id"]
            trace_response = await client.get(f"/api/traces/{trace_id}")
            assert trace_response.status_code == 200
            trace = trace_response.json()["data"]
            node_names = [step["node"] for step in trace["steps"]]
            assert trace["steps"][0]["node"] == "context_preprocess"
            assert "intent_recognition" in node_names
            assert "routing_decision" in node_names
            assert "quality_check" in node_names
            assert "response_assembly" in node_names
            assert node_names[-1] == "END"

            if sub_agent == "hotspot_agent":
                assert "hotspot_agent" in node_names
                assert "rag_retrieval" in node_names
            elif sub_agent == "data_agent":
                assert "data_query_agent" in node_names
                assert "rag_retrieval" not in node_names
            else:
                assert "stock_analysis_agent" in node_names
                assert "rag_retrieval" in node_names

            intent_step = next(step for step in trace["steps"] if step["node"] == "intent_recognition")
            intent_id = intent_step["raw_json"]["output"]["intent_id"]
            if sub_agent == "hotspot_agent":
                assert intent_id == "hotspot_analysis"
            elif sub_agent == "data_agent":
                assert intent_id == "data_query"
            else:
                assert intent_id == "stock_analysis"

            if "rag_retrieval" in node_names:
                rag_step = next(step for step in trace["steps"] if step["node"] == "rag_retrieval")
                rag_hits = rag_step["raw_json"]["output"]["rag_hits"]
                if source_type in {"market", "financial", "report"} and sub_agent != "data_agent":
                    assert rag_hits
                    assert rag_hits[0]["source_type"] == source_type
                    assert rag_hits[0]["title"]
                    assert rag_hits[0]["score"] > 0
                detail_items = rag_step["detail_sections"][0]["items"]
                assert "模式" in {item["label"] for item in detail_items}
                assert "命中数" in {item["label"] for item in detail_items}

            quality_step = next(step for step in trace["steps"] if step["node"] == "quality_check")
            assert quality_step["raw_json"]["node"] == "quality_check"
            quality_payload = quality_step["raw_json"]["output"]["quality_check_payload"]
            assert quality_payload["overall_result"] == "PASS"
            assert quality_payload["risk_tip_present"] is True

            final_step = next(step for step in trace["steps"] if step["node"] == "response_assembly")
            assert final_step["raw_json"]["node"] == "response_assembly"


@pytest.mark.asyncio
async def test_layout_preferences_get_patch_and_persist(tmp_path: Path) -> None:
    """Layout preferences can be read, saved, and read back."""
    async with api_client(tmp_path) as client:
        get_response = await client.get("/api/layout/preferences")
        assert get_response.status_code == 200
        defaults = get_response.json()["data"]
        assert defaults["sidebar_width"] == 230
        assert defaults["trace_panel_width"] == 488

        patch_response = await client.patch(
            "/api/layout/preferences",
            json={"sidebar_width": 336, "trace_panel_width": 520},
        )
        assert patch_response.status_code == 200
        patched = patch_response.json()["data"]
        assert patched["sidebar_width"] == 336
        assert patched["trace_panel_width"] == 520

        persisted_response = await client.get("/api/layout/preferences")
        assert persisted_response.status_code == 200
        persisted = persisted_response.json()["data"]
        assert persisted["sidebar_width"] == 336
        assert persisted["trace_panel_width"] == 520

        invalid_response = await client.patch(
            "/api/layout/preferences",
            json={"sidebar_width": 100, "trace_panel_width": 520},
        )
        assert invalid_response.status_code == 422
        assert invalid_response.json() == {
            "code": 422,
            "message": "sidebar_width 必须在 200 到 420 之间",
            "data": None,
        }


@pytest.mark.asyncio
async def test_layout_preferences_migrate_legacy_sidebar_width(tmp_path: Path) -> None:
    """Legacy persisted sidebar widths are migrated to the new default on read."""
    async with api_client(tmp_path) as client:
        for legacy_width in (288, 420):
            patch_response = await client.patch(
                "/api/layout/preferences",
                json={"sidebar_width": legacy_width, "trace_panel_width": 488},
            )
            assert patch_response.status_code == 200

            get_response = await client.get("/api/layout/preferences")
            assert get_response.status_code == 200
            migrated = get_response.json()["data"]
            assert migrated["sidebar_width"] == 230
