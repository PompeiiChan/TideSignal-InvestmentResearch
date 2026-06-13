"""hotspot_agent node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.agents.hotspot import hotspot_agent_prompt
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ._helpers import call_intent_json, response_kind_for_intent, run_node_with_trace


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
    intent_id = str(state.get("intent_id", "hotspot_analysis"))

    input_data = {
        "normalized_query": normalized_query,
        "slots": slots,
        "intent_id": intent_id,
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
        tool_params = parsed.get("tool_params")
        if not isinstance(tool_params, dict):
            tool_params = {
                "topic": slots.get("topic") or slots.get("industry") or "",
                "industry": slots.get("industry", ""),
                "event": slots.get("event", ""),
                "time_range": slots.get("time_range", "2026-06"),
                "signal_limit": 10,
                "stock_codes": slots.get("stock_code", "") or slots.get("stock_codes", ""),
                "news_limit": 30,
            }
        else:
            tool_params.setdefault("topic", slots.get("topic") or slots.get("industry") or "")
            tool_params.setdefault("industry", slots.get("industry", ""))
            tool_params.setdefault("event", slots.get("event", ""))
            tool_params.setdefault("time_range", slots.get("time_range", "2026-06"))
            tool_params.setdefault("signal_limit", 10)
            tool_params.setdefault("stock_codes", slots.get("stock_code", "") or slots.get("stock_codes", ""))
            tool_params.setdefault("news_limit", 30)
        output = {
            "agent_result": agent_result,
            "evidence_list": evidence_list,
            "followup_need": bool(parsed.get("followup_need", False)),
            "tool_params": tool_params,
            "data_source": str(
                parsed.get(
                    "data_source",
                    "RAG 月报/行业研报 + 东财快讯/巨潮公告 + 同花顺当日信号",
                )
            ),
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
