"""Authoritative system time for LLM prompts and quality checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from ..settings import AppSettings, get_settings
from .trading_calendar import compute_trading_day_meta


def _now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().timezone))


@dataclass(frozen=True)
class SystemTimeContext:
    """Trusted timeline injected into prompts; overrides model calendar assumptions."""

    current_date: str
    timezone: str
    source: str
    last_trading_day: str = field(init=False)
    is_trading_day: bool = field(init=False)

    def __post_init__(self) -> None:
        parsed = date.fromisoformat(self.current_date)
        last_trading_day, is_trading_day = compute_trading_day_meta(parsed)
        object.__setattr__(self, "last_trading_day", last_trading_day)
        object.__setattr__(self, "is_trading_day", is_trading_day)

    def prompt_block(self) -> str:
        trading_lines = [
            f"- last_trading_day: {self.last_trading_day}",
            f"- is_trading_day: {'true' if self.is_trading_day else 'false'}",
        ]
        if not self.is_trading_day:
            trading_lines.append(
                f"- 交易日口径：当前日历日 {self.current_date} 非 A 股交易日；"
                f"用户问「今天/刚刚/最近一个交易日/昨日收盘」及盘面/热点/行情时，"
                f"时间锚点必须用 last_trading_day（{self.last_trading_day}），"
                "不得把 current_date 写成交易日热点日期。"
            )
        else:
            trading_lines.append(
                "- 交易日口径：current_date 即当日交易日；若用户明确问「上一交易日」，"
                f"须回退到前一开市日，不得与 {self.current_date} 混用。"
            )
        trading_block = "\n".join(trading_lines)
        return (
            "【系统时间（权威，优先于你内置的日历常识）】\n"
            f"- current_date: {self.current_date}\n"
            f"- timezone: {self.timezone}\n"
            f"{trading_block}\n"
            "- scenario: 本地投研演示环境；知识库中已入库的财报、研报与热点文档均视为在该日期前可查阅的有效材料。\n"
            "- 回答与质检时：不得仅凭“当前尚未到某年/某报告未发布”否定知识库片段；"
            "文档 time_period（如 2025A、2026Q1）表示数据口径，不是幻觉。"
        )

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "current_date": self.current_date,
            "last_trading_day": self.last_trading_day,
            "is_trading_day": self.is_trading_day,
            "timezone": self.timezone,
            "source": self.source,
        }


def resolve_system_time(settings: AppSettings | None = None) -> SystemTimeContext:
    """Resolve reference date from REFERENCE_DATE or server clock in configured timezone."""
    cfg = settings or get_settings()
    timezone = cfg.timezone.strip() or "Asia/Shanghai"
    configured = cfg.reference_date.strip()
    if configured:
        try:
            parsed = date.fromisoformat(configured)
        except ValueError as exc:
            raise ValueError(
                f"REFERENCE_DATE 格式无效：{configured!r}，请使用 YYYY-MM-DD"
            ) from exc
        return SystemTimeContext(
            current_date=parsed.isoformat(),
            timezone=timezone,
            source="REFERENCE_DATE",
        )

    now = _now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo(timezone))
    else:
        now = now.astimezone(ZoneInfo(timezone))
    return SystemTimeContext(
        current_date=now.date().isoformat(),
        timezone=timezone,
        source="server_clock",
    )
