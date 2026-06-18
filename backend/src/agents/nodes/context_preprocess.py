"""context_preprocess node."""

from __future__ import annotations

import re
from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.scenario_return import is_scenario_return_query
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ._helpers import run_node_with_trace

_PREDICTION_KEYWORDS = ("预测", "目标价", "一定涨", "明天涨", "估值预测", "未来收益", "会涨吗")
_MAX_HISTORY_MESSAGES = 12
_MAX_HISTORY_CHARS = 800


def _normalize_query(query: str) -> str:
    cleaned = re.sub(r"\s+", " ", query.strip())
    return cleaned


def _summarize_history(history: list[dict[str, str]]) -> str:
    if not history:
        return ""
    lines: list[str] = []
    for message in history[-_MAX_HISTORY_MESSAGES:]:
        role = str(message.get("role", "user")).strip() or "user"
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        snippet = content if len(content) <= 200 else f"{content[:200]}..."
        lines.append(f"{role}: {snippet}")
    summary = "\n".join(lines)
    if len(summary) > _MAX_HISTORY_CHARS:
        return f"{summary[:_MAX_HISTORY_CHARS]}..."
    return summary


def _detect_risk_hint(query: str) -> str:
    if is_scenario_return_query(query):
        return ""
    lowered = query.lower()
    for keyword in _PREDICTION_KEYWORDS:
        if keyword in lowered or keyword in query:
            return "prediction_boundary"
    return ""


def _build_context_pack(
    *,
    session_id: str,
    chat_history: list[dict[str, str]],
    user_profile: dict[str, Any],
    request_meta: dict[str, Any],
) -> dict[str, Any]:
    active_document_id = request_meta.get("document_id") or request_meta.get("active_document_id")
    return {
        "session_id": session_id,
        "history_count": len(chat_history),
        "user_profile": user_profile,
        "request_meta": request_meta,
        "active_document_id": active_document_id,
        "has_document_context": bool(active_document_id),
    }


async def context_preprocess(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Clean query, summarize history, and inject authoritative system time."""
    _ = (llm, rag)
    user_query = str(state.get("user_query", "")).strip()
    chat_history = state.get("chat_history") or []
    user_profile = state.get("user_profile") or {}
    request_meta = state.get("request_meta") or {}
    session_id = str(state.get("session_id", ""))

    input_data = {
        "user_query": user_query,
        "session_id": session_id,
        "history_count": len(chat_history),
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        normalized_query = _normalize_query(user_query) or user_query
        history_summary = _summarize_history(chat_history)
        context_pack = _build_context_pack(
            session_id=session_id,
            chat_history=chat_history,
            user_profile=user_profile,
            request_meta=request_meta,
        )
        risk_hint = _detect_risk_hint(normalized_query)
        output = {
            "normalized_query": normalized_query,
            "context_pack": context_pack,
            "history_summary": history_summary,
            "risk_hint": risk_hint,
            "system_context": time_ctx.to_dict(),
        }
        return output, "完成上下文预处理"

    return await run_node_with_trace(
        state,
        node="context_preprocess",
        input_data=input_data,
        summary="完成上下文预处理",
        fn=_execute,
    )
