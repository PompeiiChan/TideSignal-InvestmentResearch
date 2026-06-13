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
