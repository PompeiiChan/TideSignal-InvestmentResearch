"""User-facing stream status phases for LangGraph chat."""

from __future__ import annotations

from typing import Any, Literal

from ...integrations.langgraph.state import AgentState

StreamPhase = Literal["thinking", "checking", "writing", "rewriting", "enriching"]

_OUTPUT_NODES = frozenset(
    {
        "clarification_response",
        "response_assembly",
        "fallback_response",
    }
)


def _has_revision_feedback(state: AgentState) -> bool:
    quality_status = str(state.get("quality_status", "")).strip().lower()
    revision_suggestions = state.get("revision_suggestions") or []
    return quality_status == "revise" or bool(revision_suggestions)


def resolve_entry_phase(node: str, state: AgentState) -> tuple[StreamPhase, str]:
    """Map a LangGraph node entry to a user-visible phase and label."""
    if node == "quality_check":
        return "checking", "Checking"
    if node in {"evidence_gap_check", "gap_planner"}:
        return "enriching", "Enriching"
    if node in _OUTPUT_NODES:
        if node == "response_assembly" and _has_revision_feedback(state):
            return "rewriting", "Rewriting"
        return "writing", "Writing"
    return "thinking", "Thinking"


def build_status_event(phase: StreamPhase, label: str) -> dict[str, Any]:
    return {"event": "status", "data": {"phase": phase, "label": label}}


def emit_node_entry_status(state: AgentState, node: str) -> None:
    """Push a status SSE event when a node starts executing."""
    stream_callback = state.get("stream_callback")
    if not callable(stream_callback):
        return
    phase, label = resolve_entry_phase(node, state)
    stream_callback(build_status_event(phase, label))


def emit_stream_phase(
    stream_callback: Any,
    phase: StreamPhase,
    label: str | None = None,
) -> None:
    """Push a status event from runner or assembly helpers."""
    if not callable(stream_callback):
        return
    display = label or {
        "thinking": "Thinking",
        "checking": "Checking",
        "writing": "Writing",
        "rewriting": "Rewriting",
        "enriching": "Enriching",
    }[phase]
    stream_callback(build_status_event(phase, display))
