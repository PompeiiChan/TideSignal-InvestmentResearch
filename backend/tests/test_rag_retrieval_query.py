"""Tests for rag_retrieval using retrieval_query (T-014)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.src.agents.nodes.rag_retrieval import rag_retrieval
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.models import RagRetrievalResult
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


def _deps() -> tuple[LLMService, RagService, AppSettings]:
    return LLMService(AppSettings()), RagService(), AppSettings()


@pytest.mark.asyncio
async def test_rag_retrieval_uses_retrieval_query_for_main_path() -> None:
    llm, rag, settings = _deps()
    state = {
        "normalized_query": "一季报呢",
        "retrieval_query": "宁德时代 一季报 财报",
        "retrieval_query_changed": True,
        "rewrite_method": "rule_multiturn",
        "execution_plan": {"needs_rag": True, "retrieval_config": {"top_k": 4}},
        "route_target": "stock_analysis_agent",
        "slots": {"stock_name": "宁德时代"},
        "trace_steps": [],
    }
    with patch.object(RagService, "retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = RagRetrievalResult(
            query="宁德时代 一季报 财报",
            mode="bm25",
            embedding_connected=False,
        )
        result = await rag_retrieval(state, llm=llm, rag=rag, settings=settings)
    mock_retrieve.assert_awaited_once()
    assert mock_retrieve.await_args.args[0] == "宁德时代 一季报 财报"
    trace_input = result["trace_steps"][-1]["raw_json"]["input"]
    assert trace_input["normalized_query"] == "一季报呢"
    assert trace_input["retrieval_query"] == "宁德时代 一季报 财报"
    assert trace_input["query"] == "宁德时代 一季报 财报"
    assert trace_input["retrieval_query_changed"] is True


@pytest.mark.asyncio
async def test_rag_retrieval_uses_retrieval_queries_for_dimension_split() -> None:
    llm, rag, settings = _deps()
    extra_queries = [
        "海天味业 财务 营收 利润 现金流 年报",
        "海天味业 盈利能力 ROE 毛利率",
        "海天味业 公司研报 竞争力 行业",
    ]
    state = {
        "normalized_query": "海天味业基本面",
        "retrieval_query": "海天味业基本面",
        "retrieval_queries": extra_queries,
        "retrieval_query_changed": True,
        "rewrite_method": "rule_dimension_split",
        "execution_plan": {"needs_rag": True, "retrieval_config": {"top_k": 4}},
        "route_target": "stock_analysis_agent",
        "slots": {"stock_name": "海天味业"},
        "trace_steps": [],
    }
    with patch.object(RagService, "retrieve_targeted", new_callable=AsyncMock) as mock_targeted:
        mock_targeted.return_value = RagRetrievalResult(
            query=" | ".join(extra_queries),
            mode="hybrid",
            embedding_connected=False,
        )
        result = await rag_retrieval(state, llm=llm, rag=rag, settings=settings)
    mock_targeted.assert_awaited_once()
    assert mock_targeted.await_args.args[0] == extra_queries
    trace_input = result["trace_steps"][-1]["raw_json"]["input"]
    assert trace_input["retrieval_queries"] == extra_queries
    assert trace_input["retrieval_query"] == "海天味业基本面"


@pytest.mark.asyncio
async def test_rag_retrieval_supplement_mode_ignores_retrieval_query() -> None:
    llm, rag, settings = _deps()
    state = {
        "normalized_query": "一季报呢",
        "retrieval_query": "宁德时代 一季报 财报",
        "supplement_mode": True,
        "supplement_rag_queries": ["宁德时代 2026年一季报 营收"],
        "supplement_rag_filters": {},
        "execution_plan": {"retrieval_config": {"top_k": 4}},
        "slots": {"stock_name": "宁德时代"},
        "trace_steps": [],
    }
    with patch.object(RagService, "retrieve_targeted", new_callable=AsyncMock) as mock_targeted:
        mock_targeted.return_value = RagRetrievalResult(query="宁德时代 2026年一季报 营收", mode="hybrid")
        await rag_retrieval(state, llm=llm, rag=rag, settings=settings)
    mock_targeted.assert_awaited_once()
    assert mock_targeted.await_args.args[0] == ["宁德时代 2026年一季报 营收"]
