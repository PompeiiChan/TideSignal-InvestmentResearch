"""Tests for conversation_context service."""

from __future__ import annotations

from backend.src.services.conversation_context import (
    build_conversation_context,
    format_conversation_context_for_prompt,
)


def test_build_conversation_context_first_turn_empty() -> None:
    ctx = build_conversation_context(
        history_summary="",
        active_slots={"stock_name": "宁德时代"},
        inherited_slot_keys=[],
        normalized_query="宁德时代基本面怎么样",
    )
    assert ctx == {"has_context": False}


def test_build_conversation_context_followup_with_inherited_slots() -> None:
    ctx = build_conversation_context(
        history_summary="user: 宁德时代基本面怎么样\nassistant: 营收稳健…",
        active_slots={
            "stock_name": "宁德时代",
            "stock_code": "300750.SZ",
            "time_range": "2026Q1",
        },
        inherited_slot_keys=["stock_name", "stock_code"],
        normalized_query="一季报呢",
    )
    assert ctx["has_context"] is True
    assert ctx["active_slots"]["stock_name"] == "宁德时代"
    assert "宁德时代" in str(ctx["carryover_hint"])
    assert "一季报" in str(ctx["carryover_hint"])


def test_format_conversation_context_for_prompt_nonempty() -> None:
    ctx = build_conversation_context(
        history_summary="user: 宁德时代基本面怎么样\nassistant: 营收稳健…",
        active_slots={"stock_name": "宁德时代", "time_range": "2026Q1"},
        inherited_slot_keys=["stock_name"],
        normalized_query="一季报呢",
    )
    text = format_conversation_context_for_prompt(ctx)
    assert text
    assert "宁德时代" in text
    assert "近期对话摘要" in text
    assert "标的=宁德时代" in text
