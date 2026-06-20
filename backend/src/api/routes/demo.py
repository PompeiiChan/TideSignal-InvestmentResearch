"""Demo quota API routes."""

from typing import cast

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter
from pycore.api.responses import APIResponse, success_response

from ...api.deps import get_session
from ...models.demo import DemoQuotaRead
from ...services.demo_quota import get_demo_quota_status

router = APIRouter(prefix="/api/demo", tags=["demo"])
DB_SESSION_DEPENDENCY = Depends(get_session)

VISITOR_HEADER = "X-Demo-Visitor-Id"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


@router.get("/quota", response_model=APIResponse[DemoQuotaRead])
async def get_demo_quota(
    request: Request,
    db: AsyncSession = DB_SESSION_DEPENDENCY,
    x_demo_visitor_id: str | None = Header(default=None, alias=VISITOR_HEADER),
) -> APIResponse[DemoQuotaRead]:
    """Return remaining daily demo question quota for the current visitor."""
    visitor_id = (x_demo_visitor_id or "").strip()
    status = await get_demo_quota_status(db, visitor_id=visitor_id)
    payload = DemoQuotaRead(
        enabled=status.enabled,
        limit=status.limit,
        used=status.used,
        remaining=status.remaining,
        reset_date=status.reset_date,
        visitor_id=status.visitor_id or visitor_id,
    )
    return cast(APIResponse[DemoQuotaRead], success_response(data=payload.model_dump()))
