"""Detect compound queries that require multiple sub-agents."""

from __future__ import annotations

import re
from typing import Any

from .scenario_return import is_scenario_return_query

_INDUSTRY_FUNDAMENTAL_RE = re.compile(
    r"行业|板块|赛道|细分|值得看好|投资价值|整体逻辑|逻辑是什么|哪些分类|重点关注|"
    r"哪些公司|可关注|龙头|基本面|产业",
    re.IGNORECASE,
)
_MARKET_HEAT_DATA_RE = re.compile(
    r"热度|成交额|交易量|成交量|换手|量能|资金|景气|行情怎么样|市场表现|交易活跃",
    re.IGNORECASE,
)
_INDUSTRY_NAME_RE = re.compile(r"([\u4e00-\u9fff]{2,10})行业")

_COMPOUND_ROUTE_SEQUENCE = ("stock_analysis_agent", "data_query_agent")


def extract_industry_label(query: str, slots: dict[str, Any] | None = None) -> str:
    """Best-effort industry label for data-query tools."""
    slots = slots or {}
    for key in ("industry", "topic", "stock_name"):
        value = str(slots.get(key, "")).strip()
        if value:
            return value
    match = _INDUSTRY_NAME_RE.search(query)
    if match:
        return f"{match.group(1)}行业"
    return ""


def resolve_compound_route_targets(
    query: str,
    *,
    intent_id: str = "",
    slots: dict[str, Any] | None = None,
    candidate_intents: list[dict[str, Any]] | None = None,
) -> list[str] | None:
    """Return sequential route targets for industry fundamentals + market heat queries."""
    slots = slots or {}
    haystack = query.strip()
    if not haystack:
        return None
    if is_scenario_return_query(haystack) or slots.get("scenario_return_mode"):
        return None
    if intent_id in {"prediction_request", "chit_chat", "unknown", "fallback_response"}:
        return None

    has_fundamentals = bool(_INDUSTRY_FUNDAMENTAL_RE.search(haystack))
    has_market_heat = bool(_MARKET_HEAT_DATA_RE.search(haystack))

    intent_ids = {
        str(item.get("intent_id", ""))
        for item in (candidate_intents or [])
        if isinstance(item, dict)
    }
    has_stock_intent = "stock_analysis" in intent_ids or intent_id == "stock_analysis"
    has_data_intent = "data_query" in intent_ids or intent_id == "data_query"

    if has_fundamentals and has_market_heat:
        return list(_COMPOUND_ROUTE_SEQUENCE)

    if has_fundamentals and has_stock_intent and has_data_intent:
        return list(_COMPOUND_ROUTE_SEQUENCE)

    return None


def enrich_slots_for_compound(query: str, slots: dict[str, Any]) -> dict[str, Any]:
    """Ensure industry slot is present for the data-query phase."""
    enriched = dict(slots)
    industry = extract_industry_label(query, enriched)
    if industry and not str(enriched.get("industry", "")).strip():
        enriched["industry"] = industry
    if industry and not str(enriched.get("topic", "")).strip():
        enriched["topic"] = industry
    if not str(enriched.get("metric", "")).strip() and _MARKET_HEAT_DATA_RE.search(query):
        enriched["metric"] = "涨幅排行"
    if not str(enriched.get("time_range", "")).strip():
        enriched["time_range"] = "近一交易日"
    return enriched
