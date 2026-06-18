"""Shared helpers for LangGraph agent nodes."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypeVar

from ...integrations.langgraph.state import AgentState
from ...integrations.langgraph.status_phases import (
    emit_node_complete_status,
    emit_node_entry_status,
)
from ...integrations.langgraph.trace_recorder import TraceRecorder
from ...integrations.llm.client import LLMClientError
from ...integrations.llm.service import LLMService

T = TypeVar("T")

_VALID_INTENT_IDS = frozenset(
    {
        "data_query",
        "hotspot_analysis",
        "stock_analysis",
        "document_qa",
        "chit_chat",
        "unknown",
        "prediction_request",
    }
)

_INTENT_DISPLAY_NAMES: dict[str, str] = {
    "data_query": "问数查询",
    "hotspot_analysis": "热点解读",
    "stock_analysis": "个股分析",
    "document_qa": "文档问答",
    "chit_chat": "闲聊",
    "unknown": "无法识别",
    "prediction_request": "预测/测算请求",
}


def next_step_index(state: AgentState) -> int:
    return len(state.get("trace_steps") or []) + 1


def build_trace_update(
    state: AgentState,
    *,
    node: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    summary: str,
    status: Literal["success", "failed"] = "success",
    latency_ms: int = 0,
    error: str | None = None,
    set_current_node: bool = True,
) -> dict[str, Any]:
    step = TraceRecorder.record(
        node=node,
        step_index=next_step_index(state),
        status=status,
        latency_ms=latency_ms,
        input_data=input_data,
        output_data=output_data,
        summary=summary,
        error=error,
    )
    update: dict[str, Any] = {"trace_steps": [step]}
    if set_current_node:
        update["current_node"] = node
    return update


def build_parallel_trace_update(
    state: AgentState,
    *,
    node: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    summary: str,
    status: Literal["success", "failed"] = "success",
    latency_ms: int = 0,
    error: str | None = None,
    detail_sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Append trace step for parallel fan-out nodes without writing current_node."""
    step = TraceRecorder.record(
        node=node,
        step_index=next_step_index(state),
        status=status,
        latency_ms=latency_ms,
        input_data=input_data,
        output_data=output_data,
        summary=summary,
        error=error,
    )
    if detail_sections:
        step["detail_sections"] = detail_sections
    return {"trace_steps": [step]}


async def run_node_with_trace(
    state: AgentState,
    *,
    node: str,
    input_data: dict[str, Any],
    summary: str,
    fn: Callable[[], Awaitable[tuple[dict[str, Any], str]]],
) -> dict[str, Any]:
    """Execute node logic and append a trace step."""
    emit_node_entry_status(state, node)
    started = time.perf_counter()
    try:
        output_data, step_summary = await fn()
        latency_ms = int((time.perf_counter() - started) * 1000)
        trace_update = build_trace_update(
            state,
            node=node,
            input_data=input_data,
            output_data=output_data,
            summary=step_summary or summary,
            status="success",
            latency_ms=latency_ms,
        )
        merged = {**output_data, **trace_update}
        emit_node_complete_status(state, node, merged)
        return merged
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        error_msg = str(exc)
        trace_update = build_trace_update(
            state,
            node=node,
            input_data=input_data,
            output_data={},
            summary=f"{summary}失败",
            status="failed",
            latency_ms=latency_ms,
            error=error_msg,
        )
        return {**trace_update, "error": error_msg}


_INTENT_TO_RESPONSE_KIND: dict[str, str] = {
    "hotspot_analysis": "hotspot",
    "data_query": "data",
    "stock_analysis": "stock",
    "document_qa": "data",
}


def response_kind_for_intent(intent_id: str) -> str:
    return _INTENT_TO_RESPONSE_KIND.get(intent_id, "data")


async def call_intent_json(
    llm: LLMService,
    *,
    system_prompt: str,
    user_payload: dict[str, Any],
    temperature: float = 0.1,
) -> dict[str, Any]:
    import json

    client = llm._intent_client()
    body = await client.chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        temperature=temperature,
        max_tokens=1024,
        json_mode=True,
    )
    return llm._parse_json_payload(client.extract_message_content(body))


def normalize_intent_id(value: Any) -> str:
    intent_id = str(value or "unknown").strip().lower()
    if intent_id not in _VALID_INTENT_IDS:
        return "unknown"
    return intent_id


def normalize_confidence(value: Any, default: float = 0.5) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, score))


def normalize_candidate_intents(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    candidates: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        intent_id = normalize_intent_id(item.get("intent_id"))
        candidates.append(
            {
                "intent_id": intent_id,
                "confidence": normalize_confidence(item.get("confidence")),
            }
        )
    return candidates


def intent_display_name(intent_id: str) -> str:
    return _INTENT_DISPLAY_NAMES.get(intent_id, intent_id)


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_slots(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in value.items() if v is not None and str(v).strip() != ""}


def normalize_slot_confidence(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key, raw in value.items():
        result[str(key)] = normalize_confidence(raw, default=0.0)
    return result


__all__ = [
    "LLMClientError",
    "build_parallel_trace_update",
    "build_trace_update",
    "call_intent_json",
    "intent_display_name",
    "normalize_candidate_intents",
    "normalize_confidence",
    "normalize_intent_id",
    "normalize_slot_confidence",
    "normalize_slots",
    "normalize_string_list",
    "next_step_index",
    "response_kind_for_intent",
    "run_node_with_trace",
]
