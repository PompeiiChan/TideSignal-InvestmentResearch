"""Runtime valuation profile lookup via Tencent realtime quotes."""

from __future__ import annotations

import logging
from typing import Any

from ...integrations.market_data.stock_code_resolver import format_ticker, resolve_stock_code
from ...integrations.market_data.tencent_quote_client import fetch_quote_snapshot

logger = logging.getLogger(__name__)


def _fmt_metric(value: float | None, *, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if suffix:
        return f"{value}{suffix}"
    return str(value)


def lookup_valuation_profile(
    *,
    stock_name: str = "",
    stock_code: str = "",
    analysis_dimension: str = "估值判断",
    **_extra: Any,
) -> dict[str, Any]:
    """Return structured valuation snapshot (price, PE TTM, PB, market cap)."""
    resolved_code, resolved_name = resolve_stock_code(stock_name, stock_code)
    if not resolved_code:
        return {
            "tool": "valuation_profile_lookup",
            "found": False,
            "analysis_dimension": analysis_dimension,
            "valuation": None,
            "source": "",
            "data_origin": "",
            "is_mock": False,
            "notes": "无法解析股票代码，估值工具跳过",
        }

    try:
        snapshot = fetch_quote_snapshot(resolved_code, stock_name=resolved_name or stock_name)
    except Exception as exc:
        logger.warning("Tencent quote lookup failed for %s: %s", resolved_code, exc)
        snapshot = None

    if snapshot is None:
        return {
            "tool": "valuation_profile_lookup",
            "found": False,
            "analysis_dimension": analysis_dimension,
            "valuation": None,
            "source": "https://qt.gtimg.cn/",
            "data_origin": "tencent_quote_api",
            "is_mock": False,
            "notes": "腾讯行情 API 未返回可用估值数据",
        }

    ticker = format_ticker(resolved_code)
    valuation = {
        "stock_name": snapshot.get("stock_name") or resolved_name or stock_name,
        "ticker": ticker,
        "price": _fmt_metric(snapshot.get("price"), suffix="元"),
        "pe_ttm": _fmt_metric(snapshot.get("pe_ttm")),
        "pb": _fmt_metric(snapshot.get("pb")),
        "market_cap": _fmt_metric(snapshot.get("market_cap_yi"), suffix="亿元"),
        "change_pct": _fmt_metric(snapshot.get("change_pct"), suffix="%"),
        "as_of": "实时行情",
    }
    return {
        "tool": "valuation_profile_lookup",
        "found": True,
        "analysis_dimension": analysis_dimension,
        "valuation": valuation,
        "source": str(snapshot.get("source", "https://qt.gtimg.cn/")),
        "data_origin": "tencent_quote_api",
        "is_mock": False,
        "notes": "结构化估值画像，源自腾讯财经实时行情",
    }
