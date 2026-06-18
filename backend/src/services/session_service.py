"""Session business service."""

from datetime import datetime
from itertools import count
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import MessageRecord, SessionRecord
from ..models.session import (
    DeleteSessionRead,
    MessageRead,
    SessionDetailRead,
    SessionPageRead,
    SessionRead,
    SessionSource,
)
from ..repositories.session_repository import SessionRepository
from ..repositories.trace_repository import TraceRepository
from ..settings import get_settings
from .demo_rich_blocks import (
    CALCULATOR_DEMO_ASSISTANT_MESSAGE_ID,
    CLIENT_SHOWCASE_SESSIONS,
    HEATMAP_DEMO_ASSISTANT_MESSAGE_ID,
    RANKING_DEMO_ASSISTANT_MESSAGE_ID,
    SHOWCASE_ASSISTANT_MESSAGES,
)
from .message_sanitizer import sanitize_assistant_content, sanitize_rich_blocks
from .rich_block_types import extract_rich_block_types

_SHOWCASE_SESSION_BY_MESSAGE = {
    RANKING_DEMO_ASSISTANT_MESSAGE_ID: "sess_20260608_001",
    CALCULATOR_DEMO_ASSISTANT_MESSAGE_ID: "sess_20260608_002",
    HEATMAP_DEMO_ASSISTANT_MESSAGE_ID: "sess_20260608_004",
}

_id_counter = count(1)


class SessionNotFoundError(ValueError):
    """Raised when a session cannot be found."""


def _now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().timezone))


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(get_settings().timezone))
    return value.isoformat(timespec="seconds")


def _session_id(now: datetime) -> str:
    return f"sess_{now.strftime('%Y%m%d_%H%M%S')}_{next(_id_counter):03d}"


def _message_id(now: datetime, suffix: str) -> str:
    return f"msg_{now.strftime('%Y%m%d_%H%M%S')}_{next(_id_counter):03d}_{suffix}"


