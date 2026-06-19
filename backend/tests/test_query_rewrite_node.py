"""Tests for query_rewrite LangGraph node (T-014)."""

from __future__ import annotations

import pytest

from backend.src.agents.nodes.query_rewrite import query_rewrite
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


def _deps() -> tuple[LLMService, RagService, AppSettings]:
    return LLMService(AppSettings()), RagService(), AppSettings()


@pytest.mark.asyncio
async def test_query_rewrite_node_outputs_retrieval_query() -> None:
    llm, rag, settings = _deps()
    state = {
        "normalized_query": "它一季报怎么样",
        "intent_id": "stock_analysis",
        "slots": {"stock_name": "宁德时代"},
        "active_slots": {"stock_name": "宁德时代"},
        "trace_steps": [],
    }
    result = await query_rewrite(state, llm=llm, rag=rag, settings=settings)
    assert "宁德时代" in result["retrieval_query"]
    assert "一季报" in result["retrieval_query"]
    assert result["retrieval_query_changed"] is True
    assert result["rewrite_method"] in {"rule_slots", "rule_multiturn"}
    assert result["current_node"] == "query_rewrite"
    trace = result["trace_steps"][-1]
    assert trace["node"] == "query_rewrite"
    assert trace["raw_json"]["input"]["normalized_query"] == "它一季报怎么样"
    assert trace["raw_json"]["output"]["retrieval_query"] == result["retrieval_query"]


@pytest.mark.asyncio
async def test_query_rewrite_node_passthrough_for_rich_query() -> None:
    llm, rag, settings = _deps()
    query = "罗莱生活 2026 年一季报"
    state = {
        "normalized_query": query,
        "intent_id": "stock_analysis",
        "slots": {"stock_name": "罗莱生活"},
        "trace_steps": [],
    }
    result = await query_rewrite(state, llm=llm, rag=rag, settings=settings)
    assert result["retrieval_query"] == query
    assert result["retrieval_query_changed"] is False
    assert result["rewrite_method"] == "passthrough"
