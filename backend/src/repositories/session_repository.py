"""Database access for sessions and messages."""

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db.models import MessageRecord, SessionRecord


class SessionRepository:
    """Repository for chat sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_sessions(self) -> int:
        """Return total persisted session count."""
        result = await self.db.execute(select(func.count(SessionRecord.id)))
        return int(result.scalar_one())

    async def list_sessions(
        self,
        keyword: str,
        page: int,
        page_size: int,
    ) -> tuple[list[SessionRecord], int]:
        """List sessions with optional keyword filtering."""
        stmt = select(SessionRecord)
        count_stmt = select(func.count(SessionRecord.id))
        normalized = keyword.strip()
        if normalized:
            pattern = f"%{normalized}%"
            stmt = stmt.where(
                SessionRecord.title.ilike(pattern)
                | SessionRecord.last_message_preview.ilike(pattern)
            )
            count_stmt = count_stmt.where(
                SessionRecord.title.ilike(pattern)
                | SessionRecord.last_message_preview.ilike(pattern)
            )

        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one())
        result = await self.db.execute(
            stmt.order_by(SessionRecord.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_latest_assistant_rich_blocks_by_sessions(
        self,
        session_ids: list[str],
    ) -> dict[str, list[dict]]:
        """Map session_id -> rich_blocks from the latest assistant message."""
        if not session_ids:
            return {}

        latest_subq = (
            select(
                MessageRecord.session_id.label("session_id"),
                func.max(MessageRecord.created_at).label("max_created_at"),
            )
            .where(
                MessageRecord.session_id.in_(session_ids),
                MessageRecord.role == "assistant",
            )
            .group_by(MessageRecord.session_id)
            .subquery()
        )
        result = await self.db.execute(
            select(MessageRecord.session_id, MessageRecord.rich_blocks).join(
                latest_subq,
                and_(
                    MessageRecord.session_id == latest_subq.c.session_id,
                    MessageRecord.created_at == latest_subq.c.max_created_at,
                    MessageRecord.role == "assistant",
                ),
            )
        )
        blocks_by_session: dict[str, list[dict]] = {}
        for session_id, rich_blocks in result.all():
            blocks_by_session[str(session_id)] = rich_blocks if isinstance(rich_blocks, list) else []
        return blocks_by_session

    async def get_session(self, session_id: str) -> SessionRecord | None:
        """Fetch one session with messages."""
        result = await self.db.execute(
            select(SessionRecord)
            .where(SessionRecord.id == session_id)
            .options(selectinload(SessionRecord.messages))
        )
        return result.scalar_one_or_none()

    async def create_session(self, session: SessionRecord) -> SessionRecord:
        """Persist a new session."""
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def create_message(self, message: MessageRecord) -> MessageRecord:
        """Persist a new message."""
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_message(self, message_id: str) -> MessageRecord | None:
        """Fetch one message by id."""
        result = await self.db.execute(select(MessageRecord).where(MessageRecord.id == message_id))
        return result.scalar_one_or_none()

    async def delete_message(self, message_id: str) -> bool:
        """Delete one message."""
        message = await self.get_message(message_id)
        if message is None:
            return False
        await self.db.delete(message)
        await self.db.flush()
        return True

    async def get_previous_user_message(
        self,
        session_id: str,
        before: datetime,
    ) -> MessageRecord | None:
        """Return the most recent user message created before the given timestamp."""
        result = await self.db.execute(
            select(MessageRecord)
            .where(
                MessageRecord.session_id == session_id,
                MessageRecord.role == "user",
                MessageRecord.created_at < before,
            )
            .order_by(MessageRecord.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_previous_assistant_message(
        self,
        session_id: str,
        before: datetime,
    ) -> MessageRecord | None:
        """Return the most recent assistant message created before the given timestamp."""
        result = await self.db.execute(
            select(MessageRecord)
            .where(
                MessageRecord.session_id == session_id,
                MessageRecord.role == "assistant",
                MessageRecord.created_at < before,
            )
            .order_by(MessageRecord.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete_session(self, session_id: str) -> bool:
        """Delete one session and its messages."""
        session = await self.get_session(session_id)
        if session is None:
            return False
        await self.db.delete(session)
        await self.db.flush()
        return True