class SessionService:
    """Business logic for session history."""

    def __init__(self, db: AsyncSession):
        self.repo = SessionRepository(db)
        self.trace_repo = TraceRepository(db)
        self.db = db

    async def ensure_seed_data(self) -> None:
        """Create minimal demo history for first local run."""
        await self.ensure_client_showcase_sessions()
        if await self.repo.count_sessions() > len(CLIENT_SHOWCASE_SESSIONS):
            return

        admin_session_id = "sess_20260608_003"
        if await self.repo.get_session(admin_session_id) is not None:
            return

        created_at = datetime.fromisoformat("2026-06-08T13:18:00+08:00")
        title = "管理端查看 Agent 路由过程"
        assistant_content = "当前问答已同步到管理端，可在右侧查看 Trace 链路占位区。"
        session = SessionRecord(
            id=admin_session_id,
            title=title,
            title_source="first_query",
            is_draft=False,
            source="admin",
            created_at=created_at,
            updated_at=created_at,
            last_message_preview=assistant_content[:120],
            last_trace_id=None,
        )
        await self.repo.create_session(session)
        await self.repo.create_message(
            MessageRecord(
                id="msg_20260608_003_user",
                session_id=admin_session_id,
                role="user",
                content=title,
                rich_blocks=[],
                trace_id=None,
                created_at=created_at,
            )
        )
        await self.repo.create_message(
            MessageRecord(
                id="msg_20260608_003_assistant",
                session_id=admin_session_id,
                role="assistant",
                content=assistant_content,
                rich_blocks=[],
                trace_id=None,
                created_at=created_at,
            )
        )
        await self.db.commit()

    async def ensure_client_showcase_sessions(self) -> None:
        """Ensure ranking / calculator / heatmap showcase sessions exist (idempotent)."""
        changed = False
        for spec in CLIENT_SHOWCASE_SESSIONS:
            session_id = str(spec["session_id"])
            if await self.repo.get_session(session_id) is not None:
                continue
            created_at = datetime.fromisoformat(str(spec["created_at"]))
            assistant_content = str(spec["assistant_content"])
            preview = assistant_content.split("\n", 1)[0].strip()[:120]
            session = SessionRecord(
                id=session_id,
                title=str(spec["title"]),
                title_source="first_query",
                is_draft=False,
                source="client",
                created_at=created_at,
                updated_at=created_at,
                last_message_preview=preview,
                last_trace_id=None,
            )
            await self.repo.create_session(session)
            await self.repo.create_message(
                MessageRecord(
                    id=str(spec["user_message_id"]),
                    session_id=session_id,
                    role="user",
                    content=str(spec["title"]),
                    rich_blocks=[],
                    trace_id=None,
                    created_at=created_at,
                )
            )
            await self.repo.create_message(
                MessageRecord(
                    id=str(spec["assistant_message_id"]),
                    session_id=session_id,
                    role="assistant",
                    content=assistant_content,
                    rich_blocks=list(spec["rich_blocks"]),
                    trace_id=None,
                    created_at=created_at,
                )
            )
            changed = True
        if changed:
            await self.db.commit()

    async def ensure_heatmap_demo_session(self) -> None:
        """Backward-compatible alias for heatmap showcase seeding."""
        await self.ensure_client_showcase_sessions()

    async def ensure_showcase_rich_blocks(self) -> None:
        """Backfill demo rich_blocks on seeded showcase messages (idempotent)."""
        changed = False
        for message_id, payload in SHOWCASE_ASSISTANT_MESSAGES.items():
            message = await self.repo.get_message(message_id)
            if message is None or message.rich_blocks:
                continue
            message.content = payload["content"]
            message.rich_blocks = payload["rich_blocks"]
            session_id = _SHOWCASE_SESSION_BY_MESSAGE.get(message_id)
            if session_id:
                session = await self.repo.get_session(session_id)
                if session is not None:
                    preview = str(payload["content"]).split("\n", 1)[0].strip()[:120]
                    session.last_message_preview = preview
                    session.updated_at = message.created_at
            changed = True
        if changed:
            await self.db.commit()

    async def _pin_showcase_sessions(self, sessions: list[SessionRecord]) -> list[SessionRecord]:
        """Keep rich-component demo sessions visible at the top of the history list."""
        by_id = {session.id: session for session in sessions}
        for spec in CLIENT_SHOWCASE_SESSIONS:
            session_id = str(spec["session_id"])
            if session_id in by_id:
                continue
            loaded = await self.repo.get_session(session_id)
            if loaded is not None:
                by_id[session_id] = loaded
        pinned = [
            by_id[str(spec["session_id"])]
            for spec in CLIENT_SHOWCASE_SESSIONS
            if str(spec["session_id"]) in by_id
        ]
        pinned_ids = {session.id for session in pinned}
        rest = [session for session in sessions if session.id not in pinned_ids]
        return [*pinned, *rest]

    async def list_sessions(self, keyword: str, page: int, page_size: int) -> SessionPageRead:
        """Return the contract-aligned session list."""
        if page < 1:
            raise ValueError("page 必须大于等于 1")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size 必须在 1 到 100 之间")

        await self.ensure_client_showcase_sessions()
        await self.ensure_showcase_rich_blocks()
        sessions, total = await self.repo.list_sessions(keyword, page, page_size)
        if not keyword.strip():
            sessions = await self._pin_showcase_sessions(sessions)
        rich_blocks_by_session = await self.repo.get_latest_assistant_rich_blocks_by_sessions(
            [session.id for session in sessions]
        )
        return SessionPageRead(
            items=[
                self._to_session_read(
                    session,
                    rich_block_types=extract_rich_block_types(
                        rich_blocks_by_session.get(session.id, [])
                    ),
                )
                for session in sessions
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def create_session(self, source: SessionSource) -> SessionRead:
        """Create a draft session."""
        now = _now()
        session = SessionRecord(
            id=_session_id(now),
            title="新对话",
            title_source="system",
            is_draft=True,
            source=source,
            created_at=now,
            updated_at=now,
            last_message_preview="",
            last_trace_id=None,
        )
        await self.repo.create_session(session)
        await self.db.commit()
        return self._to_session_read(session)

    async def get_detail(self, session_id: str) -> SessionDetailRead:
        """Return one session and its messages."""
        await self.ensure_client_showcase_sessions()
        await self.ensure_showcase_rich_blocks()
        session = await self.repo.get_session(session_id)
        if session is None:
            raise SessionNotFoundError("会话不存在")
        messages = list(session.messages)
        last_assistant_blocks: list[dict] = []
        for message in reversed(messages):
            if message.role == "assistant":
                last_assistant_blocks = message.rich_blocks if isinstance(message.rich_blocks, list) else []
                break
        return SessionDetailRead(
            session=self._to_session_read(
                session,
                rich_block_types=extract_rich_block_types(last_assistant_blocks),
            ),
            messages=[self._to_message_read(message) for message in messages],
        )

    async def delete_session(self, session_id: str) -> DeleteSessionRead:
        """Delete one session."""
        await self.trace_repo.delete_by_session(session_id)
        deleted = await self.repo.delete_session(session_id)
        if not deleted:
            await self.db.rollback()
            raise SessionNotFoundError("会话不存在")
        await self.db.commit()
        return DeleteSessionRead(id=session_id, deleted=True)

    async def add_placeholder_message(self, session_id: str, content: str) -> MessageRead:
        """Add a local placeholder message without implementing chat query."""
        now = _now()
        message = MessageRecord(
            id=_message_id(now, "local"),
            session_id=session_id,
            role="assistant",
            content=content,
            rich_blocks=[],
            trace_id=None,
            created_at=now,
        )
        await self.repo.create_message(message)
        await self.db.commit()
        return self._to_message_read(message)

    def _to_session_read(
        self,
        session: SessionRecord,
        *,
        rich_block_types: list[str] | None = None,
    ) -> SessionRead:
        return SessionRead(
            id=session.id,
            title=session.title,
            title_source=session.title_source,  # type: ignore[arg-type]
            is_draft=session.is_draft,
            source=session.source,  # type: ignore[arg-type]
            created_at=_iso(session.created_at),
            updated_at=_iso(session.updated_at),
            last_message_preview=sanitize_assistant_content("assistant", session.last_message_preview),
            last_trace_id=session.last_trace_id,
            rich_block_types=list(rich_block_types or []),
        )

    def _to_message_read(self, message: MessageRecord) -> MessageRead:
        return MessageRead(
            id=message.id,
            session_id=message.session_id,
            role=message.role,  # type: ignore[arg-type]
            content=sanitize_assistant_content(message.role, message.content),
            rich_blocks=sanitize_rich_blocks(message.role, message.rich_blocks),
            trace_id=message.trace_id,
            created_at=_iso(message.created_at),
        )
