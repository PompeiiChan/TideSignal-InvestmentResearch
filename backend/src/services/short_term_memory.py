"""Short-term conversation memory window helpers."""

from __future__ import annotations

from typing import Any

DEFAULT_SHORT_TERM_QA_ROUNDS = 5
DEFAULT_HISTORY_SUMMARY_MAX_CHARS = 800
DEFAULT_HISTORY_SNIPPET_CHARS = 200


def short_term_message_limit(*, qa_rounds: int) -> int:
    """Return max prior messages kept for a QA-round window."""
    return max(0, qa_rounds) * 2


def trim_chat_history(
    messages: list[dict[str, str]],
    *,
    max_qa_rounds: int,
    exclude_trailing_user: bool = True,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Return trimmed prior chat history and truncation metadata."""
    working = list(messages)

    if exclude_trailing_user and working:
        last_role = str(working[-1].get("role", "")).strip().lower()
        if last_role == "user":
            working = working[:-1]

    total_prior = len(working)
    limit = short_term_message_limit(qa_rounds=max_qa_rounds)
    truncated = total_prior > limit
    trimmed = working[-limit:] if limit > 0 else []

    meta: dict[str, Any] = {
        "history_window_rounds": max_qa_rounds,
        "history_total_messages": total_prior,
        "history_truncated": truncated,
        "history_count": len(trimmed),
    }
    return trimmed, meta


def summarize_chat_history(
    history: list[dict[str, str]],
    *,
    max_chars: int = DEFAULT_HISTORY_SUMMARY_MAX_CHARS,
    snippet_chars: int = DEFAULT_HISTORY_SNIPPET_CHARS,
) -> str:
    """Build a compact text summary from already-trimmed chat history."""
    if not history:
        return ""

    lines: list[str] = []
    for message in history:
        role = str(message.get("role", "user")).strip() or "user"
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        snippet = content if len(content) <= snippet_chars else f"{content[:snippet_chars]}..."
        lines.append(f"{role}: {snippet}")

    summary = "\n".join(lines)
    if len(summary) > max_chars:
        return f"{summary[:max_chars]}..."
    return summary
