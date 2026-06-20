"""Tests for data_query slot rule enrichment."""

from __future__ import annotations

from backend.src.services.data_query_slot_enrich import (
    DEFAULT_TIME_RANGE,
    METRIC_HEATMAP,
    METRIC_RANKING,
    METRIC_TURNOVER_RANKING,
    enrich_data_query_slots,
    filter_missing_after_data_query_enrich,
)


def test_r1_heatmap_metric() -> None:
    slots, applied = enrich_data_query_slots("行业板块热力图", {})
    assert slots["metric"] == METRIC_HEATMAP
    assert "metric" in applied


def test_r2_ranking_with_sector() -> None:
    slots, applied = enrich_data_query_slots("今天涨幅前10的行业板块", {})
    assert slots["metric"] == METRIC_RANKING
    assert slots["time_range"] == DEFAULT_TIME_RANGE
    assert slots["market"] == "A股"
    assert "metric" in applied
    assert "time_range" in applied


def test_r3_ranking_general() -> None:
    slots, applied = enrich_data_query_slots("半导体涨幅前五", {})
    assert slots["metric"] == METRIC_RANKING
    assert "metric" in applied


def test_r4_turnover_metric() -> None:
    slots, applied = enrich_data_query_slots("行业板块成交额排行", {})
    assert slots["metric"] == METRIC_RANKING
    slots2, applied2 = enrich_data_query_slots("今日成交量最大的板块", {})
    assert slots2["metric"] == METRIC_TURNOVER_RANKING
    assert "metric" in applied2


def test_r5_default_time_range() -> None:
    slots, applied = enrich_data_query_slots("机器人板块表现", {"metric": "涨幅排行"})
    assert slots["time_range"] == DEFAULT_TIME_RANGE
    assert "time_range" in applied


def test_r7_market_sector() -> None:
    slots, applied = enrich_data_query_slots("A股板块涨幅情况", {"metric": "涨幅排行"})
    assert slots.get("market") == "A股"
    assert "market" in applied


def test_does_not_overwrite_existing_slots() -> None:
    original = {"metric": "自定义指标", "time_range": "2026Q1", "market": "港股"}
    slots, applied = enrich_data_query_slots("今天涨幅前10的行业板块", original)
    assert slots["metric"] == "自定义指标"
    assert slots["time_range"] == "2026Q1"
    assert slots["market"] == "港股"
    assert applied == []


def test_vague_query_no_metric_enrich() -> None:
    slots, applied = enrich_data_query_slots("帮我查一下数据", {})
    assert "metric" not in slots
    assert "metric" not in applied
    assert slots["time_range"] == DEFAULT_TIME_RANGE


def test_industry_only_still_no_metric() -> None:
    slots, applied = enrich_data_query_slots("白酒", {"industry": "白酒"})
    assert "metric" not in slots
    assert "metric" not in applied


def test_filter_missing_after_enrich() -> None:
    filtered = filter_missing_after_data_query_enrich(
        ["metric", "time_range"],
        {"metric": "涨幅排行", "time_range": "近一交易日"},
    )
    assert filtered == []
