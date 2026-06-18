"""tool_call node."""

from __future__ import annotations

import time
from typing import Any, cast

from ...integrations.langgraph.state import AgentState
from ...integrations.langgraph.status_phases import emit_node_entry_status
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...settings import AppSettings
from ..data_query_tool_plan import resolve_data_query_tool_names
from ..hotspot_tool_plan import ranking_industry_param, resolve_hotspot_tool_names
from ..stock_tool_plan import resolve_stock_tool_names
from ..tools import TOOL_REGISTRY
from ._helpers import build_parallel_trace_update, normalize_slots


def _resolve_tool_names(state: AgentState) -> list[str]:
    if state.get("supplement_mode"):
        supplement_names = state.get("supplement_tool_names") or []
        return [str(name) for name in supplement_names if str(name).strip()]
    plan = state.get("execution_plan") or {}
    default_names = [str(name) for name in (plan.get("tool_names") or [])]
    if state.get("route_target") == "stock_analysis_agent":
        execution_plan = state.get("execution_plan") or {}
        slots = state.get("slots") or {}
        return resolve_stock_tool_names(
            state.get("agent_tool_names"),
            query=str(state.get("normalized_query", "")),
            analysis_dimensions=state.get("analysis_dimensions"),
            scenario_return_mode=bool(
                execution_plan.get("scenario_return_mode") or slots.get("scenario_return_mode")
            ),
        )
    if state.get("route_target") == "data_query_agent":
        return resolve_data_query_tool_names(
            state.get("agent_tool_names"),
            query=str(state.get("normalized_query", "")),
            slots=state.get("slots") or {},
        )
    if state.get("route_target") == "hotspot_agent":
        return resolve_hotspot_tool_names(
            state.get("agent_tool_names"),
            query=str(state.get("normalized_query", "")),
            slots=state.get("slots") or {},
            execution_plan=state.get("execution_plan") or {},
        )
    return default_names


async def tool_call(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Dispatch mock tools per execution_plan.tool_names."""
    emit_node_entry_status(state, "tool_call")
    _ = (llm, rag, settings)
    plan = state.get("execution_plan") or {}
    tool_names = _resolve_tool_names(state)
    tool_params = state.get("tool_params") or {}
    if not isinstance(tool_params, dict):
        tool_params = {}
    if state.get("supplement_mode"):
        plan = state.get("gap_enrichment_plan") or {}
        raw_plan_params = plan.get("tool_params")
        plan_params: dict[str, Any] = (
            cast(dict[str, Any], raw_plan_params) if isinstance(raw_plan_params, dict) else {}
        )
        tool_params = {**normalize_slots(state.get("slots") or {}), **plan_params}
    elif not tool_params:
        tool_params = normalize_slots(state.get("slots") or {})

    query = str(state.get("normalized_query", ""))
    if state.get("route_target") == "hotspot_agent":
        ranking_slots = {**(state.get("slots") or {}), **tool_params}
        ranking_industry = ranking_industry_param(query=query, slots=ranking_slots)
        if ranking_industry:
            tool_params.setdefault("industry", ranking_industry)
        tool_params.setdefault("metric", "涨幅排行")
        tool_params.setdefault("time_range", tool_params.get("time_range") or "近一交易日")
        tool_params.setdefault("rank_limit", 10)

    input_data = {
        "tool_names": tool_names,
        "tool_params": tool_params,
    }

    if not tool_names:
        trace = build_parallel_trace_update(
            state,
            node="tool_call",
            input_data=input_data,
            output_data={"tool_status": "skipped"},
            summary="无需工具调用，已跳过",
            latency_ms=0,
        )
        return {**trace, "tool_status": "skipped", "tool_latency": 0, "tool_error": None}

    started = time.perf_counter()
    merged_result: dict[str, Any] = {"tools": []}
    last_error: str | None = None
    status: str = "success"

    for tool_name in tool_names:
        tool_fn = TOOL_REGISTRY.get(str(tool_name))
        if tool_fn is None:
            status = "failed"
            last_error = f"未知工具: {tool_name}"
            merged_result["tools"].append(
                {"tool_name": tool_name, "status": "failed", "error": last_error}
            )
            continue
        try:
            call_params = dict(tool_params)
            if tool_name == "consensus_valuation_lookup":
                call_params["valuation_tool"] = merged_result.get("valuation_profile_lookup")
                call_params["rag_hits"] = state.get("rag_hits") or []
            result = tool_fn(**call_params)
            merged_result["tools"].append(
                {"tool_name": tool_name, "status": "success", "result": result}
            )
            merged_result[str(tool_name)] = result
        except Exception as exc:
            status = "failed"
            last_error = str(exc)
            merged_result["tools"].append(
                {"tool_name": tool_name, "status": "failed", "error": last_error}
            )

    latency_ms = int((time.perf_counter() - started) * 1000)
    tool_status = "success" if status == "success" else "failed"
    output_data = {
        "tool_status": tool_status,
        "tool_names": tool_names,
        "tool_result": merged_result,
        "tool_latency": latency_ms,
        "tool_error": last_error,
    }
    summary = (
        f"调用 {len(tool_names)} 个工具，状态 {tool_status}"
        if tool_status == "success"
        else f"工具调用失败：{last_error}"
    )
    trace = build_parallel_trace_update(
        state,
        node="tool_call",
        input_data=input_data,
        output_data=output_data,
        summary=summary,
        status="success" if tool_status == "success" else "failed",
        latency_ms=latency_ms,
        error=last_error,
    )
    return {
        **trace,
        "tool_params": tool_params,
        "tool_result": merged_result,
        "tool_status": tool_status,
        "tool_latency": latency_ms,
        "tool_error": last_error,
    }
