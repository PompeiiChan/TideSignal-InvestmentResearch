"""data_query_agent node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.agents.data_query import data_query_agent_prompt
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ..data_query_tool_plan import resolve_data_query_tool_names
from ._helpers import (
    call_intent_json,
    normalize_string_list,
    response_kind_for_intent,
    run_node_with_trace,
)


def _default_tool_params(slots: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {
        "industry": slots.get("industry", ""),
        "metric": slots.get("metric", "涨幅排行"),
        "time_range": slots.get("time_range", "近一交易日"),
        "rank_limit": 8,
    }
    if slots.get("trade_date"):
        params["trade_date"] = slots.get("trade_date")
    for key in ("buy_price", "sell_price", "share_count", "fee_rate"):
        if key in slots:
            params[key] = slots[key]
    return params


async def data_query_agent(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Plan data query and tool parameters via LLM sub-agent."""
    _ = rag
    normalized_query = str(state.get("normalized_query", "")).strip()
    slots = state.get("slots") or {}
    intent_id = str(state.get("intent_id", "data_query"))

    input_data = {
        "normalized_query": normalized_query,
        "slots": slots,
        "intent_id": intent_id,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        parsed = await call_intent_json(
            llm,
            system_prompt=data_query_agent_prompt(time_ctx),
            user_payload=input_data,
        )
        agent_result = str(parsed.get("agent_result", "")).strip()
        data_table = parsed.get("data_table")
        if not isinstance(data_table, list):
            data_table = []
        tool_params = parsed.get("tool_params")
        if not isinstance(tool_params, dict):
            tool_params = _default_tool_params(slots)
        else:
            merged = _default_tool_params(slots)
            merged.update(tool_params)
            tool_params = merged
        raw_tool_names = normalize_string_list(parsed.get("tool_names"))
        agent_tool_names = resolve_data_query_tool_names(
            raw_tool_names,
            query=normalized_query,
            slots=slots,
        )
        output = {
            "agent_result": agent_result,
            "data_table": data_table,
            "data_source": str(parsed.get("data_source", "东方财富 push2 行情（market_ranking_lookup）")),
            "tool_params": tool_params,
            "agent_tool_names": agent_tool_names,
            "response_kind": response_kind_for_intent(intent_id),
        }
        return output, "完成问数查询规划"

    return await run_node_with_trace(
        state,
        node="data_query_agent",
        input_data=input_data,
        summary="完成问数查询规划",
        fn=_execute,
    )
