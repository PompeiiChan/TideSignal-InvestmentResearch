"""Demo daily question quota (visitor + IP limits)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DemoQuotaCounter
from ..settings import AppSettings, get_settings

_VISITOR_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class DemoQuotaExceededError(Exception):
    """Raised when daily demo quota is exhausted."""

    def __init__(
        self,
        message: str,
        *,
        limit: int,
        used: int,
        remaining: int,
        reset_date: str,
    ) -> None:
        super().__init__(message)
        self.limit = limit
        self.used = used
        self.remaining = remaining
        self.reset_date = reset_date


@dataclass(frozen=True)
class DemoQuotaStatus:
    enabled: bool
    limit: int
    used: int
    remaining: int
    reset_date: str
    visitor_id: str = ""


def _today_key(*, timezone: str) -> str:
    return datetime.now(ZoneInfo(timezone)).date().isoformat()


def _normalize_visitor_id(visitor_id: str) -> str:
    cleaned = visitor_id.strip()
    if not cleaned or not _VISITOR_ID_RE.fullmatch(cleaned):
        raise ValueError("无效的 Demo 访客标识")
    return cleaned.lower()


def _ip_hash(client_ip: str) -> str:
    digest = hashlib.sha256(client_ip.strip().encode("utf-8")).hexdigest()
    return digest[:16]


def _quota_key(*, scope: str, identity: str, day: str) -> str:
    return f"{scope}:{identity}:{day}"


async def _get_count(db: AsyncSession, quota_key: str) -> int:
    row = await db.get(DemoQuotaCounter, quota_key)
    return int(row.usage_count) if row is not None else 0


async def _increment(db: AsyncSession, quota_key: str, *, timezone: str) -> int:
    now = datetime.now(ZoneInfo(timezone))
    row = await db.get(DemoQuotaCounter, quota_key)
    if row is None:
        row = DemoQuotaCounter(quota_key=quota_key, usage_count=1, updated_at=now)
        db.add(row)
        await db.flush()
        return 1
    row.usage_count = int(row.usage_count) + 1
    row.updated_at = now
    await db.flush()
    return int(row.usage_count)


async def get_demo_quota_status(
    db: AsyncSession,
    *,
    visitor_id: str,
    settings: AppSettings | None = None,
) -> DemoQuotaStatus:
    cfg = settings or get_settings()
    day = _today_key(timezone=cfg.timezone)
    if not cfg.demo_quota_enabled:
        return DemoQuotaStatus(
            enabled=False,
            limit=cfg.demo_quota_daily_limit,
            used=0,
            remaining=cfg.demo_quota_daily_limit,
            reset_date=day,
            visitor_id=visitor_id,
        )
    try:
        normalized = _normalize_visitor_id(visitor_id)
    except ValueError:
        return DemoQuotaStatus(
            enabled=True,
            limit=cfg.demo_quota_daily_limit,
            used=cfg.demo_quota_daily_limit,
            remaining=0,
            reset_date=day,
            visitor_id="",
        )
    used = await _get_count(db, _quota_key(scope="visitor", identity=normalized, day=day))
    limit = cfg.demo_quota_daily_limit
    remaining = max(limit - used, 0)
    return DemoQuotaStatus(
        enabled=True,
        limit=limit,
        used=used,
        remaining=remaining,
        reset_date=day,
        visitor_id=normalized,
    )


async def check_and_consume_demo_quota(
    db: AsyncSession,
    *,
    visitor_id: str,
    client_ip: str,
    settings: AppSettings | None = None,
) -> DemoQuotaStatus:
    """Validate visitor/IP limits and consume one question credit."""
    cfg = settings or get_settings()
    day = _today_key(timezone=cfg.timezone)
    if not cfg.demo_quota_enabled:
        return DemoQuotaStatus(
            enabled=False,
            limit=cfg.demo_quota_daily_limit,
            used=0,
            remaining=cfg.demo_quota_daily_limit,
            reset_date=day,
            visitor_id=visitor_id,
        )

    normalized = _normalize_visitor_id(visitor_id)
    visitor_key = _quota_key(scope="visitor", identity=normalized, day=day)
    visitor_used = await _get_count(db, visitor_key)
    visitor_limit = cfg.demo_quota_daily_limit

    if visitor_used >= visitor_limit:
        raise DemoQuotaExceededError(
            f"今日 Demo 提问额度已用完（{visitor_limit} 次/天），请明天再试。",
            limit=visitor_limit,
            used=visitor_used,
            remaining=0,
            reset_date=day,
        )

    ip_key = ""
    if client_ip.strip() and cfg.demo_quota_ip_daily_limit > 0:
        ip_key = _quota_key(scope="ip", identity=_ip_hash(client_ip), day=day)
        ip_used = await _get_count(db, ip_key)
        if ip_used >= cfg.demo_quota_ip_daily_limit:
            raise DemoQuotaExceededError(
                "当前网络今日 Demo 额度已达上限，请明天再试或更换网络。",
                limit=cfg.demo_quota_ip_daily_limit,
                used=ip_used,
                remaining=0,
                reset_date=day,
            )

    new_visitor_used = await _increment(db, visitor_key, timezone=cfg.timezone)
    if ip_key:
        await _increment(db, ip_key, timezone=cfg.timezone)

    remaining = max(visitor_limit - new_visitor_used, 0)
    return DemoQuotaStatus(
        enabled=True,
        limit=visitor_limit,
        used=new_visitor_used,
        remaining=remaining,
        reset_date=day,
        visitor_id=normalized,
    )
