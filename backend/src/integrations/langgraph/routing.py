"""Conditional edge routing functions for LangGraph."""

from __future__ import annotations

from typing import Literal

from langgraph.types import Send

from .state import AgentState

AGENT_NODES = (
    "hotspot_agent",
    "data_query_agent",
    "stock_analysis_agent",
    "document_qa_agent",
)


def route_after_clarification(
    state: AgentState,
) -> Literal["clarification_response", "routing_decision"]:
    """Route to clarification or routing based on need_clarification flag."""
    if state.get("need_clarification"):
        return "clarification_response"
    return "routing_decision"


def route_after_routing(state: AgentState) -> str:
    """Return route_target as the next node name."""
    return state.get("route_target", "fallback_response")


def fanout_after_agent(state: AgentState) -> list[Send]:
    """Fan out to rag_retrieval and/or tool_call based on execution_plan."""
    plan = state.get("execution_plan") or {}
    sends: list[Send] = []
    if plan.get("needs_rag"):
        sends.append(Send("rag_retrieval", state))
    if plan.get("needs_tool"):
        sends.append(Send("tool_call", state))
    if not sends:
        sends.append(Send("evidence_merge", state))
    return sends


def route_after_evidence_merge(
    state: AgentState,
) -> Literal["evidence_gap_check", "multi_agent_handoff", "quality_check"]:
    """After merge, compound stock phase hands off to data agent; single stock may gap-loop."""
    if state.get("evidence_supplement_done"):
        if (
            state.get("multi_agent_mode")
            and state.get("route_target") == "stock_analysis_agent"
            and not state.get("multi_agent_stock_phase_done")
        ):
            return "multi_agent_handoff"
        return "quality_check"
    if (
        state.get("multi_agent_mode")
        and state.get("route_target") == "stock_analysis_agent"
        and not state.get("multi_agent_stock_phase_done")
    ):
        return "multi_agent_handoff"
    if state.get("route_target") == "stock_analysis_agent":
        return "evidence_gap_check"
    return "quality_check"


def route_after_evidence_gap_check(
    state: AgentState,
) -> Literal["gap_planner", "quality_check"]:
    """Enter gap planner only when enrichment is still needed."""
    if state.get("should_enrich_evidence"):
        return "gap_planner"
    return "quality_check"


def fanout_after_gap_planner(state: AgentState) -> list[Send]:
    """Fan out to targeted supplement fetchers or skip directly to merge."""
    plan = state.get("gap_enrichment_plan") or {}
    rag_queries = plan.get("rag_queries") if isinstance(plan.get("rag_queries"), list) else []
    tool_names = plan.get("tool_names") if isinstance(plan.get("tool_names"), list) else []
    supplement_state = {
        **state,
        "supplement_mode": True,
        "supplement_rag_queries": rag_queries,
        "supplement_rag_filters": plan.get("rag_filters") or {},
        "supplement_tool_names": tool_names,
    }
    sends: list[Send] = []
    if rag_queries:
        sends.append(Send("rag_retrieval", supplement_state))
    if tool_names:
        sends.append(Send("tool_call", supplement_state))
    if not sends:
        sends.append(
            Send(
                "evidence_merge",
                {
                    **state,
                    "supplement_mode": False,
                    "evidence_supplement_done": True,
                },
            )
        )
    return sends


def route_after_quality(
    state: AgentState,
) -> Literal["response_assembly", "fallback_response"]:
    """Route rejected quality checks to fallback."""
    if state.get("quality_status") == "reject":
        return "fallback_response"
    return "response_assembly"
