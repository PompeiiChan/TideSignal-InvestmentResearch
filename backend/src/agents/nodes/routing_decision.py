"""routing_decision node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...settings import AppSettings
from ._helpers import run_node_with_trace

_INTENT_ROUTE_MAP: dict[str, str] = {
    "hotspot_analysis": "hotspot_agent",
    "data_query": "data_query_agent",
    "stock_analysis": "stock_analysis_agent",
    "document_qa": "document_qa_agent",
    "prediction_request": "fallback_response",
    "chit_chat": "fallback_response",
    "unknown": "fallback_response",
}

_EXECUTION_PLANS: dict[str, dict[str, Any]] = {
    "hotspot_agent": {
        "needs_rag": True,
        "needs_tool": True,
        "tool_names": ["hotspot_signal_lookup", "hotspot_fact_lookup"],
        "retrieval_config": {"top_k": 10, "strategy": "hotspot_dual", "filters": {}},
    },
    "data_query_agent": {
        "needs_rag": False,
        "needs_tool": True,
        "tool_names": [],
        "tool_plan_mode": "agent",
        "retrieval_config": {"top_k": 8, "filters": {}},
    },
    "stock_analysis_agent": {
        "needs_rag": True,
        "needs_tool": True,
        "tool_names": [],
        "tool_plan_mode": "agent",
        "retrieval_config": {"top_k": 8, "filters": {}},
    },
    "document_qa_agent": {
        "needs_rag": True,
        "needs_tool": False,
        "tool_names": [],
        "retrieval_config": {"top_k": 8, "filters": {}},
    },
    "fallback_response": {
        "needs_rag": False,
        "needs_tool": False,
        "tool_names": [],
        "retrieval_config": {},
    },
}

_ROUTE_REASONS: dict[str, str] = {
    "hotspot_agent": "用户询问市场热点或事件解读，进入热点解读 Agent",
    "data_query_agent": "用户询问排行或指标数据，进入问数 Agent",
    "stock_analysis_agent": "用户询问个股诊断或基本面，进入问股 Agent",
    "document_qa_agent": "用户询问文档内容，进入文档问答 Agent",
    "fallback_response": "意图为闲聊、未知或预测类请求，进入兜底回复",
}


def resolve_route_target(intent_id: str) -> str:
    return _INTENT_ROUTE_MAP.get(intent_id, "fallback_response")


def _has_return_calculator_slots(slots: dict[str, Any]) -> bool:
    required = ("buy_price", "sell_price", "share_count")
    return all(key in slots and slots[key] not in (None, "") for key in required)


def build_execution_plan(
    route_target: str,
    *,
    slots: dict[str, Any] | None = None,
    query: str = "",
) -> dict[str, Any]:
    if route_target == "data_query_agent" and slots and _has_return_calculator_slots(slots):
        return {
            "needs_rag": False,
            "needs_tool": True,
            "tool_names": ["local_return_calculator"],
            "tool_plan_mode": "calculator",
            "retrieval_config": {},
        }
    return dict(_EXECUTION_PLANS.get(route_target, _EXECUTION_PLANS["fallback_response"]))


async def routing_decision(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Map intent and slots to downstream agent route."""
    _ = (llm, rag, settings)
    intent_id = str(state.get("intent_id", "unknown"))
    slots = state.get("slots") or {}
    normalized_query = str(state.get("normalized_query", "")).strip()
    context_pack = state.get("context_pack") or {}
    risk_hint = str(state.get("risk_hint", ""))

    input_data = {
        "intent_id": intent_id,
        "slots": slots,
        "context_pack": context_pack,
        "risk_hint": risk_hint,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        route_target = resolve_route_target(intent_id)
        if risk_hint == "prediction_boundary" and intent_id != "data_query":
            route_target = "fallback_response"
        route_reason = _ROUTE_REASONS.get(route_target, "根据意图选择执行链路")
        execution_plan = build_execution_plan(
            route_target,
            slots=slots,
            query=normalized_query,
        )
        output = {
            "route_target": route_target,
            "route_reason": route_reason,
            "execution_plan": execution_plan,
            "langgraph_connected": True,
        }
        return output, f"路由至 {route_target}"

    return await run_node_with_trace(
        state,
        node="routing_decision",
        input_data=input_data,
        summary="完成路由决策",
        fn=_execute,
    )
