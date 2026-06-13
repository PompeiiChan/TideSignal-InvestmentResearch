"""Tests for stock-aware tool_call resolution."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.src.agents.nodes.tool_call import tool_call
from backend.src.integrations.langgraph.state import AgentState
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


@pytest.mark.asyncio
@patch("backend.src.agents.nodes.tool_call.TOOL_REGISTRY")
async def test_tool_call_uses_agent_tool_names_for_stock_route(mock_registry: object) -> None:
    mock_registry.get = lambda name: {
        "mock_financial_profile_lookup": lambda **_kwargs: {
            "tool": "mock_financial_profile_lookup",
            "found": True,
        },
        "valuation_profile_lookup": lambda **_kwargs: {
            "tool": "valuation_profile_lookup",
            "found": True,
        },
    }.get(name)
    llm = LLMService(AppSettings())
    rag = RagService()
    settings = AppSettings()
    state: AgentState = {
        "route_target": "stock_analysis_agent",
        "normalized_query": "长春高新估值贵不贵",
        "analysis_dimensions": ["估值水平"],
        "agent_tool_names": ["mock_financial_profile_lookup", "valuation_profile_lookup"],
        "execution_plan": {"tool_names": []},
        "tool_params": {"stock_name": "长春高新", "stock_code": "000661.SZ"},
        "trace_steps": [],
    }
    result = await tool_call(state, llm=llm, rag=rag, settings=settings)

    assert result["tool_status"] == "success"
    assert "mock_financial_profile_lookup" in result["tool_result"]
    assert "valuation_profile_lookup" in result["tool_result"]
    assert len(result["tool_result"]["tools"]) == 2
