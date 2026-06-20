"""A-share trading day helpers (weekends + exchange holidays)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .a_share_holidays import is_exchange_holiday

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

_EXPLICIT_DATE_FULL_RE = re.compile(
    r"(?P<y>20\d{2})\s*[-年/.]\s*(?P<m>\d{1,2})\s*[-月/.]\s*(?P<d>\d{1,2})\s*日?",
    re.IGNORECASE,
)
_EXPLICIT_DATE_MD_RE = re.compile(
    r"(?P<m>\d{1,2})\s*月\s*(?P<d>\d{1,2})\s*[日号]?",
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


def is_trading_day(d: date) -> bool:
    """True when d is a weekday and not a statutory exchange holiday."""
    return d.weekday() < 5 and not is_exchange_holiday(d)


def rollback_to_last_trading_day(d: date) -> date:
    """Walk backward to the most recent trading day on or before d."""
    cursor = d
    while not is_trading_day(cursor):
        cursor -= timedelta(days=1)
    return cursor


def compute_trading_day_meta(d: date) -> tuple[str, bool]:
    """Return (last_trading_day_iso, is_current_date_trading_day)."""
    if is_trading_day(d):
        return d.isoformat(), True
    last_day = rollback_to_last_trading_day(d)
    return last_day.isoformat(), False


def calendar_today(*, timezone: str = "Asia/Shanghai") -> date:
    now = datetime.now(ZoneInfo(timezone))
    return now.date()


def resolve_default_trade_date(*, timezone: str = "Asia/Shanghai") -> str:
    """Default trade_date for market tools when caller omits it."""
    today = calendar_today(timezone=timezone)
    last_trading_day, _ = compute_trading_day_meta(today)
    return last_trading_day


def _valid_calendar_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_explicit_trade_date(query: str, *, default_year: int | None = None) -> str | None:
    """Parse explicit calendar dates like 2026-06-18 or 6月18号 from user text."""
    haystack = query.strip()
    if not haystack:
        return None

    match = _EXPLICIT_DATE_FULL_RE.search(haystack)
    if match:
        parsed = _valid_calendar_date(
            int(match.group("y")),
            int(match.group("m")),
            int(match.group("d")),
        )
        return parsed.isoformat() if parsed else None

    match = _EXPLICIT_DATE_MD_RE.search(haystack)
    if match:
        year = default_year or calendar_today().year
        parsed = _valid_calendar_date(year, int(match.group("m")), int(match.group("d")))
        return parsed.isoformat() if parsed else None

    return None


def resolve_trade_date_label(
    *,
    trade_date: str = "",
    time_range: str = "",
    timezone: str = "Asia/Shanghai",
) -> str:
    """Pick the trade_date label for market tools from params or system default."""
    explicit = trade_date.strip() or parse_explicit_trade_date(time_range)
    if explicit:
        return explicit
    return resolve_default_trade_date(timezone=timezone)


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
    is_current_trading_day: bool,
    current_date: str = "",
) -> dict[str, Any]:
    """Deterministic slot enrichment for trading-day phrasing (Plan B)."""
    enriched = dict(slots)
    default_year: int | None = None
    if current_date and len(current_date) >= 4:
        try:
            default_year = int(current_date[:4])
        except ValueError:
            default_year = None

    explicit_date = parse_explicit_trade_date(query, default_year=default_year)
    if not explicit_date:
        for key in ("trade_date", "time_range"):
            candidate = str(enriched.get(key, "")).strip()
            if candidate and _EXPLICIT_DATE_FULL_RE.search(candidate):
                explicit_date = parse_explicit_trade_date(candidate, default_year=default_year)
                break
            if candidate and _EXPLICIT_DATE_MD_RE.search(candidate):
                explicit_date = parse_explicit_trade_date(candidate, default_year=default_year)
                break
            if candidate and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", candidate):
                explicit_date = candidate
                break

    if explicit_date:
        enriched["trade_date"] = explicit_date
        enriched["time_range"] = explicit_date
        if not is_trading_day(date.fromisoformat(explicit_date)):
            enriched["trade_date_note"] = (
                f"{explicit_date} 非 A 股交易日；行情口径以最近可用收盘日为准"
            )
        return enriched

    explicit_trading = query_requests_trading_day(query)
    recent_session = query_requests_recent_session(query)
    time_range = str(enriched.get("time_range", "")).strip()
    today_is_trading = is_current_trading_day

    if explicit_trading or time_range in _TRADING_SLOT_TIME_RANGES:
        enriched["time_range"] = "近一交易日"
        enriched["trade_date"] = last_trading_day
        return enriched

    if recent_session and not today_is_trading and not time_range:
        enriched["time_range"] = "近一交易日"
        enriched["trade_date"] = last_trading_day
    elif recent_session and not today_is_trading and time_range in _TRADING_SLOT_TIME_RANGES:
        enriched["trade_date"] = last_trading_day
    return enriched


def apply_tool_trading_defaults(
    tool_params: dict[str, Any],
    *,
    slots: dict[str, Any],
    query: str,
    last_trading_day: str,
    is_current_trading_day: bool,
    current_date: str = "",
) -> dict[str, Any]:
    """Merge slot trade_date into tool_call params for market tools."""
    merged_slots = enrich_trading_slots(
        query,
        {**slots, **tool_params},
        last_trading_day=last_trading_day,
        is_current_trading_day=is_current_trading_day,
        current_date=current_date,
    )
    params = dict(tool_params)
    trade_date = str(merged_slots.get("trade_date", "")).strip()
    time_range = str(merged_slots.get("time_range", "")).strip()
    if trade_date:
        params["trade_date"] = trade_date
    if time_range:
        params["time_range"] = time_range
    elif not params.get("time_range"):
        params["time_range"] = "近一交易日"
    return params
