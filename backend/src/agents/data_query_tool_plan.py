"""Dynamic data-query tool orchestration with whitelist and rule fallback."""

from __future__ import annotations

import re

from .heatmap_intent import wants_sector_heatmap

DATA_QUERY_TOOL_WHITELIST: frozenset[str] = frozenset(
    {
        "market_ranking_lookup",
        "sector_heatmap_lookup",
        "local_return_calculator",
    }
)

_HEATMAP_KEYWORD_RE = re.compile(
    r"热力图|heatmap|板块全景|行业全景|板块地图|行业板块热|板块热力|A股行业板块",
    re.IGNORECASE,
)
_RANKING_KEYWORD_RE = re.compile(
    r"排行|涨幅|跌幅|领涨|领跌|成分股|涨了多少|跌了多少|板块表现|热度|成交额|交易量|成交量",
    re.IGNORECASE,
)
_DUAL_INTENT_RE = re.compile(r"顺便|同时|以及|还有|再看看|另外", re.IGNORECASE)


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


def _query_wants_ranking(query: str, slots: dict) -> bool:
    if _RANKING_KEYWORD_RE.search(query):
        return True
    return bool(str(slots.get("industry", "")).strip())


def _is_heatmap_only_query(query: str, slots: dict) -> bool:
    """True when the user asks for a heatmap view without an explicit ranking ask."""
    if not wants_sector_heatmap(query) and not _HEATMAP_KEYWORD_RE.search(query):
        return False
    if _DUAL_INTENT_RE.search(query):
        return False
    return not _query_wants_ranking(query, slots)


def _apply_heatmap_only_filter(names: list[str], *, query: str, slots: dict) -> list[str]:
    if not _is_heatmap_only_query(query, slots):
        return names
    if "sector_heatmap_lookup" not in names:
        return names
    return ["sector_heatmap_lookup"]


def _augment_heatmap_tool(names: list[str], *, query: str) -> list[str]:
    augmented = list(names)
    if _HEATMAP_KEYWORD_RE.search(query) and "sector_heatmap_lookup" not in augmented:
        augmented.append("sector_heatmap_lookup")
    return augmented


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
        if _query_wants_ranking(query, slots):
            valid.append("market_ranking_lookup")
        if not valid:
            valid = ["market_ranking_lookup"]
        return _apply_heatmap_only_filter(_dedupe(valid), query=query, slots=slots)

    if agent_specified:
        valid = _augment_heatmap_tool(valid, query=query)
        return _apply_heatmap_only_filter(_dedupe(valid), query=query, slots=slots)

    valid = _augment_heatmap_tool(valid, query=query)
    if _query_wants_ranking(query, slots) and "market_ranking_lookup" not in valid:
        valid.append("market_ranking_lookup")

    filtered = _apply_heatmap_only_filter(_dedupe(valid), query=query, slots=slots)
    return filtered or ["market_ranking_lookup"]
