"""Project ORM models based on the PyCore database model template."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pycore.integrations.db.models import Base


class SessionRecord(Base):
    """Persisted chat session."""

    __tablename__ = "investment_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_source: Mapped[str] = mapped_column(String(32), nullable=False)
    is_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_message_preview: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    last_trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    messages: Mapped[list["MessageRecord"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MessageRecord.created_at",
    )


class MessageRecord(Base):
    """Persisted chat message for a session."""

    __tablename__ = "investment_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rich_blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped[SessionRecord] = relationship(back_populates="messages")


class TraceRecord(Base):
    """Persisted fallback trace details for a chat response."""

    __tablename__ = "investment_traces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investment_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    trace_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LayoutPreferenceRecord(Base):
    """Persisted layout preferences for the single-user MVP."""

    __tablename__ = "layout_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    sidebar_width: Mapped[int] = mapped_column(Integer, nullable=False, default=230)
    trace_panel_width: Mapped[int] = mapped_column(Integer, nullable=False, default=488)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


__all__ = ["Base", "LayoutPreferenceRecord", "MessageRecord", "SessionRecord", "TraceRecord"]
