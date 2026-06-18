"""Dynamic hotspot tool orchestration (fact/signal + optional market heat tools)."""

from __future__ import annotations

import re

HOTSPOT_TOOL_WHITELIST: frozenset[str] = frozenset(
    {
        "hotspot_fact_lookup",
        "hotspot_signal_lookup",
        "market_ranking_lookup",
        "sector_heatmap_lookup",
    }
)

_BASE_TOOLS = ("hotspot_fact_lookup", "hotspot_signal_lookup")

_MARKET_HEAT_RE = re.compile(
    r"热度|资金|景气|板块表现|市场表现|炒什么|火不火|有多火|涨幅|领涨|轮动|热力|行情怎么样",
    re.IGNORECASE,
)
_HEATMAP_RE = re.compile(
    r"热力图|板块全景|全景|板块地图|在全市场|全市场.*热|A股.*热",
    re.IGNORECASE,
)


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
    return [name for name in requested if name in HOTSPOT_TOOL_WHITELIST]


def wants_market_ranking(query: str, slots: dict | None = None) -> bool:
    slots = slots or {}
    if _MARKET_HEAT_RE.search(query):
        return True
    if str(slots.get("industry", "")).strip():
        return True
    return bool(str(slots.get("topic", "")).strip() and any(token in query for token in ("公司", "分类", "赛道", "标的", "关注")))


def wants_sector_heatmap(query: str) -> bool:
    if _HEATMAP_RE.search(query):
        return True
    return bool("在全市场" in query and "热" in query)


def ranking_industry_param(*, query: str, slots: dict | None = None) -> str:
    """Pick Eastmoney board keyword from slots/query."""
    slots = slots or {}
    for key in ("industry", "topic"):
        value = str(slots.get(key, "")).strip()
        if value:
            return value
    for match in re.finditer(r"([\u4e00-\u9fff]{2,8})(?:行业|概念|板块)", query):
        return match.group(0)
    return ""


def resolve_hotspot_tool_names(
    requested: list[str] | None,
    *,
    query: str,
    slots: dict | None = None,
    execution_plan: dict | None = None,
) -> list[str]:
    """Merge base hotspot tools with market heat tools when the query needs them."""
    _ = execution_plan
    slots = slots or {}
    names = list(_BASE_TOOLS)
    names.extend(_filter_whitelisted(requested))

    if wants_market_ranking(query, slots):
        names.append("market_ranking_lookup")
    if wants_sector_heatmap(query):
        names.append("sector_heatmap_lookup")

    return _dedupe([name for name in names if name in HOTSPOT_TOOL_WHITELIST])
