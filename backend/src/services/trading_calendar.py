"""A-share trading day helpers (weekend rollback v1; holidays later)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

_TRADING_DAY_QUERY_RE = re.compile(
    r"刚刚过去的?这个?交易日|上一个交易日|上个交易日|前一交易日|前个交易日|"
    r"最近一个交易日|近一交易日|最近交易日|昨日收盘|昨天收盘|上个交易日收盘|"
    r"上一交易日收盘|刚过去的交易日",
    re.IGNORECASE,
)

_RECENT_SESSION_RE = re.compile(
    r"今天|今日|当天|当日|盘面|刚刚|最新|当前",
    re.IGNORECASE,
)

_TRADING_SLOT_TIME_RANGES = frozenset(
    {
        "近一交易日",
        "上一交易日",
        "最近一个交易日",
        "最近交易日",
        "昨日收盘",
        "昨天收盘",
    }
)


def compute_trading_day_meta(d: date) -> tuple[str, bool]:
    """Return (last_trading_day_iso, is_current_date_trading_day)."""
    is_trading = d.weekday() < 5
    if is_trading:
        return d.isoformat(), True
    cursor = d
    while cursor.weekday() >= 5:
        cursor -= timedelta(days=1)
    return cursor.isoformat(), False


def calendar_today(*, timezone: str = "Asia/Shanghai") -> date:
    now = datetime.now(ZoneInfo(timezone))
    return now.date()


def resolve_default_trade_date(*, timezone: str = "Asia/Shanghai") -> str:
    """Default trade_date for market tools when caller omits it."""
    today = calendar_today(timezone=timezone)
    last_trading_day, _ = compute_trading_day_meta(today)
    return last_trading_day


def query_requests_trading_day(query: str) -> bool:
    haystack = query.strip()
    if not haystack:
        return False
    return bool(_TRADING_DAY_QUERY_RE.search(haystack))


def query_requests_recent_session(query: str) -> bool:
    haystack = query.strip()
    if not haystack:
        return False
    return bool(_RECENT_SESSION_RE.search(haystack))


def enrich_trading_slots(
    query: str,
    slots: dict[str, Any],
    *,
    last_trading_day: str,
    is_trading_day: bool,
) -> dict[str, Any]:
    """Deterministic slot enrichment for trading-day phrasing (Plan B)."""
    enriched = dict(slots)
    explicit_trading = query_requests_trading_day(query)
    recent_session = query_requests_recent_session(query)
    time_range = str(enriched.get("time_range", "")).strip()

    if explicit_trading or time_range in _TRADING_SLOT_TIME_RANGES:
        enriched["time_range"] = "近一交易日"
        enriched["trade_date"] = last_trading_day
        return enriched

    if recent_session and not is_trading_day and not time_range:
        enriched["time_range"] = "近一交易日"
        enriched["trade_date"] = last_trading_day
    return enriched
