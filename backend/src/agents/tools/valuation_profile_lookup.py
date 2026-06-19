"""Runtime valuation profile lookup via Tencent realtime quotes + Eastmoney history."""

from __future__ import annotations

import logging
from typing import Any

from ...integrations.market_data.em_valuation_history_client import fetch_valuation_history
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

    valuation_history: dict[str, Any] | None = None
    history_notes = ""
    try:
        history_payload = fetch_valuation_history(resolved_code)
        if history_payload.get("found"):
            valuation_history = history_payload
        else:
            history_notes = str(history_payload.get("notes", "历史估值暂不可用"))
    except Exception as exc:
        logger.warning("Valuation history lookup failed for %s: %s", resolved_code, exc)
        history_notes = f"历史估值拉取失败: {exc}"

    notes = "结构化估值画像：腾讯实时行情"
    if valuation_history:
        notes += " + 东财近 3 年 PE/PB 历史分位"
    elif history_notes:
        notes += f"；{history_notes}"

    return {
        "tool": "valuation_profile_lookup",
        "found": True,
        "analysis_dimension": analysis_dimension,
        "valuation": valuation,
        "valuation_history": valuation_history,
        "source": str(snapshot.get("source", "https://qt.gtimg.cn/")),
        "data_origin": "tencent_quote_api",
        "is_mock": False,
        "notes": notes,
    }
