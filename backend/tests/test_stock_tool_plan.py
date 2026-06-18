"""Tests for dynamic stock tool orchestration."""

from __future__ import annotations

from unittest.mock import patch

from backend.src.agents.stock_tool_plan import resolve_stock_tool_names
from backend.src.agents.tools.valuation_profile_lookup import lookup_valuation_profile


def test_resolve_stock_tool_names_fallback_includes_valuation_for_general_query() -> None:
    names = resolve_stock_tool_names(
        None,
        query="长春高新基本面怎么样",
        analysis_dimensions=["利润修复", "估值匹配"],
    )
    assert names == ["mock_financial_profile_lookup", "valuation_profile_lookup"]


def test_resolve_stock_tool_names_financial_only_query() -> None:
    names = resolve_stock_tool_names(
        None,
        query="分析一下千禾味业2026Q1财报业绩",
        analysis_dimensions=["营收", "净利润"],
    )
    assert names == ["mock_financial_profile_lookup"]


def test_resolve_stock_tool_names_respects_agent_selection() -> None:
    names = resolve_stock_tool_names(
        ["mock_financial_profile_lookup"],
        query="长春高新基本面怎么样",
        analysis_dimensions=["估值"],
    )
    assert names == ["mock_financial_profile_lookup"]


def test_resolve_stock_tool_names_filters_unknown_tools() -> None:
    names = resolve_stock_tool_names(
        ["mock_financial_profile_lookup", "unknown_tool", "valuation_profile_lookup"],
        query="估值贵不贵",
        analysis_dimensions=[],
    )
    assert names == ["mock_financial_profile_lookup", "valuation_profile_lookup"]


def test_resolve_stock_tool_names_pipeline_query_skips_financial_tools() -> None:
    names = resolve_stock_tool_names(
        ["mock_financial_profile_lookup", "valuation_profile_lookup"],
        query="恒瑞医药的创新药管线？",
        analysis_dimensions=["研发管线布局"],
    )
    assert names == []


def test_resolve_stock_tool_names_pipeline_fallback_is_empty() -> None:
    names = resolve_stock_tool_names(
        None,
        query="恒瑞医药的创新药管线怎么样",
        analysis_dimensions=[],
    )
    assert names == []


def test_is_qualitative_business_query_detects_pipeline() -> None:
    from backend.src.agents.stock_tool_plan import is_qualitative_business_query

    assert is_qualitative_business_query(query="恒瑞医药的创新药管线？") is True
    assert is_qualitative_business_query(query="分析一下千禾味业2026Q1财报业绩") is False


@patch("backend.src.agents.tools.valuation_profile_lookup.fetch_quote_snapshot")
@patch("backend.src.agents.tools.valuation_profile_lookup.resolve_stock_code")
def test_lookup_valuation_profile_success(
    mock_resolve: object,
    mock_fetch: object,
) -> None:
    mock_resolve.return_value = ("000661", "长春高新")
    mock_fetch.return_value = {
        "stock_name": "长春高新",
        "price": 120.5,
        "pe_ttm": 18.2,
        "pb": 3.1,
        "market_cap_yi": 480.0,
        "change_pct": 1.2,
        "source": "https://qt.gtimg.cn/",
    }
    result = lookup_valuation_profile(stock_name="长春高新", stock_code="000661.SZ")
    assert result["found"] is True
    assert result["data_origin"] == "tencent_quote_api"
    assert result["valuation"]["pe_ttm"] == "18.2"
