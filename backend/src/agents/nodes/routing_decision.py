"""routing_decision node."""

from __future__ import annotations

from datetime import date
from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.service import LLMService
from ...services.compound_routing import enrich_slots_for_compound, resolve_compound_route_targets
from ...services.hotspot_recency import build_hotspot_execution_plan
from ...services.rag.chunker import resolve_kb_root
from ...services.rag.company_index import (
    enrich_stock_slots_from_kb,
    is_kb_resolvable_document_query,
)
from ...services.rag.service import RagService
from ...services.scenario_return import is_scenario_return_query
from ...services.system_time import resolve_system_time
from ...settings import BACKEND_ROOT, AppSettings
from ..stock_tool_plan import is_qualitative_business_query
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
    if route_target == "hotspot_agent":
        time_ctx = resolve_system_time()
        current = date.fromisoformat(time_ctx.current_date)
        return build_hotspot_execution_plan(query, slots, current_date=current)
    plan = dict(_EXECUTION_PLANS.get(route_target, _EXECUTION_PLANS["fallback_response"]))
    if route_target == "stock_analysis_agent" and slots and (
        slots.get("scenario_return_mode") or is_scenario_return_query(query)
    ):
        plan["scenario_return_mode"] = True
    if route_target == "stock_analysis_agent" and is_qualitative_business_query(query=query):
        plan["stock_narrative_mode"] = True
        plan["needs_tool"] = False
        plan["tool_names"] = []
        plan["retrieval_config"] = {
            "top_k": 10,
            "strategy": "stock_narrative",
            "filters": {},
        }
    return plan


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
    slots = enrich_slots_for_compound(
        str(state.get("normalized_query", "")).strip(),
        dict(state.get("slots") or {}),
    )
    normalized_query = str(state.get("normalized_query", "")).strip()
    context_pack = state.get("context_pack") or {}
    risk_hint = str(state.get("risk_hint", ""))
    candidate_intents = state.get("candidate_intents") or []

    input_data = {
        "intent_id": intent_id,
        "slots": slots,
        "context_pack": context_pack,
        "risk_hint": risk_hint,
        "candidate_intents": candidate_intents,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)
        route_slots = dict(slots)
        effective_intent = intent_id
        if intent_id == "document_qa" and is_kb_resolvable_document_query(
            normalized_query, route_slots, kb_root
        ):
            route_slots = enrich_stock_slots_from_kb(normalized_query, route_slots, kb_root)
            effective_intent = "stock_analysis"

        compound_targets = resolve_compound_route_targets(
            normalized_query,
            intent_id=effective_intent,
            slots=route_slots,
            candidate_intents=candidate_intents if isinstance(candidate_intents, list) else [],
        )
        if compound_targets:
            route_target = compound_targets[0]
            route_reason = "复合意图：行业基本面走问股助手，市场热度走问数助手"
            execution_plan = build_execution_plan(
                route_target,
                slots=route_slots,
                query=normalized_query,
            )
            output = {
                "route_target": route_target,
                "route_targets": compound_targets,
                "multi_agent_mode": True,
                "multi_agent_stock_phase_done": False,
                "multi_agent_data_phase_done": False,
                "agent_summaries": {},
                "is_multi_intent": True,
                "route_reason": route_reason,
                "execution_plan": execution_plan,
                "response_kind": "compound_stock_data",
                "slots": route_slots,
                "langgraph_connected": True,
            }
            return output, f"复合路由：{' → '.join(compound_targets)}"

        route_target = resolve_route_target(effective_intent)
        if (
            risk_hint == "prediction_boundary"
            and effective_intent != "data_query"
            and not is_scenario_return_query(normalized_query)
            and not route_slots.get("scenario_return_mode")
        ):
            route_target = "fallback_response"
        route_reason = _ROUTE_REASONS.get(route_target, "根据意图选择执行链路")
        execution_plan = build_execution_plan(
            route_target,
            slots=route_slots,
            query=normalized_query,
        )
        output = {
            "route_target": route_target,
            "route_reason": route_reason,
            "execution_plan": execution_plan,
            "slots": route_slots,
            "multi_agent_mode": False,
            "is_multi_intent": False,
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
