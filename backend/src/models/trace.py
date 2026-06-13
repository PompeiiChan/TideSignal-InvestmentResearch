"""Trace API DTOs."""

from typing import Any

from pydantic import BaseModel

from .chat import QualityResult, TraceStatus


class TraceDetailItem(BaseModel):
    """One key-value row inside a trace detail section."""

    label: str
    value: str


class TraceDetailSection(BaseModel):
    """Expandable detail section for a trace step."""

    title: str
    items: list[TraceDetailItem]


class TraceStepRead(BaseModel):
    """One step in a trace timeline."""

    step_id: str
    step_index: int
    name: str
    node: str
    status: TraceStatus
    latency_ms: int
    summary: str
    detail_sections: list[TraceDetailSection]
    input: dict[str, Any]
    output: dict[str, Any]
    raw_json: dict[str, Any]
    error: str | None


class TraceMetadataRead(BaseModel):
    """Trace-level metrics."""

    total_latency_ms: int
    tool_calls_count: int
    quality_check_result: QualityResult
    model_versions: dict[str, str] | None = None


class TraceRead(BaseModel):
    """Full Trace response."""

    id: str
    session_id: str
    message_id: str
    user_query: str
    status: TraceStatus
    steps: list[TraceStepRead]
    metadata: TraceMetadataRead


class RawTraceStepRead(BaseModel):
    """Raw JSON payload for a single Trace step."""

    trace_id: str
    step_id: str
    raw_json: dict[str, Any]
