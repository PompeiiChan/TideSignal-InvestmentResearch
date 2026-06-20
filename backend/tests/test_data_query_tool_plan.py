"""Tests for data-query tool orchestration."""

from __future__ import annotations

from backend.src.agents.data_query_tool_plan import resolve_data_query_tool_names


def test_resolve_dual_tools_for_heatmap_and_ranking_query() -> None:
    names = resolve_data_query_tool_names(
        None,
        query="今天行业板块热力图怎么样，顺便看看半导体涨幅前五",
        slots={},
    )
    assert "sector_heatmap_lookup" in names
    assert "market_ranking_lookup" in names


def test_resolve_ranking_only_for_industry_leaderboard() -> None:
    names = resolve_data_query_tool_names(
        None,
        query="全行业板块涨幅榜",
        slots={},
    )
    assert names == ["market_ranking_lookup"]


def test_resolve_heatmap_only() -> None:
    names = resolve_data_query_tool_names(
        None,
        query="帮我看一下行业板块热力图",
        slots={},
    )
    assert names == ["sector_heatmap_lookup"]


def test_resolve_heatmap_for_a_share_sector_phrase() -> None:
    names = resolve_data_query_tool_names(
        None,
        query="帮我看一下今天A股行业板块热力图",
        slots={},
    )
    assert names == ["sector_heatmap_lookup"]


def test_calculator_exclusive_when_slots_complete() -> None:
    names = resolve_data_query_tool_names(
        ["market_ranking_lookup", "sector_heatmap_lookup"],
        query="随便",
        slots={"buy_price": 10, "sell_price": 12, "share_count": 1000},
    )
    assert names == ["local_return_calculator"]


def test_respects_agent_tool_selection() -> None:
    names = resolve_data_query_tool_names(
        ["sector_heatmap_lookup"],
        query="半导体涨幅排行",
        slots={},
    )
    assert names == ["sector_heatmap_lookup"]


def test_resolve_ranking_for_market_heat_query() -> None:
    names = resolve_data_query_tool_names(
        None,
        query="宠物行业最近市场热度怎么样？",
        slots={"industry": "宠物行业"},
    )
    assert names == ["market_ranking_lookup"]


def test_agent_ranking_only_still_gets_heatmap_for_heatmap_query() -> None:
    """LLM 若只选排行工具，规则层仍须补热力图（BC：热力图问句不出组件）。"""
    names = resolve_data_query_tool_names(
        ["market_ranking_lookup"],
        query="帮我看一下今天A股行业板块热力图",
        slots={"metric": "行业板块热力图", "time_range": "近一交易日", "market": "A股"},
    )
    assert names == ["sector_heatmap_lookup"]
