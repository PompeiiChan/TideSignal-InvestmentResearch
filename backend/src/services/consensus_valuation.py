"""Build scenario return bands from institutional EPS × PE consensus."""

from __future__ import annotations

from typing import Any

from ..integrations.market_data.em_report_consensus_client import fetch_em_report_consensus
from ..integrations.market_data.ths_worth_client import fetch_ths_worth_consensus
from .earnings_forecast import extract_earnings_forecast

_SCENARIO_YEARS: dict[str, int] = {
    "bear": 2026,
    "base": 2027,
    "bull": 2028,
}
_SCENARIO_LABELS: dict[str, str] = {
    "bear": "保守（2026E）",
    "base": "中性（2027E）",
    "bull": "乐观（2028E）",
}
_EPS_KEYS: dict[str, str] = {
    "bear": "low",
    "base": "mid",
    "bull": "high",
}
_PE_KEYS: dict[str, str] = {
    "bear": "low",
    "base": "mid",
    "bull": "high",
}
_REFERENCE_YEAR = 2025
_LOW_COVERAGE_THRESHOLD = 3


def _year_data(years: dict[str, Any], year: int) -> dict[str, Any] | None:
    direct = years.get(str(year))
    if isinstance(direct, dict):
        return direct
    for payload in years.values():
        if isinstance(payload, dict) and int(payload.get("year", 0)) == year:
            return payload
    return None


def _nearest_year_data(years: dict[str, Any], year: int) -> dict[str, Any] | None:
    hit = _year_data(years, year)
    if hit:
        return hit
    available = sorted(
        int(item.get("year", key))
        for key, item in years.items()
        if isinstance(item, dict) and str(item.get("year", key)).isdigit()
    )
    if not available:
        return None
    nearest = min(available, key=lambda item: abs(item - year))
    return _year_data(years, nearest)


def _build_scenario(
    *,
    key: str,
    years: dict[str, Any],
    target_year: int,
    source: dict[str, str],
) -> dict[str, Any] | None:
    year_payload = _nearest_year_data(years, target_year)
    if not year_payload:
        return None
    eps_band = year_payload.get("eps")
    pe_band = year_payload.get("pe")
    if not isinstance(eps_band, dict) or not isinstance(pe_band, dict):
        return None
    eps_key = _EPS_KEYS[key]
    pe_key = _PE_KEYS[key]
    eps = eps_band.get(eps_key)
    pe = pe_band.get(pe_key)
    if eps is None or pe is None:
        return None
    try:
        eps_f = float(eps)
        pe_f = float(pe)
    except (TypeError, ValueError):
        return None
    if eps_f <= 0 or pe_f <= 0:
        return None
    used_year = int(year_payload.get("year", target_year))
    analyst_count = int(year_payload.get("analyst_count") or 0)
    return {
        "label": _SCENARIO_LABELS[key],
        "forecast_year": used_year,
        "eps": round(eps_f, 4),
        "pe": round(pe_f, 2),
        "target_price": round(eps_f * pe_f, 2),
        "assumption": (
            f"{used_year}E：EPS {_EPS_KEYS[key]} {eps_f} × PE {_PE_KEYS[key]} {pe_f}"
        ),
        "analyst_count": analyst_count,
        "source": dict(source),
    }


def build_consensus_scenarios(
    raw: dict[str, Any],
    *,
    stock_name: str = "",
) -> dict[str, Any]:
    """Normalize THS / Eastmoney consensus payload into bear/base/bull scenarios."""
    years = raw.get("years")
    if not isinstance(years, dict) or not years:
        return {
            "tool": "consensus_valuation_lookup",
            "found": False,
            "stock_name": stock_name,
            "scenarios": {},
            "scenario_order": [],
            "reference_year": _REFERENCE_YEAR,
            "data_origin": raw.get("data_origin", ""),
            "source": str(raw.get("source", "")),
            "notes": str(raw.get("notes", "无一致预期数据")),
        }

    source_meta = {
        "title": (
            "同花顺机构一致预期"
            if raw.get("data_origin") == "ths_worth_consensus"
            else "东财研报一致预期"
        ),
        "origin": str(raw.get("data_origin", "")),
        "path": str(raw.get("source", "")),
        "time_period": f"基准年 {_REFERENCE_YEAR}，情景 2026–2028E",
        "excerpt": "",
        "doc_id": "",
    }
    scenarios: dict[str, dict[str, Any]] = {}
    for key, target_year in _SCENARIO_YEARS.items():
        built = _build_scenario(
            key=key,
            years=years,
            target_year=target_year,
            source=source_meta,
        )
        if built:
            scenarios[key] = built

    analyst_counts = [int(item.get("analyst_count") or 0) for item in scenarios.values()]
    max_analysts = max(analyst_counts) if analyst_counts else 0
    scenario_order = [key for key in ("bear", "base", "bull") if key in scenarios]

    return {
        "tool": "consensus_valuation_lookup",
        "found": bool(scenarios),
        "stock_name": stock_name,
        "scenarios": scenarios,
        "scenario_order": scenario_order,
        "reference_year": int(raw.get("reference_year") or _REFERENCE_YEAR),
        "forecast_years": dict(_SCENARIO_YEARS),
        "low_coverage": max_analysts < _LOW_COVERAGE_THRESHOLD if max_analysts else True,
        "analyst_count": max_analysts,
        "extraction_method": "eps_x_pe_consensus",
        "primary_source": source_meta,
        "data_origin": raw.get("data_origin", ""),
        "source": str(raw.get("source", "")),
        "notes": str(raw.get("notes", "")),
        "formula": "target_price = EPS × PE",
    }


def lookup_consensus_valuation(
    *,
    stock_name: str = "",
    stock_code: str = "",
    current_price: float | None = None,
    rag_hits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """API-first consensus lookup with Eastmoney and KB fallbacks."""
    code = (stock_code or "").zfill(6)
    ths_raw = fetch_ths_worth_consensus(code) if len(code) == 6 else {"found": False}
    if ths_raw.get("found"):
        result = build_consensus_scenarios(ths_raw, stock_name=stock_name)
        if result.get("found"):
            return result

    em_raw = fetch_em_report_consensus(code, current_price=current_price) if len(code) == 6 else {"found": False}
    if em_raw.get("found"):
        result = build_consensus_scenarios(em_raw, stock_name=stock_name)
        if result.get("found"):
            return result

    kb_forecast = extract_earnings_forecast(rag_hits, stock_name=stock_name)
    if kb_forecast.get("found"):
        return {
            **kb_forecast,
            "tool": "consensus_valuation_lookup",
            "data_origin": "local_kb",
            "reference_year": _REFERENCE_YEAR,
            "forecast_years": dict(_SCENARIO_YEARS),
            "formula": "target_price = EPS × PE",
            "notes": "已降级为本地研报摘录",
        }

    return {
        "tool": "consensus_valuation_lookup",
        "found": False,
        "stock_name": stock_name,
        "scenarios": {},
        "scenario_order": [],
        "reference_year": _REFERENCE_YEAR,
        "data_origin": "",
        "source": "",
        "notes": "暂无机构一致预期覆盖，无法构建情景测算",
    }
