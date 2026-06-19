"""Structured multi-turn conversation carryover for downstream LangGraph nodes."""

from __future__ import annotations

from typing import Any

from ..integrations.langgraph.state import AgentState

_KEY_SLOT_KEYS = ("stock_name", "industry", "topic")

_SLOT_LABELS: dict[str, str] = {
    "stock_name": "标的",
    "stock_code": "代码",
    "time_range": "时间口径",
    "industry": "行业",
    "topic": "主题",
    "analysis_dimension": "分析维度",
}


def _has_key_slots(active_slots: dict[str, Any]) -> bool:
    return any(str(active_slots.get(key, "")).strip() for key in _KEY_SLOT_KEYS)


def _build_carryover_hint(
    *,
    active_slots: dict[str, Any],
    normalized_query: str,
) -> str:
    stock_name = str(active_slots.get("stock_name", "")).strip()
    industry = str(active_slots.get("industry", "")).strip()
    topic = str(active_slots.get("topic", "")).strip()
    time_range = str(active_slots.get("time_range", "")).strip()
    query = normalized_query.strip().rstrip("？?")

    if stock_name:
        subject = f"{stock_name}基本面"
    elif industry:
        subject = f"{industry}行业"
    elif topic:
        subject = topic
    else:
        subject = "上一轮话题"

    if query:
        focus = query
    elif time_range:
        focus = time_range
    else:
        focus = "续问"

    return f"续问：用户在上轮已讨论{subject}，本轮关注{focus}。"


def build_conversation_context(
    *,
    history_summary: str,
    active_slots: dict[str, Any],
    inherited_slot_keys: list[str] | None = None,
    normalized_query: str = "",
) -> dict[str, Any]:
    """Return structured carryover; empty signal yields ``has_context=false``."""
    history = history_summary.strip()
    slots = dict(active_slots or {})
    inherited = [str(key) for key in (inherited_slot_keys or []) if str(key).strip()]

    if not history or (not _has_key_slots(slots) and not inherited):
        return {"has_context": False}

    return {
        "has_context": True,
        "history_summary": history,
        "active_slots": slots,
        "inherited_slot_keys": inherited,
        "carryover_hint": _build_carryover_hint(
            active_slots=slots,
            normalized_query=normalized_query,
        ),
    }


def format_conversation_context_for_prompt(ctx: dict[str, Any]) -> str:
    """Human-readable block for LLM user prompts."""
    if not ctx.get("has_context"):
        return ""

    lines: list[str] = []
    carryover_hint = str(ctx.get("carryover_hint", "")).strip()
    if carryover_hint:
        lines.append(carryover_hint)

    history = str(ctx.get("history_summary", "")).strip()
    if history:
        lines.append("近期对话摘要：")
        lines.append(history)

    raw_slots = ctx.get("active_slots")
    active_slots: dict[str, Any] = raw_slots if isinstance(raw_slots, dict) else {}
    slot_parts: list[str] = []
    for key, label in _SLOT_LABELS.items():
        value = str(active_slots.get(key, "")).strip()
        if value:
            slot_parts.append(f"{label}={value}")
    if slot_parts:
        lines.append("当前槽位：" + "，".join(slot_parts))

    inherited = ctx.get("inherited_slot_keys") or []
    if inherited:
        lines.append("继承槽位：" + "、".join(str(key) for key in inherited))

    return "\n".join(lines)


def enrich_state_conversation_context(state: AgentState) -> dict[str, Any]:
    """Build conversation_context from LangGraph state."""
    return build_conversation_context(
        history_summary=str(state.get("history_summary", "")),
        active_slots=state.get("active_slots") or state.get("slots") or {},
        inherited_slot_keys=state.get("inherited_slot_keys") or [],
        normalized_query=str(state.get("normalized_query", "")),
    )
