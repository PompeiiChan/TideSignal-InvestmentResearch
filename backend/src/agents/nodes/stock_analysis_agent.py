"""stock_analysis_agent node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.agents.stock_analysis import stock_analysis_agent_prompt
from ...integrations.llm.service import LLMService
from ...services.conversation_context import build_conversation_context
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ..stock_tool_plan import (
    is_qualitative_business_query,
    resolve_stock_tool_names,
)
from ._helpers import (
    call_intent_json,
    normalize_string_list,
    response_kind_for_intent,
    run_node_with_trace,
)


async def stock_analysis_agent(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Plan stock analysis dimensions via LLM sub-agent."""
    _ = rag
    normalized_query = str(state.get("normalized_query", "")).strip()
    slots = state.get("slots") or {}
    active_slots = state.get("active_slots") or slots
    history_summary = str(state.get("history_summary", "")).strip()
    inherited_slot_keys = state.get("inherited_slot_keys") or []
    intent_id = str(state.get("intent_id", "stock_analysis"))
    conversation_context = build_conversation_context(
        history_summary=history_summary,
        active_slots=active_slots,
        inherited_slot_keys=inherited_slot_keys,
        normalized_query=normalized_query,
    )

    input_data = {
        "normalized_query": normalized_query,
        "slots": slots,
        "active_slots": active_slots,
        "history_summary": history_summary,
        "conversation_context": conversation_context,
        "intent_id": intent_id,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        parsed = await call_intent_json(
            llm,
            system_prompt=stock_analysis_agent_prompt(time_ctx),
            user_payload=input_data,
        )
        agent_result = str(parsed.get("agent_result", "")).strip()
        analysis_dimensions = normalize_string_list(parsed.get("analysis_dimensions"))
        if not analysis_dimensions:
            if is_qualitative_business_query(query=normalized_query):
                analysis_dimensions = ["研发管线布局", "临床与商业化进度", "核心产品与适应症"]
            else:
                analysis_dimensions = ["基本面", "盈利能力", "估值水平"]
        tool_params = parsed.get("tool_params")
        if not isinstance(tool_params, dict):
            tool_params = {
                "stock_name": slots.get("stock_name", ""),
                "stock_code": slots.get("stock_code", ""),
                "analysis_dimension": slots.get("analysis_dimension", "基本面"),
            }
        raw_tool_names = normalize_string_list(parsed.get("tool_names"))
        agent_tool_names = resolve_stock_tool_names(
            raw_tool_names,
            query=normalized_query,
            analysis_dimensions=analysis_dimensions,
        )
        output = {
            "agent_result": agent_result,
            "analysis_dimensions": analysis_dimensions,
            "tool_params": tool_params,
            "agent_tool_names": agent_tool_names,
            "response_kind": response_kind_for_intent(intent_id),
        }
        return output, "完成问股分析规划"

    return await run_node_with_trace(
        state,
        node="stock_analysis_agent",
        input_data=input_data,
        summary="完成问股分析规划",
        fn=_execute,
    )
