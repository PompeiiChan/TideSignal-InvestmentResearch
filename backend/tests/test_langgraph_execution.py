"""Tests for LangGraph Phase 3 execution chain."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.agents.nodes.tool_call import tool_call
from backend.src.agents.tools import TOOL_REGISTRY
from backend.src.agents.tools.return_calculator import compute_return
from backend.src.integrations.langgraph.graph import GraphDeps, build_graph
from backend.src.integrations.langgraph.runner import LangGraphRunner
from backend.src.integrations.langgraph.state import AgentState
from backend.src.integrations.llm.models import LLMCallMeta, QualityCheckResult
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.models import RagHit, RagRetrievalResult, RerankCandidateSnapshot
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


def _llm_deps() -> tuple[LLMService, RagService, AppSettings]:
    return LLMService(AppSettings()), RagService(), AppSettings()


def _mock_llm_json_responses(responses: list[dict[str, Any]]) -> Any:
    queue = list(responses)

    async def _chat_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        payload = queue.pop(0)
        return {
            "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
            "usage": {},
        }

    return _chat_completion


def _mock_stream_deltas(text: str) -> Any:
    async def _chat_completion_stream(*_args: Any, **_kwargs: Any) -> AsyncIterator[str]:
        yield text

    return _chat_completion_stream


def _sample_rag_result(query: str = "测试") -> RagRetrievalResult:
    hit = RagHit(
        doc_id="rag_stock_000568",
        title="泸州老窖财务摘要",
        source_type="financial",
        path="data/knowledge-base/financials/000568.md",
        score=0.86,
        snippet="营收与净利润保持增长。",
        relevance_reason="命中个股名称",
        chunk_id="chunk_001",
        time_period="2025A",
    )
    return RagRetrievalResult(
        hits=[hit],
        latency_ms=120,
        embedding_connected=True,
        rerank_connected=True,
        rerank_before=[
            RerankCandidateSnapshot(chunk_id="chunk_001", title=hit.title, score=0.82),
            RerankCandidateSnapshot(chunk_id="chunk_002", title="其他文档", score=0.75),
        ],
        rerank_after=[
            RerankCandidateSnapshot(chunk_id="chunk_001", title=hit.title, score=0.91),
        ],
        index_chunk_count=100,
        query=query,
        model="mock-embedding",
        mode="hybrid",
    )


@pytest.mark.parametrize(
    "tool_name",
    [
        "market_ranking_lookup",
        "mock_market_ranking_lookup",
        "mock_financial_profile_lookup",
        "valuation_profile_lookup",
        "hotspot_signal_lookup",
        "hotspot_fact_lookup",
        "mock_hotspot_material_lookup",
        "local_return_calculator",
    ],
)
def test_tool_registry_dispatch(tool_name: str) -> None:
    assert tool_name in TOOL_REGISTRY


def test_return_calculator_snapshot() -> None:
    result = compute_return(buy_price=10.0, sell_price=12.0, share_count=1000, fee_rate=0.0003)
    assert result["net_profit"] == pytest.approx(1993.4, rel=1e-3)
    assert result["return_pct"] == pytest.approx(20.0, rel=1e-3)


@pytest.mark.asyncio
async def test_tool_call_node_invokes_mock_tools() -> None:
    llm, rag, settings = _llm_deps()
    state: AgentState = {
        "execution_plan": {"tool_names": ["mock_market_ranking_lookup"]},
        "tool_params": {"industry": "半导体", "metric": "涨幅排行"},
        "trace_steps": [],
    }
    result = await tool_call(state, llm=llm, rag=rag, settings=settings)
    assert result["tool_status"] == "success"
    assert "mock_market_ranking_lookup" in result["tool_result"]
    assert result["trace_steps"][0]["node"] == "tool_call"


@pytest.mark.asyncio
async def test_stock_path_trace_contains_rag_and_tool() -> None:
    deps = GraphDeps(llm=LLMService(AppSettings()), rag=RagService(), settings=AppSettings())
    graph = build_graph(deps)
    mock_responses: list[dict[str, Any]] = [
        {
            "intent_id": "stock_analysis",
            "intent_name": "个股分析",
            "intent_confidence": 0.92,
            "candidate_intents": [{"intent_id": "stock_analysis", "confidence": 0.92}],
            "missing_slots": [],
        },
        {
            "slots": {"stock_name": "泸州老窖", "analysis_dimension": "基本面"},
            "slot_confidence": {"stock_name": 0.95},
            "missing_slots": [],
            "ambiguous_slots": [],
        },
        {
            "agent_result": "从基本面、盈利能力和估值三个维度分析泸州老窖。",
            "analysis_dimensions": ["基本面", "盈利能力"],
            "tool_params": {"stock_name": "泸州老窖"},
        },
        {
            "overall_result": "PASS",
            "compliance_scan": {"summary": "通过"},
            "citation_check": {"summary": "通过", "citation_count": 1},
            "data_consistency": {"summary": "一致"},
            "format_check": {"summary": "完整"},
            "risk_tip_present": True,
            "blacklist_expressions_found": [],
        },
    ]
    mock_intent_client = type(
        "MockIntentClient",
        (),
        {
            "chat_completion": _mock_llm_json_responses(mock_responses),
            "extract_message_content": staticmethod(
                lambda body: body["choices"][0]["message"]["content"]
            ),
        },
    )()
    mock_output_client = type(
        "MockOutputClient",
        (),
        {
            "chat_completion_stream": _mock_stream_deltas(
                "泸州老窖基本面稳健，2025A 营收与净利润保持增长。以上内容仅为信息整理，不构成投资建议。"
            ),
        },
    )()

    with (
        patch.object(LLMService, "_intent_client", return_value=mock_intent_client),
        patch.object(LLMService, "_output_client", return_value=mock_output_client),
        patch.object(RagService, "retrieve", new_callable=AsyncMock) as mock_retrieve,
    ):
        mock_retrieve.return_value = _sample_rag_result("泸州老窖基本面")
        result = await graph.ainvoke(
            {
                "user_query": "帮我看一下泸州老窖基本面怎么样？",
                "session_id": "session_stock_exec",
                "chat_history": [],
                "trace_steps": [],
            }
        )

    node_names = [step["node"] for step in result.get("trace_steps", [])]
    assert "stock_analysis_agent" in node_names
    assert "rag_retrieval" in node_names
    assert "tool_call" in node_names
    assert "evidence_merge" in node_names
    assert "quality_check" in node_names
    assert "response_assembly" in node_names
    rag_step = next(step for step in result["trace_steps"] if step["node"] == "rag_retrieval")
    assert "rerank_before" in rag_step["output"]
    assert result.get("final_response")


@pytest.mark.asyncio
async def test_data_query_path_completes() -> None:
    deps = GraphDeps(llm=LLMService(AppSettings()), rag=RagService(), settings=AppSettings())
    graph = build_graph(deps)
    mock_responses: list[dict[str, Any]] = [
        {
            "intent_id": "data_query",
            "intent_confidence": 0.9,
            "candidate_intents": [{"intent_id": "data_query", "confidence": 0.9}],
            "missing_slots": [],
        },
        {
            "slots": {"metric": "涨幅排行", "industry": "半导体"},
            "slot_confidence": {},
            "missing_slots": [],
            "ambiguous_slots": [],
        },
        {
            "agent_result": "查询半导体板块涨幅排行。",
            "data_table": [{"field": "pct_change", "description": "涨跌幅"}],
            "data_source": "mock",
            "tool_params": {"industry": "半导体", "metric": "涨幅排行"},
        },
        {
            "overall_result": "PASS",
            "compliance_scan": {"summary": "通过"},
            "citation_check": {"summary": "通过"},
            "data_consistency": {"summary": "一致"},
            "format_check": {"summary": "完整"},
            "risk_tip_present": True,
            "blacklist_expressions_found": [],
        },
    ]
    with (
        patch.object(
            LLMService,
            "_intent_client",
            return_value=type(
                "C",
                (),
                {
                    "chat_completion": _mock_llm_json_responses(mock_responses),
                    "extract_message_content": staticmethod(
                        lambda b: b["choices"][0]["message"]["content"]
                    ),
                },
            )(),
        ),
        patch.object(
            LLMService,
            "_output_client",
            return_value=type(
                "O",
                (),
                {"chat_completion_stream": _mock_stream_deltas("半导体板块涨幅排行整理如下。")},
            )(),
        ),
    ):
        result = await graph.ainvoke(
            {
                "user_query": "半导体板块今天涨幅排行？",
                "session_id": "session_data",
                "chat_history": [],
                "trace_steps": [],
            }
        )
    node_names = [step["node"] for step in result["trace_steps"]]
    assert "data_query_agent" in node_names
    assert "tool_call" in node_names
    assert "rag_retrieval" not in node_names
    assert "response_assembly" in node_names


@pytest.mark.asyncio
async def test_hotspot_path_completes() -> None:
    deps = GraphDeps(llm=LLMService(AppSettings()), rag=RagService(), settings=AppSettings())
    graph = build_graph(deps)
    mock_responses: list[dict[str, Any]] = [
        {
            "intent_id": "hotspot_analysis",
            "intent_confidence": 0.88,
            "candidate_intents": [{"intent_id": "hotspot_analysis", "confidence": 0.88}],
            "missing_slots": [],
        },
        {
            "slots": {"topic": "机器人", "industry": "机器人"},
            "slot_confidence": {},
            "missing_slots": [],
            "ambiguous_slots": [],
        },
        {
            "agent_result": "机器人板块受政策与订单催化。",
            "evidence_list": [{"title": "机器人", "summary": "政策催化"}],
            "tool_params": {"topic": "机器人"},
        },
        {
            "overall_result": "PASS",
            "compliance_scan": {"summary": "通过"},
            "citation_check": {"summary": "通过"},
            "data_consistency": {"summary": "一致"},
            "format_check": {"summary": "完整"},
            "risk_tip_present": True,
            "blacklist_expressions_found": [],
        },
    ]
    with (
        patch.object(
            LLMService,
            "_intent_client",
            return_value=type(
                "C",
                (),
                {
                    "chat_completion": _mock_llm_json_responses(mock_responses),
                    "extract_message_content": staticmethod(
                        lambda b: b["choices"][0]["message"]["content"]
                    ),
                },
            )(),
        ),
        patch.object(
            LLMService,
            "_output_client",
            return_value=type(
                "O",
                (),
                {"chat_completion_stream": _mock_stream_deltas("机器人热点解读正文。")},
            )(),
        ),
        patch.object(RagService, "retrieve", new_callable=AsyncMock) as mock_retrieve,
    ):
        mock_retrieve.return_value = _sample_rag_result("机器人热点")
        result = await graph.ainvoke(
            {
                "user_query": "机器人板块最近有什么催化？",
                "session_id": "session_hotspot",
                "chat_history": [],
                "trace_steps": [],
            }
        )
    node_names = [step["node"] for step in result["trace_steps"]]
    assert "hotspot_agent" in node_names
    assert "rag_retrieval" in node_names
    assert "tool_call" in node_names
    assert "response_assembly" in node_names


@pytest.mark.asyncio
async def test_prediction_request_routes_to_fallback_without_calc_numbers() -> None:
    deps = GraphDeps(llm=LLMService(AppSettings()), rag=RagService(), settings=AppSettings())
    graph = build_graph(deps)
    mock_responses: list[dict[str, Any]] = [
        {
            "intent_id": "prediction_request",
            "intent_confidence": 0.9,
            "candidate_intents": [{"intent_id": "prediction_request", "confidence": 0.9}],
            "missing_slots": [],
        },
        {"slots": {}, "slot_confidence": {}, "missing_slots": [], "ambiguous_slots": []},
    ]
    with patch.object(
        LLMService,
        "_intent_client",
        return_value=type(
            "C",
            (),
            {
                "chat_completion": _mock_llm_json_responses(mock_responses),
                "extract_message_content": staticmethod(
                    lambda b: b["choices"][0]["message"]["content"]
                ),
            },
        )(),
    ):
        result = await graph.ainvoke(
            {
                "user_query": "预测明天泸州老窖会涨到多少目标价？",
                "session_id": "session_prediction",
                "chat_history": [],
                "trace_steps": [],
            }
        )
    node_names = [step["node"] for step in result["trace_steps"]]
    assert "fallback_response" in node_names
    assert "tool_call" not in node_names
    assert "response_assembly" not in node_names
    response = result.get("final_response", "")
    assert "目标价" in response or "预测" in response
    assert not re.search(r"目标价[：:]\s*\d+", response)
    assert not re.search(r"涨到\s*\d+", response)


@pytest.mark.asyncio
async def test_quality_reject_routes_to_fallback() -> None:
    deps = GraphDeps(llm=LLMService(AppSettings()), rag=RagService(), settings=AppSettings())
    graph = build_graph(deps)
    mock_responses: list[dict[str, Any]] = [
        {
            "intent_id": "data_query",
            "intent_confidence": 0.9,
            "candidate_intents": [{"intent_id": "data_query", "confidence": 0.9}],
            "missing_slots": [],
        },
        {
            "slots": {"metric": "涨幅排行"},
            "slot_confidence": {},
            "missing_slots": [],
            "ambiguous_slots": [],
        },
        {
            "agent_result": "查询涨幅排行",
            "tool_params": {"metric": "涨幅排行"},
        },
    ]
    fail_quality = QualityCheckResult(
        overall_result="FAIL",
        compliance_scan={"summary": "命中黑名单"},
        citation_check={"summary": "不足"},
        data_consistency={"summary": "不一致"},
        format_check={"summary": "缺失"},
        risk_tip_present=False,
        blacklist_expressions_found=["建议买入"],
        meta=LLMCallMeta(
            model="mock",
            latency_ms=1,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            finish_reason="stop",
            raw_json={},
        ),
    )
    with (
        patch.object(
            LLMService,
            "_intent_client",
            return_value=type(
                "C",
                (),
                {
                    "chat_completion": _mock_llm_json_responses(mock_responses),
                    "extract_message_content": staticmethod(
                        lambda b: b["choices"][0]["message"]["content"]
                    ),
                },
            )(),
        ),
        patch.object(LLMService, "quality_check", new_callable=AsyncMock) as mock_qc,
    ):
        mock_qc.return_value = fail_quality
        result = await graph.ainvoke(
            {
                "user_query": "建议买入的半导体涨幅排行",
                "session_id": "session_qc_reject",
                "chat_history": [],
                "trace_steps": [],
            }
        )
    node_names = [step["node"] for step in result["trace_steps"]]
    assert "quality_check" in node_names
    assert "fallback_response" in node_names
    assert "response_assembly" not in node_names
    assert result.get("quality_status") == "reject"


@pytest.mark.asyncio
async def test_runner_appends_end_trace_step() -> None:
    runner = LangGraphRunner(
        llm=LLMService(AppSettings()),
        rag=RagService(),
        db=AsyncMock(),
        settings=AppSettings(),
    )

    class _FakeGraph:
        async def ainvoke(self, state: AgentState) -> AgentState:
            return {
                **state,
                "final_response": "测试回答",
                "trace_id": "trace_end_test",
                "trace_steps": [{"node": "context_preprocess", "step_index": 1}],
            }

    runner._graph = _FakeGraph()
    result = await runner.ainvoke(user_query="测试", session_id="sess_end")
    end_steps = [step for step in result["trace_steps"] if step["node"] == "END"]
    assert end_steps
    assert end_steps[0]["output"]["trace_id"] == "trace_end_test"
