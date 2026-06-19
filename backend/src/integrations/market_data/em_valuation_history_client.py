"""Eastmoney datacenter client for historical PE/PB valuation bands."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .eastmoney_client import em_get
from .stock_code_resolver import format_ticker, normalize_stock_code

_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_REPORT_NAME = "RPT_VALUEANALYSIS_DET"
_REFERER = "https://data.eastmoney.com/"
_MIN_POSITIVE = 0.01


def _shanghai_today() -> datetime:
    return datetime.now(tz=ZoneInfo("Asia/Shanghai"))


def _safe_float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:  # NaN
        return None
    return parsed


def _percentile_rank(current: float, history: list[float]) -> float | None:
    if not history:
        return None
    count_le = sum(1 for item in history if item <= current)
    return round(100 * count_le / len(history), 1)


def _quartile(sorted_values: list[float], fraction: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return round(sorted_values[0], 2)
    index = (len(sorted_values) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    value = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    return round(value, 2)


def _metric_summary(current: float | None, history: list[float]) -> dict[str, Any]:
    if not history:
        return {
            "current": round(current, 2) if current is not None else None,
            "sample_count": 0,
            "percentile": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "min": None,
            "max": None,
        }
    sorted_values = sorted(history)
    return {
        "current": round(current, 2) if current is not None else None,
        "sample_count": len(sorted_values),
        "percentile": _percentile_rank(current, sorted_values) if current is not None else None,
        "p25": _quartile(sorted_values, 0.25),
        "p50": _quartile(sorted_values, 0.50),
        "p75": _quartile(sorted_values, 0.75),
        "min": round(sorted_values[0], 2),
        "max": round(sorted_values[-1], 2),
    }


def _quarter_key(trade_date: str) -> str:
    year = int(trade_date[:4])
    month = int(trade_date[5:7])
    quarter = (month - 1) // 3 + 1
    return f"{year}Q{quarter}"


def _build_quarterly_series(rows: list[dict[str, Any]], *, max_points: int = 12) -> list[dict[str, Any]]:
    by_quarter: dict[str, dict[str, Any]] = {}
    for row in rows:
        trade_date = str(row.get("trade_date", ""))[:10]
        if not trade_date:
            continue
        quarter = _quarter_key(trade_date)
        existing = by_quarter.get(quarter)
        if existing is None or trade_date > str(existing.get("trade_date", "")):
            by_quarter[quarter] = row
    ordered = sorted(by_quarter.values(), key=lambda item: str(item.get("trade_date", "")))
    return ordered[-max_points:]


def _fetch_raw_rows(secu_code: str, *, page_size: int = 800) -> list[dict[str, Any]]:
    params = {
        "reportName": _REPORT_NAME,
        "columns": "SECUCODE,SECURITY_NAME_ABBR,PE_TTM,PE_LAR,PB_MRQ,TRADE_DATE",
        "filter": f'(SECUCODE="{secu_code}")',
        "pageNumber": "1",
        "pageSize": str(page_size),
        "sortTypes": "-1",
        "sortColumns": "TRADE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    response = em_get(
        _DATACENTER_URL,
        params=params,
        headers={"User-Agent": "Mozilla/5.0", "Referer": _REFERER},
        timeout=18,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        return []
    result = payload.get("result") or {}
    data = result.get("data") or []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def fetch_valuation_history(
    stock_code: str,
    *,
    years: int = 3,
    page_size: int = 800,
) -> dict[str, Any]:
    """Return ~3-year PE/PB history summary and quarterly snapshots from Eastmoney."""
    normalized = normalize_stock_code(stock_code)
    if not normalized:
        return {
            "found": False,
            "secu_code": "",
            "source": _DATACENTER_URL,
            "data_origin": "eastmoney_valuation_history",
            "notes": "无法解析股票代码，历史估值跳过",
        }

    secu_code = format_ticker(normalized)
    try:
        raw_rows = _fetch_raw_rows(secu_code, page_size=page_size)
    except Exception as exc:
        return {
            "found": False,
            "secu_code": secu_code,
            "source": _DATACENTER_URL,
            "data_origin": "eastmoney_valuation_history",
            "notes": f"东财历史估值 API 请求失败: {exc}",
        }

    if not raw_rows:
        return {
            "found": False,
            "secu_code": secu_code,
            "source": _DATACENTER_URL,
            "data_origin": "eastmoney_valuation_history",
            "notes": "东财历史估值 API 未返回可用数据",
        }

    cutoff = (_shanghai_today() - timedelta(days=max(int(years), 1) * 365)).strftime("%Y-%m-%d")
    normalized_rows: list[dict[str, Any]] = []
    for item in raw_rows:
        trade_date = str(item.get("TRADE_DATE", ""))[:10]
        if not trade_date or trade_date < cutoff:
            continue
        pe_ttm = _safe_float(item.get("PE_TTM"))
        pb = _safe_float(item.get("PB_MRQ"))
        normalized_rows.append(
            {
                "trade_date": trade_date,
                "pe_ttm": round(pe_ttm, 2) if pe_ttm is not None else None,
                "pb": round(pb, 2) if pb is not None else None,
            }
        )

    if not normalized_rows:
        return {
            "found": False,
            "secu_code": secu_code,
            "source": _DATACENTER_URL,
            "data_origin": "eastmoney_valuation_history",
            "notes": f"近 {years} 年无可用历史估值样本",
        }

    normalized_rows.sort(key=lambda row: str(row.get("trade_date", "")))
    latest = normalized_rows[-1]
    pe_history = [
        float(row["pe_ttm"])
        for row in normalized_rows
        if row.get("pe_ttm") is not None and float(row["pe_ttm"]) > _MIN_POSITIVE
    ]
    pb_history = [
        float(row["pb"])
        for row in normalized_rows
        if row.get("pb") is not None and float(row["pb"]) > _MIN_POSITIVE
    ]

    quarterly_series = _build_quarterly_series(normalized_rows)
    return {
        "found": True,
        "secu_code": secu_code,
        "lookback_years": years,
        "as_of": str(latest.get("trade_date", "")),
        "trading_day_count": len(normalized_rows),
        "pe_ttm": _metric_summary(
            float(latest["pe_ttm"]) if latest.get("pe_ttm") is not None else None,
            pe_history,
        ),
        "pb": _metric_summary(
            float(latest["pb"]) if latest.get("pb") is not None else None,
            pb_history,
        ),
        "quarterly_series": quarterly_series,
        "source": _DATACENTER_URL,
        "data_origin": "eastmoney_valuation_history",
        "notes": (
            f"东财估值分析日频数据，近 {years} 年共 {len(normalized_rows)} 个交易日；"
            "PE 分位仅统计盈利期（PE>0）样本"
        ),
    }
