"""Dynamic data-query tool orchestration with whitelist and rule fallback."""

from __future__ import annotations

import re

DATA_QUERY_TOOL_WHITELIST: frozenset[str] = frozenset(
    {
        "market_ranking_lookup",
        "sector_heatmap_lookup",
        "local_return_calculator",
    }
)

_HEATMAP_KEYWORD_RE = re.compile(r"热力图|heatmap|板块全景|行业全景|板块地图", re.IGNORECASE)
_RANKING_KEYWORD_RE = re.compile(
    r"排行|涨幅|跌幅|领涨|领跌|成分股|涨了多少|跌了多少|板块表现",
    re.IGNORECASE,
)


def _has_return_calculator_slots(slots: dict) -> bool:
    required = ("buy_price", "sell_price", "share_count")
    return all(key in slots and slots[key] not in (None, "") for key in required)


def _dedupe(names: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _filter_whitelisted(requested: list[str] | None) -> list[str]:
    if not requested:
        return []
    return [name for name in requested if name in DATA_QUERY_TOOL_WHITELIST]


def resolve_data_query_tool_names(
    requested: list[str] | None,
    *,
    query: str,
    slots: dict | None = None,
) -> list[str]:
    """Validate agent-requested tools; calculator is exclusive when slots are complete."""
    slots = slots or {}
    if _has_return_calculator_slots(slots):
        return ["local_return_calculator"]

    valid = _dedupe(_filter_whitelisted(requested))
    agent_specified = bool(valid)

    if not valid:
        valid = []
        if _HEATMAP_KEYWORD_RE.search(query):
            valid.append("sector_heatmap_lookup")
        if _RANKING_KEYWORD_RE.search(query) or str(slots.get("industry", "")).strip():
            valid.append("market_ranking_lookup")
        if not valid:
            valid = ["market_ranking_lookup"]
        return _dedupe(valid)

    if agent_specified:
        return _dedupe(valid)

    if _HEATMAP_KEYWORD_RE.search(query) and "sector_heatmap_lookup" not in valid:
        valid.append("sector_heatmap_lookup")
    if (
        _RANKING_KEYWORD_RE.search(query) or str(slots.get("industry", "")).strip()
    ) and "market_ranking_lookup" not in valid:
        valid.append("market_ranking_lookup")

    return _dedupe(valid) or ["market_ranking_lookup"]
