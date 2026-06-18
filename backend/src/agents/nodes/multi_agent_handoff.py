"""Hand off from stock-analysis phase to data-query phase in compound routing."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.service import LLMService
from ...services.compound_routing import enrich_slots_for_compound
from ...services.rag.service import RagService
from ...settings import AppSettings
from ._helpers import run_node_with_trace
from .routing_decision import build_execution_plan


async def multi_agent_handoff(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Prepare the data-query agent phase after stock-analysis evidence is merged."""
    _ = (llm, rag, settings)
    normalized_query = str(state.get("normalized_query", "")).strip()
    slots = enrich_slots_for_compound(
        normalized_query,
        dict(state.get("slots") or {}),
    )

    input_data = {
        "from_agent": state.get("route_target", ""),
        "to_agent": "data_query_agent",
        "multi_agent_mode": True,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        summaries = dict(state.get("agent_summaries") or {})
        stock_summary = str(state.get("agent_result", "")).strip()
        if stock_summary:
            summaries["stock_analysis_agent"] = stock_summary

        accumulated_rag = list(state.get("accumulated_rag_hits") or state.get("rag_hits") or [])
        accumulated_tool = dict(state.get("accumulated_tool_result") or state.get("tool_result") or {})

        execution_plan = build_execution_plan(
            "data_query_agent",
            slots=slots,
            query=normalized_query,
        )
        output: dict[str, Any] = {
            "route_target": "data_query_agent",
            "route_reason": "复合意图：行业基本面已完成，切换至问数助手处理市场热度",
            "execution_plan": execution_plan,
            "slots": slots,
            "agent_summaries": summaries,
            "agent_result": "",
            "agent_tool_names": [],
            "analysis_dimensions": [],
            "data_table": [],
            "accumulated_rag_hits": accumulated_rag,
            "accumulated_tool_result": accumulated_tool,
            "rag_hits": [],
            "tool_result": {},
            "retrieved_chunks": [],
            "citations": [],
            "multi_agent_stock_phase_done": True,
            "response_kind": "compound_stock_data",
        }
        return output, "问股阶段完成，切换至问数助手"

    return await run_node_with_trace(
        state,
        node="multi_agent_handoff",
        input_data=input_data,
        summary="切换至问数助手",
        fn=_execute,
    )
