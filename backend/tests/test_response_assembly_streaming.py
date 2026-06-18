"""Tests for response_assembly streaming behavior (no visible draft withdrawal)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.src.agents.nodes.response_assembly import response_assembly
from backend.src.integrations.langgraph.state import AgentState
from backend.src.integrations.llm.client import LLMClientError
from backend.src.services.message_sanitizer import ensure_public_risk_notice
from backend.src.services.rag.models import RagHit
from backend.src.services.system_time import SystemTimeContext


def _rag_hit() -> dict[str, Any]:
    return RagHit(
        chunk_id="c1",
        doc_id="d1",
        title="测试研报",
        snippet="营收 100 亿元",
        source_type="report",
        path="reports/x.md",
        score=0.9,
        time_period="2025A",
        relevance_reason="匹配用户问题",
    ).model_dump()


def _time_ctx() -> SystemTimeContext:
    return SystemTimeContext(
        current_date="2026-06-13",
        timezone="Asia/Shanghai",
        source="test",
    )


_GOOD_DRAFT = (
    "公司营收 100 亿元，利润 20 亿元。[citation:1]\n\n"
    "### 参考来源\n\n"
    "- [citation:1]测试"
)
_BAD_DRAFT = "公司营收 100 亿元，利润 20 亿元。\n\n### 参考来源\n\n- [citation:1]测试"


@pytest.mark.asyncio
async def test_citation_retry_live_streams_revised_draft() -> None:
    """First non-compliant draft is buffered; revision pass streams live to the client."""
    events: list[dict[str, Any]] = []

    def stream_callback(event: dict[str, Any]) -> None:
        events.append(event)

    bad_draft = _BAD_DRAFT
    good_draft = _GOOD_DRAFT
    call_count = 0

    async def _fake_stream(*_args: Any, **_kwargs: Any) -> AsyncIterator[str]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield bad_draft
        else:
            yield good_draft

    stream_mock = MagicMock()
    stream_mock.chat_completion_stream = _fake_stream

    llm = MagicMock()
    llm._output_client.return_value = stream_mock
    llm.enrich_rich_blocks.return_value = []

    state: AgentState = {
        "normalized_query": "测试公司基本面",
        "response_kind": "stock",
        "evidence_pack": {
            "agent_summary": "要点",
            "tool_result": {},
            "retrieved_chunks": [{"snippet": "x"}],
        },
        "rag_hits": [_rag_hit()],
        "stream_callback": stream_callback,
        "trace_steps": [],
    }

    with patch(
        "backend.src.agents.nodes.response_assembly.resolve_system_time",
        return_value=_time_ctx(),
    ), patch(
        "backend.src.agents.nodes.response_assembly.build_citation_catalog",
        return_value=MagicMock(entries=[], to_quality_payload=lambda: {}),
    ), patch(
        "backend.src.agents.nodes.response_assembly.format_citation_context",
        return_value="",
    ), patch(
        "backend.src.agents.nodes.response_assembly.normalize_assembly_citations",
        side_effect=lambda content, _catalog: content,
    ):
        result = await response_assembly(state, llm=llm, rag=MagicMock(), settings=MagicMock())

    event_names = [event["event"] for event in events]
    assert "content_reset" not in event_names
    streamed = "".join(event["data"]["delta"] for event in events if event["event"] == "content_delta")
    assert _BAD_DRAFT not in streamed
    assert ensure_public_risk_notice(good_draft) in streamed
    assert result["final_response"] == ensure_public_risk_notice(good_draft)


@pytest.mark.asyncio
async def test_citation_retry_fallback_buffers_draft_when_revision_fails() -> None:
    """When revision fails, fall back to buffered first draft without content_reset."""
    events: list[dict[str, Any]] = []

    def stream_callback(event: dict[str, Any]) -> None:
        events.append(event)

    bad_draft = _BAD_DRAFT
    call_count = 0

    async def _fake_stream(*_args: Any, **_kwargs: Any) -> AsyncIterator[str]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield bad_draft
            return
        raise LLMClientError("LLM 请求超时")

    stream_mock = MagicMock()
    stream_mock.chat_completion_stream = _fake_stream

    llm = MagicMock()
    llm._output_client.return_value = stream_mock
    llm.enrich_rich_blocks.return_value = []

    state: AgentState = {
        "normalized_query": "测试公司基本面",
        "response_kind": "stock",
        "evidence_pack": {
            "agent_summary": "要点",
            "tool_result": {},
            "retrieved_chunks": [{"snippet": "x"}],
        },
        "rag_hits": [_rag_hit()],
        "stream_callback": stream_callback,
        "trace_steps": [],
    }

    with patch(
        "backend.src.agents.nodes.response_assembly.resolve_system_time",
        return_value=_time_ctx(),
    ), patch(
        "backend.src.agents.nodes.response_assembly.build_citation_catalog",
        return_value=MagicMock(entries=[], to_quality_payload=lambda: {}),
    ), patch(
        "backend.src.agents.nodes.response_assembly.format_citation_context",
        return_value="",
    ), patch(
        "backend.src.agents.nodes.response_assembly.normalize_assembly_citations",
        side_effect=lambda content, _catalog: content,
    ):
        result = await response_assembly(state, llm=llm, rag=MagicMock(), settings=MagicMock())

    assert result["final_response"] == ensure_public_risk_notice(bad_draft)
    assert "content_reset" not in {event["event"] for event in events}
    streamed = "".join(event["data"]["delta"] for event in events if event["event"] == "content_delta")
    assert _BAD_DRAFT in streamed or ensure_public_risk_notice(bad_draft) in streamed
    assert any(event["event"] == "content_done" for event in events)


@pytest.mark.asyncio
async def test_first_pass_compliant_uses_buffered_typewriter() -> None:
    events: list[dict[str, Any]] = []

    def stream_callback(event: dict[str, Any]) -> None:
        events.append(event)

    good_draft = _GOOD_DRAFT

    async def _fake_stream(*_args: Any, **_kwargs: Any) -> AsyncIterator[str]:
        yield good_draft

    stream_mock = MagicMock()
    stream_mock.chat_completion_stream = _fake_stream

    llm = MagicMock()
    llm._output_client.return_value = stream_mock
    llm.enrich_rich_blocks.return_value = []

    state: AgentState = {
        "normalized_query": "测试公司基本面",
        "response_kind": "stock",
        "evidence_pack": {
            "agent_summary": "要点",
            "tool_result": {},
            "retrieved_chunks": [{"snippet": "x"}],
        },
        "rag_hits": [_rag_hit()],
        "stream_callback": stream_callback,
        "trace_steps": [],
    }

    with patch(
        "backend.src.agents.nodes.response_assembly.resolve_system_time",
        return_value=_time_ctx(),
    ), patch(
        "backend.src.agents.nodes.response_assembly.build_citation_catalog",
        return_value=MagicMock(entries=[], to_quality_payload=lambda: {}),
    ), patch(
        "backend.src.agents.nodes.response_assembly.format_citation_context",
        return_value="",
    ), patch(
        "backend.src.agents.nodes.response_assembly.normalize_assembly_citations",
        side_effect=lambda content, _catalog: content,
    ):
        result = await response_assembly(state, llm=llm, rag=MagicMock(), settings=MagicMock())

    delta_events = [event for event in events if event["event"] == "content_delta"]
    assert len(delta_events) >= 1
    assert "".join(event["data"]["delta"] for event in delta_events) == ensure_public_risk_notice(good_draft)
    assert result["final_response"] == ensure_public_risk_notice(good_draft)


@pytest.mark.asyncio
async def test_heatmap_rich_blocks_stream_before_content_delta() -> None:
    events: list[dict[str, Any]] = []

    def stream_callback(event: dict[str, Any]) -> None:
        events.append(event)

    async def _fake_stream(*_args: Any, **_kwargs: Any) -> AsyncIterator[str]:
        yield "半导体板块成交居前，白酒板块涨幅靠前。[citation:1]"

    stream_mock = MagicMock()
    stream_mock.chat_completion_stream = _fake_stream

    heatmap_block = {
        "type": "sector_heatmap",
        "title": "行业板块热力图",
        "payload": {"board_kind": "industry", "trade_date": "2026-06-18", "tiles": [], "size_by": "turnover_amount"},
        "sources": [],
        "risk_notice": "以上内容仅为信息整理，不构成投资建议。",
    }

    llm = MagicMock()
    llm._output_client.return_value = stream_mock
    llm.enrich_rich_blocks.return_value = [heatmap_block]

    state: AgentState = {
        "normalized_query": "帮我看一下今天A股行业板块热力图",
        "response_kind": "data",
        "evidence_pack": {
            "agent_summary": "热力图",
            "tool_result": {
                "sector_heatmap_lookup": {
                    "tiles": [
                        {
                            "board_name": "半导体",
                            "board_code": "BK1036",
                            "pct_change": 2.1,
                            "turnover_amount": 120.0,
                        }
                    ],
                    "source": "东财",
                    "trade_date": "2026-06-18",
                }
            },
        },
        "rag_hits": [],
        "stream_callback": stream_callback,
        "trace_steps": [],
    }

    with patch(
        "backend.src.agents.nodes.response_assembly.resolve_system_time",
        return_value=_time_ctx(),
    ), patch(
        "backend.src.agents.nodes.response_assembly.build_citation_catalog",
        return_value=MagicMock(entries=[], to_quality_payload=lambda: {}),
    ), patch(
        "backend.src.agents.nodes.response_assembly.format_citation_context",
        return_value="",
    ), patch(
        "backend.src.agents.nodes.response_assembly.normalize_assembly_citations",
        side_effect=lambda content, _catalog: content,
    ):
        result = await response_assembly(state, llm=llm, rag=MagicMock(), settings=MagicMock())

    event_names = [event["event"] for event in events]
    assert "rich_blocks" in event_names
    assert "content_delta" in event_names
    assert event_names.index("rich_blocks") < event_names.index("content_delta")
    assert result.get("rich_blocks_streamed") is True
    rich_payload = next(event for event in events if event["event"] == "rich_blocks")["data"]["rich_blocks"]
    assert rich_payload[0]["type"] == "sector_heatmap"
