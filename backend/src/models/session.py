"""Session API DTOs."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SessionSource = Literal["client", "admin"]
MessageRole = Literal["user", "assistant", "system"]
TitleSource = Literal["first_query", "system"]


class SessionCreate(BaseModel):
    """Request body for creating a draft session."""

    source: SessionSource


class SessionRead(BaseModel):
    """Session DTO returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    title_source: TitleSource
    is_draft: bool
    source: SessionSource
    created_at: str
    updated_at: str
    last_message_preview: str
    last_trace_id: str | None
    rich_block_types: list[str] = Field(default_factory=list)


class MessageRead(BaseModel):
    """Message DTO returned in session detail."""

    id: str
    session_id: str
    role: MessageRole
    content: str
    rich_blocks: list[dict[str, Any]] = Field(default_factory=list)
    trace_id: str | None
    created_at: str


class SessionDetailRead(BaseModel):
    """Session detail response."""

    session: SessionRead
    messages: list[MessageRead]


class SessionPageRead(BaseModel):
    """Contract-aligned session list page."""

    items: list[SessionRead]
    total: int
    page: int
    page_size: int


class DeleteSessionRead(BaseModel):
    """Delete session response."""

    id: str
    deleted: bool
