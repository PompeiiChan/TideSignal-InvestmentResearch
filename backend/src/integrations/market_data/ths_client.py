"""Tonghuashun (10jqka) hotspot signal client.

Adapted from simonlin1212/a-stock-data SKILL.md §3.1 (Apache-2.0).
"""

from __future__ import annotations

from typing import Any

import requests

from ...services.trading_calendar import resolve_default_trade_date

THS_HOT_URL_TEMPLATE = (
    "http://zx.10jqka.com.cn/event/api/getharden/"
    "date/{trade_date}/orderby/date/orderway/desc/charset/GBK/"
)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "Chrome/117.0.0.0 Safari/537.36"
)


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _keyword_variants(needle: str) -> list[str]:
    variants: list[str] = []
    for candidate in (needle, needle.replace("行业", ""), needle.replace("概念", ""), needle.replace("板块", "")):
        token = candidate.strip()
        if token and token not in variants:
            variants.append(token)
    return variants


def _row_matches_keywords(row: dict[str, Any], needles: list[str]) -> bool:
    haystack = " ".join(
        [
            str(row.get("reason", "")),
            str(row.get("stock_name", "")),
            str(row.get("market", "")),
        ]
    )
    return any(token and token in haystack for token in needles)


def fetch_ths_hot_stocks(
    *,
    trade_date: str | None = None,
    keyword: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Fetch same-day strong stocks with editorial reason tags from THS."""
    resolved_date = trade_date or resolve_default_trade_date()
    url = THS_HOT_URL_TEMPLATE.format(trade_date=resolved_date)
    response = requests.get(url, headers={"User-Agent": UA}, timeout=15)
    response.raise_for_status()
    payload = response.json()
    if payload.get("errocode", 0) != 0:
        raise RuntimeError(f"同花顺热点错误: {payload.get('errormsg', '')}")

    raw_rows = payload.get("data") or []
    stocks: list[dict[str, Any]] = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "")).zfill(6)
        name = str(item.get("name", ""))
        reason = str(item.get("reason", "")).strip()
        stocks.append(
            {
                "code": code,
                "stock_name": name,
                "reason": reason,
                "pct_change": _safe_float(item.get("zhangfu")),
                "close_price": _safe_float(item.get("close")),
                "turnover_amount": _safe_float(item.get("chengjiaoe")),
                "turnover_rate": _safe_float(item.get("huanshou")),
                "market": str(item.get("market", "")),
            }
        )

    needle = keyword.strip()
    keyword_variants = _keyword_variants(needle) if needle else []
    filtered = stocks
    topic_matched = True
    if needle:
        matched = [row for row in stocks if _row_matches_keywords(row, keyword_variants)]
        if matched:
            filtered = matched
            topic_matched = True
        else:
            filtered = []
            topic_matched = False

    filtered.sort(key=lambda row: row.get("pct_change") or 0.0, reverse=True)
    top = filtered[: max(limit, 1)]

    themes: list[str] = []
    seen: set[str] = set()
    for row in top:
        for tag in _split_reason_tags(str(row.get("reason", ""))):
            if tag not in seen:
                seen.add(tag)
                themes.append(tag)

    return {
        "trade_date": resolved_date,
        "total_available": len(stocks),
        "matched_count": len(filtered),
        "topic_matched": topic_matched,
        "stocks": top,
        "themes": themes[:15],
        "keyword": needle,
    }


def _split_reason_tags(reason: str) -> list[str]:
    if not reason:
        return []
    normalized = reason.replace("＋", "+").replace(";", "+").replace("，", "+")
    return [part.strip() for part in normalized.split("+") if part.strip()]
