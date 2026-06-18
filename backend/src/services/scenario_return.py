"""Scenario return calculator: detect queries and build calculator params from tools/API."""

from __future__ import annotations

import re
from typing import Any

_DEFAULT_SHARE_COUNT = 100
_DEFAULT_FEE_RATE = 0.0003

_SCENARIO_RETURN_RE = re.compile(
    r"预期回报|预期收益|回报率|收益率|能赚多少|赚多少|现在买.*回报|买入.*回报|"
    r"如果.*买.*回报|情景测算|收益测算",
    re.IGNORECASE,
)

_PREDICTION_ONLY_RE = re.compile(
    r"预测.*涨|明天涨|一定涨|目标价[是给多少]|涨到多少|会涨吗",
    re.IGNORECASE,
)


def is_scenario_return_query(query: str) -> bool:
    haystack = query.strip()
    if not haystack:
        return False
    if _PREDICTION_ONLY_RE.search(haystack) and not _SCENARIO_RETURN_RE.search(haystack):
        return False
    return bool(_SCENARIO_RETURN_RE.search(haystack))


def enrich_scenario_return_slots(query: str, slots: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(slots)
    if not is_scenario_return_query(query):
        return enriched
    enriched["scenario_return_mode"] = True
    if not enriched.get("share_count"):
        enriched["share_count"] = _DEFAULT_SHARE_COUNT
    return enriched


def _parse_price(value: str) -> float | None:
    if not value:
        return None
    cleaned = str(value).replace("元", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _valuation_buy_price(valuation_tool: dict[str, Any]) -> float | None:
    valuation = valuation_tool.get("valuation")
    if not isinstance(valuation, dict):
        return None
    return _parse_price(str(valuation.get("price", "")))


def _base_scenario(forecast_tool: dict[str, Any]) -> dict[str, Any] | None:
    scenarios = forecast_tool.get("scenarios")
    if not isinstance(scenarios, dict):
        return None
    for key in ("base", "bear", "bull"):
        scenario = scenarios.get(key)
        if isinstance(scenario, dict) and scenario.get("target_price"):
            return scenario
    for scenario in scenarios.values():
        if isinstance(scenario, dict) and scenario.get("target_price"):
            return scenario
    return None


def build_scenario_return_calculation(
    *,
    valuation_tool: dict[str, Any] | None,
    forecast_tool: dict[str, Any] | None,
    rag_hits: list[dict[str, Any]] | None,
    share_count: int = _DEFAULT_SHARE_COUNT,
    fee_rate: float = _DEFAULT_FEE_RATE,
) -> dict[str, Any] | None:
    """Build local_return_calculator result from live price + consensus EPS×PE scenarios."""
    _ = rag_hits
    if not isinstance(valuation_tool, dict) or not valuation_tool.get("found"):
        return None
    buy_price = _valuation_buy_price(valuation_tool)
    if buy_price is None or buy_price <= 0:
        return None
    if not isinstance(forecast_tool, dict) or not forecast_tool.get("found"):
        return None

    base = _base_scenario(forecast_tool)
    if not base:
        return None
    sell_price = _parse_price(str(base.get("target_price", "")))
    if sell_price is None or sell_price <= 0:
        return None

    from ..agents.tools.return_calculator import compute_return

    calc = compute_return(
        buy_price=buy_price,
        sell_price=sell_price,
        share_count=share_count,
        fee_rate=fee_rate,
    )
    stock_name = ""
    valuation = valuation_tool.get("valuation")
    if isinstance(valuation, dict):
        stock_name = str(valuation.get("stock_name", ""))
    assumption = str(base.get("assumption", "") or forecast_tool.get("notes", ""))
    return {
        **calc,
        "scenario_return_mode": True,
        "stock_name": stock_name,
        "assumption": assumption,
        "buy_price_source": "valuation_profile_lookup",
        "scenario_price_source": str(forecast_tool.get("data_origin") or "consensus_valuation_lookup"),
        "forecast_scenarios": forecast_tool.get("scenarios") if isinstance(forecast_tool, dict) else {},
        "reference_year": forecast_tool.get("reference_year"),
        "low_coverage": forecast_tool.get("low_coverage"),
        "formula": forecast_tool.get("formula", "target_price = EPS × PE"),
    }
