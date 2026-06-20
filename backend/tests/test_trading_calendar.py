"""Tests for A-share trading day resolution and slot enrichment."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from src.agents.nodes.hotspot_agent import _apply_hotspot_tool_trading_defaults
from src.services.system_time import SystemTimeContext, resolve_system_time
from src.services.trading_calendar import (
    compute_trading_day_meta,
    enrich_trading_slots,
    is_trading_day,
    parse_explicit_trade_date,
    query_requests_trading_day,
    resolve_default_trade_date,
)
from src.settings import AppSettings


def test_compute_trading_day_meta_weekend() -> None:
    last_day, is_trading = compute_trading_day_meta(date(2026, 6, 14))
    assert last_day == "2026-06-12"
    assert is_trading is False


def test_compute_trading_day_meta_weekday() -> None:
    last_day, is_trading = compute_trading_day_meta(date(2026, 6, 12))
    assert last_day == "2026-06-12"
    assert is_trading is True


def test_system_time_context_includes_last_trading_day() -> None:
    ctx = resolve_system_time(AppSettings(reference_date="2026-06-14", timezone="Asia/Shanghai"))
    assert ctx.current_date == "2026-06-14"
    assert ctx.last_trading_day == "2026-06-12"
    assert ctx.is_trading_day is False
    assert ctx.last_trading_day in ctx.prompt_block()
    assert ctx.to_dict()["last_trading_day"] == "2026-06-12"


def test_enrich_trading_slots_from_query() -> None:
    slots = enrich_trading_slots(
        "刚刚过去的这个交易日，热点分别是什么？",
        {"topic": "A股"},
        last_trading_day="2026-06-12",
        is_current_trading_day=False,
    )
    assert slots["time_range"] == "近一交易日"
    assert slots["trade_date"] == "2026-06-12"


def test_compute_trading_day_meta_dragon_boat_holiday_weekend() -> None:
    """2026-06-20 周六，端午 6/19-21 放假 → 上一交易日 6/18。"""
    last_day, is_trading = compute_trading_day_meta(date(2026, 6, 20))
    assert last_day == "2026-06-18"
    assert is_trading is False


def test_compute_trading_day_meta_dragon_boat_friday() -> None:
    last_day, is_trading = compute_trading_day_meta(date(2026, 6, 19))
    assert last_day == "2026-06-18"
    assert is_trading is False


def test_is_trading_day_excludes_holiday() -> None:
    assert is_trading_day(date(2026, 6, 19)) is False
    assert is_trading_day(date(2026, 6, 18)) is True


def test_parse_explicit_trade_date_month_day() -> None:
    assert parse_explicit_trade_date("我要看6月18号的涨幅排行榜", default_year=2026) == "2026-06-18"


def test_enrich_trading_slots_explicit_date_overrides_recent_session() -> None:
    slots = enrich_trading_slots(
        "帮我查6月18号的涨幅排行榜",
        {"metric": "涨幅排行"},
        last_trading_day="2026-06-19",
        is_current_trading_day=False,
        current_date="2026-06-20",
    )
    assert slots["trade_date"] == "2026-06-18"
    assert slots["time_range"] == "2026-06-18"


def test_enrich_trading_slots_today_on_holiday_weekend() -> None:
    slots = enrich_trading_slots(
        "今天的涨幅排行榜",
        {"metric": "涨幅排行"},
        last_trading_day="2026-06-18",
        is_current_trading_day=False,
        current_date="2026-06-20",
    )
    assert slots["trade_date"] == "2026-06-18"
    assert slots["time_range"] == "近一交易日"


def test_query_requests_trading_day() -> None:
    assert query_requests_trading_day("刚刚过去的这个交易日的热点")
    assert not query_requests_trading_day("5月热点月度复盘")


def test_hotspot_tool_defaults_apply_trade_date() -> None:
    ctx = SystemTimeContext(current_date="2026-06-14", timezone="Asia/Shanghai", source="test")
    tool_params = _apply_hotspot_tool_trading_defaults(
        {"topic": "A股", "time_range": "2026-06"},
        slots={"topic": "A股"},
        query="刚刚过去的这个交易日热点是什么",
        last_trading_day=ctx.last_trading_day,
        is_trading_day=ctx.is_trading_day,
    )
    assert tool_params["time_range"] == "近一交易日"
    assert tool_params["trade_date"] == "2026-06-12"


def test_resolve_default_trade_date_on_weekend(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FixedDateTime:
        @classmethod
        def now(cls, tz: Any) -> Any:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            return datetime(2026, 6, 14, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    monkeypatch.setattr("src.services.trading_calendar.datetime", _FixedDateTime)
    assert resolve_default_trade_date(timezone="Asia/Shanghai") == "2026-06-12"
