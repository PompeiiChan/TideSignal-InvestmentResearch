"""Database access for Trace records."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TraceRecord


class TraceRepository:
    """Repository for persisted trace details."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_trace(self, trace: TraceRecord) -> TraceRecord:
        """Persist a trace detail record."""
        self.db.add(trace)
        await self.db.flush()
        await self.db.refresh(trace)
        return trace

    async def get_trace(self, trace_id: str) -> TraceRecord | None:
        """Fetch one trace detail record."""
        result = await self.db.execute(select(TraceRecord).where(TraceRecord.id == trace_id))
        return result.scalar_one_or_none()

    async def delete_by_session(self, session_id: str) -> None:
        """Delete all traces for one session."""
        await self.db.execute(delete(TraceRecord).where(TraceRecord.session_id == session_id))
