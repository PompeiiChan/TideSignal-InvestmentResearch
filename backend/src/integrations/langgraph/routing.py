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


def route_after_quality(
    state: AgentState,
) -> Literal["response_assembly", "fallback_response"]:
    """Route rejected quality checks to fallback."""
    if state.get("quality_status") == "reject":
        return "fallback_response"
    return "response_assembly"
