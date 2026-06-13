"""Tests for user-facing stream status phases."""

from __future__ import annotations

from src.integrations.langgraph.status_phases import (
    build_status_event,
    emit_node_entry_status,
    resolve_entry_phase,
)


def test_resolve_entry_phase_defaults_to_thinking() -> None:
    phase, label = resolve_entry_phase("intent_recognition", {})
    assert phase == "thinking"
    assert label == "Thinking"


def test_resolve_entry_phase_quality_check() -> None:
    phase, label = resolve_entry_phase("quality_check", {})
    assert phase == "checking"
    assert label == "Checking"


def test_resolve_entry_phase_writing() -> None:
    phase, label = resolve_entry_phase("response_assembly", {"quality_status": "pass"})
    assert phase == "writing"
    assert label == "Writing"


def test_resolve_entry_phase_rewriting_after_revise() -> None:
    phase, label = resolve_entry_phase(
        "response_assembly",
        {"quality_status": "revise", "revision_suggestions": ["补充引用"]},
    )
    assert phase == "rewriting"
    assert label == "Rewriting"


def test_emit_node_entry_status_uses_stream_callback() -> None:
    events: list[dict] = []

    def callback(event: dict) -> None:
        events.append(event)

    emit_node_entry_status({"stream_callback": callback}, "quality_check")
    assert events == [build_status_event("checking", "Checking")]
