"""Shared helpers for demo quota enforcement on chat routes."""

from __future__ import annotations

from fastapi import Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.demo_quota import DemoQuotaExceededError, check_and_consume_demo_quota

VISITOR_HEADER = "X-Demo-Visitor-Id"


def client_ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


async def enforce_demo_quota(
    db: AsyncSession,
    *,
    request: Request,
    visitor_id: str | None,
) -> None:
    """Consume one demo credit or raise DemoQuotaExceededError."""
    await check_and_consume_demo_quota(
        db,
        visitor_id=visitor_id or "",
        client_ip=client_ip_from_request(request),
    )


def visitor_header_dependency(
    x_demo_visitor_id: str | None = Header(default=None, alias=VISITOR_HEADER),
) -> str:
    return (x_demo_visitor_id or "").strip()
