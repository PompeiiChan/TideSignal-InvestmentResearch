"""Tests for response_assembly multi-turn context injection."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.src.agents.nodes.response_assembly import response_assembly
from backend.src.integrations.langgraph.state import AgentState
from backend.src.services.system_time import SystemTimeContext


def _time_ctx() -> SystemTimeContext:
    return SystemTimeContext(
        current_date="2026-06-19",
        timezone="Asia/Shanghai",
        source="test",
    )


@pytest.mark.asyncio
async def test_response_assembly_injects_multiturn_block() -> None:
    captured_prompts: list[str] = []

    async def _fake_stream(_messages: Any, **_kwargs: Any) -> AsyncIterator[str]:
        captured_prompts.append(str(_messages[-1]["content"]))
        yield "宁德时代 2026Q1 一季报解读。[citation:1]\n\n### 参考来源\n\n- 测试"

    stream_mock = MagicMock()
    stream_mock.chat_completion_stream = _fake_stream

    llm = MagicMock()
    llm._assembly_client.return_value = stream_mock
    llm.enrich_rich_blocks.return_value = []

    state: AgentState = {
        "normalized_query": "一季报呢",
        "response_kind": "stock",
        "history_summary": "user: 宁德时代基本面怎么样\nassistant: 营收稳健…",
        "active_slots": {
            "stock_name": "宁德时代",
            "stock_code": "300750.SZ",
            "time_range": "2026Q1",
        },
        "inherited_slot_keys": ["stock_name", "stock_code"],
        "evidence_pack": {
            "agent_summary": "要点",
            "tool_result": {},
            "retrieved_chunks": [{"snippet": "x"}],
        },
        "rag_hits": [],
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
    ), patch(
        "backend.src.agents.nodes.response_assembly.evidence_requires_citations",
        return_value=False,
    ):
        result = await response_assembly(state, llm=llm, rag=MagicMock(), settings=MagicMock())

    assert captured_prompts
    user_prompt = captured_prompts[0]
    assert "【多轮对话上下文】" in user_prompt
    assert "宁德时代" in user_prompt
    assert "不得要求用户重复提供公司名称" in user_prompt
    trace_input = result["trace_steps"][-1]["raw_json"]["input"]
    assert trace_input["history_summary"].startswith("user: 宁德时代")
    assert trace_input["active_slots"]["stock_name"] == "宁德时代"
    assert trace_input["conversation_context"]["has_context"] is True


@pytest.mark.asyncio
async def test_response_assembly_skips_multiturn_block_without_history() -> None:
    captured_prompts: list[str] = []

    async def _fake_stream(_messages: Any, **_kwargs: Any) -> AsyncIterator[str]:
        captured_prompts.append(str(_messages[-1]["content"]))
        yield "单轮回答。\n\n### 参考来源\n\n- 测试"

    stream_mock = MagicMock()
    stream_mock.chat_completion_stream = _fake_stream

    llm = MagicMock()
    llm._assembly_client.return_value = stream_mock
    llm.enrich_rich_blocks.return_value = []

    state: AgentState = {
        "normalized_query": "宁德时代基本面怎么样",
        "response_kind": "stock",
        "history_summary": "",
        "active_slots": {"stock_name": "宁德时代"},
        "evidence_pack": {"agent_summary": "要点", "tool_result": {}},
        "rag_hits": [],
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
    ), patch(
        "backend.src.agents.nodes.response_assembly.evidence_requires_citations",
        return_value=False,
    ):
        await response_assembly(state, llm=llm, rag=MagicMock(), settings=MagicMock())

    user_prompt = captured_prompts[0]
    assert "【多轮对话上下文】" not in user_prompt
