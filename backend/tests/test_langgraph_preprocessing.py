"""Tests for LangGraph preprocessing chain (Phase 2)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.agents.nodes.clarification_check import clarification_check
from backend.src.agents.nodes.routing_decision import (
    build_execution_plan,
    resolve_route_target,
    routing_decision,
)
from backend.src.integrations.langgraph.graph import GraphDeps, build_graph
from backend.src.integrations.langgraph.routing import route_after_clarification
from backend.src.integrations.langgraph.runner import LangGraphRunner
from backend.src.integrations.langgraph.state import AgentState
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


def _llm_deps() -> tuple[LLMService, RagService, AppSettings]:
    return LLMService(AppSettings()), RagService(), AppSettings()


@pytest.mark.parametrize(
    ("state", "expected_route"),
    [
        ({"need_clarification": True}, "clarification_response"),
        ({"need_clarification": False}, "query_rewrite"),
        ({}, "query_rewrite"),
    ],
)
def test_route_after_clarification_branches(state: AgentState, expected_route: str) -> None:
    assert route_after_clarification(state) == expected_route


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "need_clarification", "reason_fragment"),
    [
        (
            {
                "intent_id": "stock_analysis",
                "intent_confidence": 0.65,
                "slots": {"stock_name": "泸州老窖"},
                "missing_slots": [],
                "ambiguous_slots": [],
            },
            True,
            "置信度",
        ),
        (
            {
                "intent_id": "stock_analysis",
                "intent_confidence": 0.9,
                "slots": {},
                "missing_slots": [],
                "ambiguous_slots": [],
            },
            True,
            "stock_name",
        ),
        (
            {
                "intent_id": "data_query",
                "intent_confidence": 0.9,
                "normalized_query": "今天涨幅前10的行业板块",
                "slots": {
                    "metric": "涨幅排行",
                    "time_range": "近一交易日",
                    "market": "A股",
                },
                "missing_slots": [],
                "ambiguous_slots": [],
            },
            False,
            "进入路由",
        ),
        (
            {
                "intent_id": "data_query",
                "intent_confidence": 0.9,
                "normalized_query": "帮我查一下数据",
                "slots": {},
                "missing_slots": ["metric"],
                "ambiguous_slots": [],
            },
            True,
            "metric",
        ),
        (
            {
                "intent_id": "data_query",
                "intent_confidence": 0.9,
                "slots": {"industry": "白酒"},
                "missing_slots": [],
                "ambiguous_slots": [],
            },
            True,
            "metric",
        ),
        (
            {
                "intent_id": "stock_analysis",
                "intent_confidence": 0.9,
                "slots": {"stock_name": "茅台"},
                "missing_slots": [],
                "ambiguous_slots": ["stock_name"],
            },
            True,
            "歧义",
        ),
        (
            {
                "intent_id": "data_query",
                "intent_confidence": 0.9,
                "slots": {"metric": "涨幅排行", "industry": "机器人"},
                "missing_slots": ["time_range"],
                "ambiguous_slots": [],
            },
            False,
            "近一交易日",
        ),
        (
            {
                "intent_id": "stock_analysis",
                "intent_confidence": 0.92,
                "normalized_query": "海天味业基本面怎么样",
                "slots": {"stock_name": "海天味业", "analysis_dimension": "基本面"},
                "missing_slots": ["stock_code"],
                "ambiguous_slots": ["stock_code"],
            },
            False,
            "进入路由",
        ),
        (
            {
                "intent_id": "stock_analysis",
                "intent_confidence": 0.92,
                "normalized_query": "茅台怎么样",
                "slots": {"stock_name": "茅台"},
                "missing_slots": [],
                "ambiguous_slots": ["stock_name"],
            },
            True,
            "歧义",
        ),
        (
            {
                "intent_id": "document_qa",
                "intent_confidence": 0.95,
                "normalized_query": "海天味业2025年年度报告营业收入是多少",
                "slots": {},
                "missing_slots": [],
                "ambiguous_slots": [],
            },
            False,
            "进入路由",
        ),
        (
            {
                "intent_id": "document_qa",
                "intent_confidence": 0.95,
                "normalized_query": "请查询海天味业2025年年度报告中的营业收入数据",
                "slots": {
                    "stock_name": "海天味业",
                    "time_range": "2025A",
                    "metric": "营业收入",
                },
                "missing_slots": ["document_id"],
                "ambiguous_slots": [],
            },
            False,
            "进入路由",
        ),
    ],
)
async def test_clarification_check_rule_branches(
    state: AgentState,
    need_clarification: bool,
    reason_fragment: str,
) -> None:
    llm, rag, settings = _llm_deps()
    result = await clarification_check(state, llm=llm, rag=rag, settings=settings)
    assert result["need_clarification"] is need_clarification
    assert reason_fragment in result["clarification_reason"]
    assert result["current_node"] == "clarification_check"
    assert result["trace_steps"]


@pytest.mark.parametrize(
    ("intent_id", "route_target"),
    [
        ("hotspot_analysis", "hotspot_agent"),
        ("data_query", "data_query_agent"),
        ("stock_analysis", "stock_analysis_agent"),
        ("document_qa", "document_qa_agent"),
        ("prediction_request", "fallback_response"),
        ("chit_chat", "fallback_response"),
        ("unknown", "fallback_response"),
    ],
)
def test_routing_decision_intent_mapping(intent_id: str, route_target: str) -> None:
    assert resolve_route_target(intent_id) == route_target


@pytest.mark.parametrize(
    ("route_target", "needs_rag", "needs_tool"),
    [
        ("hotspot_agent", True, True),
        ("data_query_agent", False, True),
        ("stock_analysis_agent", True, True),
        ("document_qa_agent", True, False),
        ("fallback_response", False, False),
    ],
)
def test_execution_plan_defaults(route_target: str, needs_rag: bool, needs_tool: bool) -> None:
    plan = build_execution_plan(route_target)
    assert plan["needs_rag"] is needs_rag
    assert plan["needs_tool"] is needs_tool


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("intent_id", "route_target"),
    [
        ("hotspot_analysis", "hotspot_agent"),
        ("data_query", "data_query_agent"),
        ("stock_analysis", "stock_analysis_agent"),
        ("document_qa", "document_qa_agent"),
        ("prediction_request", "fallback_response"),
        ("chit_chat", "fallback_response"),
    ],
)
async def test_routing_decision_node_outputs(intent_id: str, route_target: str) -> None:
    llm, rag, settings = _llm_deps()
    result = await routing_decision(
        {
            "intent_id": intent_id,
            "slots": {"metric": "涨幅"},
            "context_pack": {},
            "risk_hint": "",
        },
        llm=llm,
        rag=rag,
        settings=settings,
    )
    assert result["route_target"] == route_target
    assert result["execution_plan"]
    assert result["trace_steps"][0]["node"] == "routing_decision"


def _mock_llm_json_responses(responses: list[dict[str, Any]]) -> Any:
    queue = list(responses)

    async def _chat_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        payload = queue.pop(0)
        return {
            "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
            "usage": {},
        }

    return _chat_completion


@pytest.mark.asyncio
async def test_routing_decision_kb_document_query_routes_to_stock_analysis() -> None:
    llm, rag, settings = _llm_deps()
    result = await routing_decision(
        {
            "intent_id": "document_qa",
            "normalized_query": "请查询海天味业2025年年度报告中的营业收入数据",
            "slots": {
                "stock_name": "海天味业",
                "time_range": "2025A",
                "metric": "营业收入",
            },
            "context_pack": {},
            "risk_hint": "",
        },
        llm=llm,
        rag=rag,
        settings=settings,
    )
    assert result["route_target"] == "stock_analysis_agent"
    assert result["slots"].get("stock_code")


@pytest.mark.asyncio
async def test_graph_clarification_path_ends_with_clarification_response() -> None:
    deps = GraphDeps(
        llm=LLMService(AppSettings()),
        rag=RagService(),
        settings=AppSettings(),
    )
    graph = build_graph(deps)
    mock_responses: list[dict[str, Any]] = [
        {
            "intent_id": "unknown",
            "intent_name": "无法识别",
            "intent_confidence": 0.4,
            "candidate_intents": [{"intent_id": "unknown", "confidence": 0.4}],
            "missing_slots": [],
        },
        {
            "slots": {},
            "slot_confidence": {},
            "missing_slots": [],
            "ambiguous_slots": [],
        },
        {
            "final_response": "请说明您想查询的热点、个股还是数据指标？",
            "next_expected_slots": ["intent_scope"],
            "clarification_questions": ["您想了解哪类投研问题？"],
        },
    ]

    with patch.object(
        LLMService,
        "_intent_client",
        return_value=type(
            "MockClient",
            (),
            {
                "chat_completion": _mock_llm_json_responses(mock_responses),
                "extract_message_content": staticmethod(
                    lambda body: body["choices"][0]["message"]["content"]
                ),
            },
        )(),
    ):
        result = await graph.ainvoke(
            {
                "user_query": "那个怎么样",
                "session_id": "session_clarify",
                "chat_history": [],
                "trace_steps": [],
            }
        )

    node_names = [step["node"] for step in result.get("trace_steps", [])]
    assert "clarification_response" in node_names
    assert "routing_decision" not in node_names
    assert result.get("final_response")
    assert result.get("need_clarification") is True


@pytest.mark.asyncio
async def test_graph_clear_stock_query_reaches_stock_route() -> None:
    deps = GraphDeps(
        llm=LLMService(AppSettings()),
        rag=RagService(),
        settings=AppSettings(),
    )
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
            "slots": {
                "stock_name": "泸州老窖",
                "analysis_dimension": "基本面",
            },
            "slot_confidence": {"stock_name": 0.95},
            "missing_slots": [],
            "ambiguous_slots": [],
        },
    ]

    with patch.object(
        LLMService,
        "_intent_client",
        return_value=type(
            "MockClient",
            (),
            {
                "chat_completion": _mock_llm_json_responses(mock_responses),
                "extract_message_content": staticmethod(
                    lambda body: body["choices"][0]["message"]["content"]
                ),
            },
        )(),
    ):
        result = await graph.ainvoke(
            {
                "user_query": "帮我看一下泸州老窖基本面怎么样？",
                "session_id": "session_stock",
                "chat_history": [],
                "trace_steps": [],
            }
        )

    node_names = [step["node"] for step in result.get("trace_steps", [])]
    routing_steps = [
        step for step in result.get("trace_steps", []) if step["node"] == "routing_decision"
    ]
    assert "query_rewrite" in node_names
    assert routing_steps
    assert routing_steps[0]["output"]["route_target"] == "stock_analysis_agent"
    assert result.get("route_target") == "stock_analysis_agent"
    assert result.get("need_clarification") is False


@pytest.mark.asyncio
async def test_runner_ainvoke_accepts_query_and_history() -> None:
    runner = LangGraphRunner(
        llm=LLMService(AppSettings()),
        rag=RagService(),
        db=AsyncMock(),
        settings=AppSettings(),
    )

    class _FakeGraph:
        async def ainvoke(self, state: AgentState) -> AgentState:
            assert state["user_query"] == "测试问题"
            assert state["session_id"] == "sess_1"
            assert state["chat_history"] == [{"role": "user", "content": "上一轮"}]
            return {**state, "trace_steps": [], "current_node": "context_preprocess"}

    runner._graph = _FakeGraph()

    result = await runner.ainvoke(
        user_query="测试问题",
        session_id="sess_1",
        chat_history=[{"role": "user", "content": "上一轮"}],
    )
    assert result["user_query"] == "测试问题"
    assert result["session_id"] == "sess_1"
