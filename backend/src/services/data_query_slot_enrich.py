"""Rule-based slot enrichment for data_query before clarification."""

from __future__ import annotations

import re
from typing import Any

from ..agents.heatmap_intent import wants_sector_heatmap

DEFAULT_TIME_RANGE = "近一交易日"
DEFAULT_MARKET = "A股"
METRIC_HEATMAP = "行业板块热力图"
METRIC_RANKING = "涨幅排行"
METRIC_TURNOVER_RANKING = "成交额排行"

_RANKING_WITH_SECTOR_RE = re.compile(
    r"(?:涨幅|涨跌|排行|前\s*\d+|Top\s*\d+).*(?:板块|行业)|(?:板块|行业).*(?:涨幅|涨跌|排行|前\s*\d+|Top\s*\d+)",
    re.IGNORECASE,
)
_RANKING_GENERAL_RE = re.compile(
    r"涨幅|涨跌|排行|前\s*\d+|Top\s*\d+|领涨|领跌|前五|前十|前\d+",
    re.IGNORECASE,
)
_TURNOVER_RE = re.compile(r"成交额|成交量|交易量|换手|量能", re.IGNORECASE)
_SECTOR_MARKET_RE = re.compile(r"行业板块|板块涨幅|A股板块", re.IGNORECASE)
_VAGUE_DATA_QUERY_RE = re.compile(
    r"^(帮我)?(查一下|查询|看看)?数据[吗？?]?$|^(帮我)?查一下$",
    re.IGNORECASE,
)


def _slot_has_value(slots: dict[str, Any], key: str) -> bool:
    value = slots.get(key)
    if value is None:
        return False
    return bool(str(value).strip())


def _apply(slots: dict[str, Any], key: str, value: str, applied: list[str]) -> None:
    if _slot_has_value(slots, key):
        return
    slots[key] = value
    if key not in applied:
        applied.append(key)


def _infer_metric(query: str) -> str | None:
    normalized = query.strip()
    if not normalized or _VAGUE_DATA_QUERY_RE.search(normalized):
        return None
    if wants_sector_heatmap(normalized):
        return METRIC_HEATMAP
    if _RANKING_WITH_SECTOR_RE.search(normalized):
        return METRIC_RANKING
    if _RANKING_GENERAL_RE.search(normalized):
        return METRIC_RANKING
    if _TURNOVER_RE.search(normalized):
        return METRIC_TURNOVER_RANKING
    return None


def enrich_data_query_slots(
    query: str,
    slots: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Fill empty data_query slots from query keywords; never overwrite LLM values."""
    enriched = dict(slots)
    applied: list[str] = []

    metric = _infer_metric(query)
    if metric:
        _apply(enriched, "metric", metric, applied)

    if not _slot_has_value(enriched, "time_range"):
        _apply(enriched, "time_range", DEFAULT_TIME_RANGE, applied)

    if _SECTOR_MARKET_RE.search(query):
        _apply(enriched, "market", DEFAULT_MARKET, applied)

    return enriched, applied


def build_data_query_slot_enrich_trace(
    enriched_slots: dict[str, Any],
    applied_keys: list[str],
) -> dict[str, Any]:
    """Trace payload for slot_extraction output."""
    return {
        "applied_keys": applied_keys,
        "metric": enriched_slots.get("metric"),
        "time_range": enriched_slots.get("time_range"),
        "market": enriched_slots.get("market"),
    }


def filter_missing_after_data_query_enrich(
    missing_slots: list[str],
    enriched_slots: dict[str, Any],
) -> list[str]:
    """Drop missing slot names that enrich filled with a concrete value."""
    return [
        name
        for name in missing_slots
        if not _slot_has_value(enriched_slots, name)
    ]
