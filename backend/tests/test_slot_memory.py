"""Tests for session pending slot memory helpers."""

from __future__ import annotations

from backend.src.services.slot_memory import (
    build_context_state_from_run,
    filter_missing_after_inherit,
    merge_pending_slots,
    should_clear_pending,
    should_persist_pending,
)


def test_merge_inherits_stock_name_on_follow_up() -> None:
    merged, inherited, overridden = merge_pending_slots(
        intent_id="stock_analysis",
        pending_slots={"stock_name": "宁德时代", "stock_code": "300750.SZ"},
        extracted_slots={"time_range": "2026Q1"},
        pending_intent_id="stock_analysis",
    )

    assert merged["stock_name"] == "宁德时代"
    assert merged["time_range"] == "2026Q1"
    assert "stock_name" in inherited
    assert overridden == []


def test_merge_overrides_stock_name_when_user_switches() -> None:
    merged, inherited, overridden = merge_pending_slots(
        intent_id="stock_analysis",
        pending_slots={"stock_name": "宁德时代"},
        extracted_slots={"stock_name": "泸州老窖"},
        pending_intent_id="stock_analysis",
    )

    assert merged["stock_name"] == "泸州老窖"
    assert "stock_name" not in inherited
    assert "stock_name" in overridden


def test_filter_missing_removes_inherited_stock_name() -> None:
    filtered = filter_missing_after_inherit(
        ["stock_name", "time_range"],
        {"stock_name": "宁德时代"},
        ["stock_name"],
    )

    assert filtered == ["time_range"]


def test_should_clear_pending_on_chit_chat() -> None:
    assert should_clear_pending(new_intent_id="chit_chat", old_intent_id="stock_analysis") is True
    assert should_clear_pending(new_intent_id="stock_analysis", old_intent_id="stock_analysis") is False


def test_should_persist_pending_only_after_successful_route() -> None:
    assert should_persist_pending(intent_id="stock_analysis", need_clarification=False) is True
    assert should_persist_pending(intent_id="stock_analysis", need_clarification=True) is False
    assert should_persist_pending(intent_id="chit_chat", need_clarification=False) is False


def test_build_context_state_from_run_keeps_inheritable_slots() -> None:
    payload = build_context_state_from_run(
        intent_id="stock_analysis",
        slots={
            "stock_name": "宁德时代",
            "stock_code": "300750.SZ",
            "time_range": "2026Q1",
        },
        slot_confidence={"stock_name": 0.95},
    )

    assert payload["pending_intent_id"] == "stock_analysis"
    assert payload["pending_slots"]["stock_name"] == "宁德时代"
    assert "time_range" not in payload["pending_slots"]
    assert payload["pending_slot_confidence"]["stock_name"] == 0.95
    assert payload["updated_at"]
