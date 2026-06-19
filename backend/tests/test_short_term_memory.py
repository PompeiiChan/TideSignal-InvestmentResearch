"""Tests for short-term conversation memory window."""

from __future__ import annotations

from backend.src.services.short_term_memory import (
    DEFAULT_HISTORY_SUMMARY_MAX_CHARS,
    summarize_chat_history,
    trim_chat_history,
)


def _history(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"role": role, "content": content} for role, content in pairs]


def test_trim_keeps_five_rounds_on_sixth_turn() -> None:
    """Six prior QA rounds (12 messages) keep the latest five rounds."""
    messages = _history(
        ("user", "u1"),
        ("assistant", "a1"),
        ("user", "u2"),
        ("assistant", "a2"),
        ("user", "u3"),
        ("assistant", "a3"),
        ("user", "u4"),
        ("assistant", "a4"),
        ("user", "u5"),
        ("assistant", "a5"),
        ("user", "u6"),
        ("assistant", "a6"),
    )
    trimmed, meta = trim_chat_history(messages, max_qa_rounds=5, exclude_trailing_user=True)

    assert len(trimmed) == 10
    assert trimmed[0]["content"] == "u2"
    assert trimmed[-1]["content"] == "a6"
    assert meta["history_truncated"] is True
    assert meta["history_total_messages"] == 12
    assert meta["history_count"] == 10
    assert meta["history_window_rounds"] == 5


def test_trim_excludes_trailing_user() -> None:
    """Current-turn user message must not enter prior chat history."""
    messages = _history(
        ("user", "u1"),
        ("assistant", "a1"),
        ("user", "u2"),
    )
    trimmed, meta = trim_chat_history(messages, max_qa_rounds=5, exclude_trailing_user=True)

    assert trimmed == _history(("user", "u1"), ("assistant", "a1"))
    assert meta["history_total_messages"] == 2
    assert meta["history_count"] == 2
    assert meta["history_truncated"] is False


def test_summarize_respects_max_chars() -> None:
    """Long histories are summarized within the configured character cap."""
    long_content = "x" * 500
    history = _history(
        ("user", long_content),
        ("assistant", long_content),
        ("user", long_content),
        ("assistant", long_content),
    )
    summary = summarize_chat_history(history, max_chars=DEFAULT_HISTORY_SUMMARY_MAX_CHARS)

    assert summary
    assert len(summary) <= DEFAULT_HISTORY_SUMMARY_MAX_CHARS + 3


def test_round_seven_drops_oldest_pair() -> None:
    """Round-seven session drops only the oldest QA pair from six prior rounds."""
    messages = _history(
        ("user", "u1"),
        ("assistant", "a1"),
        ("user", "u2"),
        ("assistant", "a2"),
        ("user", "u3"),
        ("assistant", "a3"),
        ("user", "u4"),
        ("assistant", "a4"),
        ("user", "u5"),
        ("assistant", "a5"),
        ("user", "u6"),
        ("assistant", "a6"),
        ("user", "u7"),
    )
    trimmed, meta = trim_chat_history(messages, max_qa_rounds=5, exclude_trailing_user=True)

    contents = [message["content"] for message in trimmed]
    assert "u1" not in contents
    assert "a1" not in contents
    assert trimmed[0]["content"] == "u2"
    assert trimmed[-1]["content"] == "a6"
    assert len(trimmed) == 10
    assert meta["history_truncated"] is True
