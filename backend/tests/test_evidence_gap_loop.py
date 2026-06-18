"""Tests for evidence gap loop graph routing."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.integrations.langgraph.graph import GraphDeps, build_graph
from backend.src.integrations.langgraph.routing import (
    route_after_evidence_gap_check,
    route_after_evidence_merge,
)
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.models import RagHit, RagRetrievalResult
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


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


def test_route_after_evidence_merge_only_stock_before_supplement() -> None:
    assert route_after_evidence_merge({"route_target": "stock_analysis_agent"}) == "evidence_gap_check"
    assert route_after_evidence_merge({"route_target": "data_query_agent"}) == "quality_check"
    assert route_after_evidence_merge({"evidence_supplement_done": True}) == "quality_check"
    compound_stock = {
        "multi_agent_mode": True,
        "route_target": "stock_analysis_agent",
        "multi_agent_stock_phase_done": False,
    }
    assert route_after_evidence_merge(compound_stock) == "multi_agent_handoff"


def test_route_after_evidence_gap_check() -> None:
    assert route_after_evidence_gap_check({"should_enrich_evidence": True}) == "gap_planner"
    assert route_after_evidence_gap_check({"should_enrich_evidence": False}) == "quality_check"


@pytest.mark.asyncio
async def test_stock_path_runs_gap_loop_when_company_rag_missing() -> None:
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
            "slots": {"stock_name": "寒武纪", "analysis_dimension": "基本面"},
            "slot_confidence": {"stock_name": 0.95},
            "missing_slots": [],
            "ambiguous_slots": [],
        },
        {
            "agent_result": "从基本面与盈利质量分析寒武纪。",
            "analysis_dimensions": ["基本面", "盈利能力"],
            "tool_params": {"stock_name": "寒武纪"},
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
                "寒武纪仍处于投入期，短期盈利承压。以上内容仅为信息整理，不构成投资建议。"
            ),
        },
    )()
    initial_hit = RagHit(
        doc_id="industry_ai",
        title="AI芯片行业研报",
        source_type="report",
        path="industry-reports/ai.md",
        score=0.7,
        snippet="行业景气度较高。",
        relevance_reason="行业",
        chunk_id="chunk_industry",
    )
    supplement_hit = RagHit(
        doc_id="report_hanwuji",
        title="寒武纪公司研报",
        source_type="report",
        path="company-reports/688256.md",
        score=0.91,
        snippet="寒武纪研发投入高，短期利润承压。",
        relevance_reason="公司名命中",
        chunk_id="chunk_company",
    )

    async def _retrieve_side_effect(query: str, *, top_k: int = 6) -> RagRetrievalResult:
        return RagRetrievalResult(hits=[initial_hit], query=query, mode="hybrid")

    async def _retrieve_targeted_side_effect(
        queries: list[str],
        *,
        top_k: int = 4,
        filters: dict[str, str] | None = None,
        entity_name: str = "",
    ) -> RagRetrievalResult:
        _ = (queries, top_k, filters, entity_name)
        return RagRetrievalResult(hits=[supplement_hit], query=" | ".join(queries), mode="hybrid")

    with (
        patch.object(LLMService, "_intent_client", return_value=mock_intent_client),
        patch.object(LLMService, "_output_client", return_value=mock_output_client),
        patch.object(RagService, "retrieve", new_callable=AsyncMock) as mock_retrieve,
        patch.object(RagService, "retrieve_targeted", new_callable=AsyncMock) as mock_targeted,
    ):
        mock_retrieve.side_effect = _retrieve_side_effect
        mock_targeted.side_effect = _retrieve_targeted_side_effect
        result = await graph.ainvoke(
            {
                "user_query": "帮我看一下寒武纪基本面怎么样？",
                "session_id": "session_gap_loop",
                "chat_history": [],
                "trace_steps": [],
            }
        )

    node_names = [step["node"] for step in result.get("trace_steps", [])]
    assert "evidence_gap_check" in node_names
    assert "gap_planner" in node_names
    assert node_names.count("rag_retrieval") >= 2
    assert node_names.count("evidence_merge") >= 2
    mock_targeted.assert_awaited()
    assert result.get("final_response")
