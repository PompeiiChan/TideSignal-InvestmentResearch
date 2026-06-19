"""Tests for hotspot dynamic tool orchestration."""

from __future__ import annotations

from src.agents.hotspot_tool_plan import (
    ranking_industry_param,
    resolve_hotspot_stock_codes,
    resolve_hotspot_tool_names,
    wants_market_ranking,
)


def test_wants_market_ranking_on_heat_keyword() -> None:
    query = "宠物行业是否值得看好？逻辑、分类、关注公司、最近市场热度怎么样？"
    assert wants_market_ranking(query, {}) is True


def test_resolve_hotspot_tools_includes_ranking_for_pet_query() -> None:
    query = "宠物行业是否值得看好？逻辑、分类、关注公司、最近市场热度怎么样？"
    names = resolve_hotspot_tool_names(None, query=query, slots={"industry": "宠物"})
    assert "hotspot_fact_lookup" in names
    assert "hotspot_signal_lookup" in names
    assert "market_ranking_lookup" in names


def test_resolve_hotspot_tools_adds_heatmap_when_asked() -> None:
    query = "机器人板块在全市场热力图里排第几？"
    names = resolve_hotspot_tool_names(None, query=query, slots={})
    assert "sector_heatmap_lookup" in names


def test_ranking_industry_param_from_query() -> None:
    assert ranking_industry_param(query="宠物行业最近怎么样", slots={}) == "宠物行业"


def test_ranking_industry_param_prefers_slots() -> None:
    assert ranking_industry_param(query="最近热度", slots={"topic": "宠物"}) == "宠物"


def test_resolve_hotspot_tools_skip_signal_for_replay() -> None:
    query = "帮我复盘4月到6月半导体热点演变"
    names = resolve_hotspot_tool_names(None, query=query, slots={"topic": "半导体"})
    assert names == ["hotspot_fact_lookup"]


def test_resolve_hotspot_tools_respects_agent_selection() -> None:
    names = resolve_hotspot_tool_names(
        ["hotspot_fact_lookup", "sector_heatmap_lookup"],
        query="机器人板块在全市场热力图里排第几？",
        slots={},
    )
    assert "hotspot_signal_lookup" not in names
    assert "sector_heatmap_lookup" in names


def test_resolve_hotspot_stock_codes_from_query_and_slots() -> None:
    codes = resolve_hotspot_stock_codes(
        query="看看300308最近公告",
        slots={"stock_code": "000001"},
        tool_stock_codes="",
    )
    assert "300308" in codes.split(",")
    assert "000001" in codes.split(",")
