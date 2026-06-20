"""hotspot_agent node."""

from __future__ import annotations

from typing import Any, cast

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.agents.hotspot import hotspot_agent_prompt
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...services.trading_calendar import apply_tool_trading_defaults
from ...settings import AppSettings
from ..hotspot_tool_plan import resolve_hotspot_stock_codes, resolve_hotspot_tool_names
from ._helpers import call_intent_json, response_kind_for_intent, run_node_with_trace


def _apply_hotspot_tool_trading_defaults(
    tool_params: dict[str, Any],
    *,
    slots: dict[str, Any],
    query: str,
    last_trading_day: str,
    is_trading_day: bool,
    current_date: str = "",
) -> dict[str, Any]:
    return apply_tool_trading_defaults(
        tool_params,
        slots=slots,
        query=query,
        last_trading_day=last_trading_day,
        is_current_trading_day=is_trading_day,
        current_date=current_date,
    )


async def hotspot_agent(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Plan hotspot analysis via LLM sub-agent."""
    _ = rag
    normalized_query = str(state.get("normalized_query", "")).strip()
    slots = state.get("slots") or {}
    execution_plan = state.get("execution_plan") or {}
    intent_id = str(state.get("intent_id", "hotspot_analysis"))

    input_data = {
        "normalized_query": normalized_query,
        "slots": slots,
        "intent_id": intent_id,
        "execution_plan": execution_plan,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        parsed = await call_intent_json(
            llm,
            system_prompt=hotspot_agent_prompt(time_ctx),
            user_payload=input_data,
        )
        agent_result = str(parsed.get("agent_result", "")).strip()
        evidence_list = parsed.get("evidence_list")
        if not isinstance(evidence_list, list):
            evidence_list = []
        raw_tool_params = parsed.get("tool_params")
        plan_defaults: dict[str, Any] = (
            cast(dict[str, Any], execution_plan.get("tool_params_defaults"))
            if isinstance(execution_plan.get("tool_params_defaults"), dict)
            else {}
        )
        if not isinstance(raw_tool_params, dict):
            tool_params: dict[str, Any] = {
                "topic": slots.get("topic") or slots.get("industry") or "",
                "industry": slots.get("industry", ""),
                "event": slots.get("event", ""),
                "time_range": slots.get("time_range", "2026-06"),
                "signal_limit": 10,
                "stock_codes": slots.get("stock_code", "") or slots.get("stock_codes", ""),
                "news_limit": 30,
            }
        else:
            tool_params = cast(dict[str, Any], raw_tool_params)
            tool_params.setdefault("topic", slots.get("topic") or slots.get("industry") or "")
            tool_params.setdefault("industry", slots.get("industry", ""))
            tool_params.setdefault("event", slots.get("event", ""))
            tool_params.setdefault("time_range", slots.get("time_range", "2026-06"))
            tool_params.setdefault("signal_limit", 10)
            tool_params.setdefault("stock_codes", slots.get("stock_code", "") or slots.get("stock_codes", ""))
            tool_params.setdefault("news_limit", 30)
        for key, value in plan_defaults.items():
            tool_params.setdefault(key, value)
        tool_params = _apply_hotspot_tool_trading_defaults(
            tool_params,
            slots=slots,
            query=normalized_query,
            last_trading_day=time_ctx.last_trading_day,
            is_trading_day=time_ctx.is_trading_day,
            current_date=time_ctx.current_date,
        )
        tool_params["stock_codes"] = resolve_hotspot_stock_codes(
            query=normalized_query,
            slots=slots,
            tool_stock_codes=str(tool_params.get("stock_codes", "")),
        )
        raw_tool_names = parsed.get("tool_names")
        requested_tool_names = (
            [str(name) for name in raw_tool_names if str(name).strip()]
            if isinstance(raw_tool_names, list)
            else None
        )
        agent_tool_names = resolve_hotspot_tool_names(
            requested_tool_names,
            query=normalized_query,
            slots=slots,
            execution_plan=execution_plan,
        )
        data_source_default = str(
            execution_plan.get("data_source_hint", "RAG 月报/行业研报 + 东财快讯/巨潮公告 + 同花顺当日信号")
        )
        output = {
            "agent_result": agent_result,
            "evidence_list": evidence_list,
            "followup_need": bool(parsed.get("followup_need", False)),
            "tool_params": tool_params,
            "agent_tool_names": agent_tool_names,
            "data_source": str(parsed.get("data_source", data_source_default)),
            "response_kind": response_kind_for_intent(intent_id),
        }
        return output, "完成热点解读规划"

    return await run_node_with_trace(
        state,
        node="hotspot_agent",
        input_data=input_data,
        summary="完成热点解读规划",
        fn=_execute,
    )
