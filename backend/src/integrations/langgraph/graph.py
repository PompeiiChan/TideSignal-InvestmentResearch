"""LangGraph StateGraph builder aligned with langgraph-flow.md."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache, partial
from typing import Any

from langgraph.graph import END, StateGraph

from ...agents.nodes import ALL_NODES
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...settings import AppSettings, get_settings
from .routing import (
    AGENT_NODES,
    fanout_after_agent,
    route_after_clarification,
    route_after_quality,
    route_after_routing,
)
from .state import AgentState

ROUTE_TARGETS = (
    "hotspot_agent",
    "data_query_agent",
    "stock_analysis_agent",
    "document_qa_agent",
    "fallback_response",
)


@dataclass(frozen=True)
class GraphDeps:
    """Dependencies injected into LangGraph node callables."""

    llm: LLMService
    rag: RagService
    settings: AppSettings


def _bind_node(node_fn: Any, deps: GraphDeps) -> Any:
    return partial(
        node_fn,
        llm=deps.llm,
        rag=deps.rag,
        settings=deps.settings,
    )


def build_graph(deps: GraphDeps) -> Any:
    """Build and compile the investment research LangGraph workflow."""
    graph = StateGraph(AgentState)

    for name, node_fn in ALL_NODES.items():
        graph.add_node(name, _bind_node(node_fn, deps))

    graph.set_entry_point("context_preprocess")
    graph.add_edge("context_preprocess", "intent_recognition")
    graph.add_edge("intent_recognition", "slot_extraction")
    graph.add_edge("slot_extraction", "clarification_check")
    graph.add_conditional_edges(
        "clarification_check",
        route_after_clarification,
        {
            "clarification_response": "clarification_response",
            "routing_decision": "routing_decision",
        },
    )
    graph.add_edge("clarification_response", END)
    graph.add_conditional_edges(
        "routing_decision",
        route_after_routing,
        {target: target for target in ROUTE_TARGETS},
    )

    for agent in AGENT_NODES:
        graph.add_conditional_edges(agent, fanout_after_agent)

    graph.add_edge("rag_retrieval", "evidence_merge")
    graph.add_edge("tool_call", "evidence_merge")
    graph.add_edge("evidence_merge", "quality_check")
    graph.add_conditional_edges(
        "quality_check",
        route_after_quality,
        {
            "response_assembly": "response_assembly",
            "fallback_response": "fallback_response",
        },
    )
    graph.add_edge("response_assembly", END)
    graph.add_edge("fallback_response", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_compiled_graph(
    llm_id: int,
    rag_id: int,
    settings_langgraph_env: str,
) -> Any:
    """Return a module-level cached compiled graph for the given dependency ids."""
    _ = (llm_id, rag_id, settings_langgraph_env)
    settings = get_settings()
    deps = GraphDeps(
        llm=LLMService(),
        rag=RagService(settings),
        settings=settings,
    )
    return build_graph(deps)
