"""Tests for execution plan heatmap routing (agent-driven tool plan)."""

from backend.src.agents.data_query_tool_plan import resolve_data_query_tool_names
from backend.src.agents.nodes.routing_decision import build_execution_plan


def test_build_execution_plan_data_query_uses_agent_mode() -> None:
    plan = build_execution_plan(
        "data_query_agent",
        slots={},
        query="帮我看一下今天行业板块热力图",
    )
    assert plan["tool_names"] == []
    assert plan.get("tool_plan_mode") == "agent"


def test_resolve_tools_for_heatmap_query() -> None:
    names = resolve_data_query_tool_names(
        None,
        query="帮我看一下今天行业板块热力图",
        slots={},
    )
    assert names == ["sector_heatmap_lookup"]
