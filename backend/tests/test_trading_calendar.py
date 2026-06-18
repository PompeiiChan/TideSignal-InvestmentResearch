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
        is_trading_day=False,
    )
    assert slots["time_range"] == "近一交易日"
    assert slots["trade_date"] == "2026-06-12"


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
