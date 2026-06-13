"""Chat query API DTOs."""

from typing import Literal

from pydantic import BaseModel, Field

from .session import MessageRead, SessionRead, SessionSource

TraceStatus = Literal["pending", "running", "success", "failed"]
QualityResult = Literal["PASS", "FAIL"]


class ChatQueryRequest(BaseModel):
    """Request body for sending an investment research query."""

    session_id: str = Field(..., min_length=1)
    source: SessionSource
    query: str = Field(..., min_length=1)


class ChatRegenerateRequest(BaseModel):
    """Request body for regenerating an assistant reply."""

    session_id: str = Field(..., min_length=1)
    assistant_message_id: str = Field(..., min_length=1)
    source: SessionSource


class TraceSummaryMetadata(BaseModel):
    """Basic trace metadata returned by the fallback chat endpoint."""

    total_latency_ms: int
    tool_calls_count: int
    quality_check_result: QualityResult
    model_versions: dict[str, str] | None = None


class TraceSummaryRead(BaseModel):
    """T-004 trace summary; full trace details are implemented in T-005."""

    id: str
    status: TraceStatus
    metadata: TraceSummaryMetadata


class ChatQueryResponse(BaseModel):
    """Contract-aligned response for POST /api/chat/query."""

    session: SessionRead
    user_message: MessageRead
    assistant_message: MessageRead
    trace: TraceSummaryRead
