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
            "data_origin": "sina_api",
            "is_mock": False,
            "source": "https://quotes.sina.cn/",
            "attribution": "third_party/a-stock-data (Apache-2.0)",
        },
        "valuation_profile_lookup": lambda **_kwargs: {
            "tool": "valuation_profile_lookup",
            "found": True,
            "data_origin": "tencent_quote_api",
            "is_mock": False,
            "source": "https://qt.gtimg.cn/",
            "attribution": "third_party/a-stock-data (Apache-2.0)",
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
    trace_step = result["trace_steps"][-1]
    assert "detail_sections" in trace_step
    titles = [section["title"] for section in trace_step["detail_sections"]]
    assert "工具归因" in titles
    output = trace_step["output"]
    assert "tool_attributions" in output
    assert len(output["tool_attributions"]) == 2
    assert output["tool_attributions"][0]["attribution"] == "third_party/a-stock-data (Apache-2.0)"
