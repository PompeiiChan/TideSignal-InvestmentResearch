"""evidence_gap_check node — decide whether stock analysis needs a supplement fetch."""

from __future__ import annotations

from typing import Any, cast

from ...integrations.langgraph.state import AgentState
from ...integrations.langgraph.status_phases import emit_node_entry_status
from ...integrations.llm.service import LLMService
from ...services.evidence_gaps import detect_stock_evidence_gaps
from ...services.rag.service import RagService
from ...settings import AppSettings
from ._helpers import run_node_with_trace


async def evidence_gap_check(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Detect evidence gaps after the first stock-analysis evidence merge."""
    emit_node_entry_status(state, "evidence_gap_check")
    _ = (llm, rag, settings)

    evidence_pack = state.get("evidence_pack") or {}
    raw_tool_result = evidence_pack.get("tool_result")
    tool_result: dict[str, Any] = (
        cast(dict[str, Any], raw_tool_result) if isinstance(raw_tool_result, dict) else {}
    )
    rag_hits: list[dict[str, Any]] = [
        item for item in (evidence_pack.get("rag_hits") or []) if isinstance(item, dict)
    ]
    slots = state.get("slots") or {}
    stock_name = str(slots.get("stock_name", "")).strip()
    analysis_dimensions = state.get("analysis_dimensions") or evidence_pack.get("analysis_dimensions") or []

    input_data = {
        "route_target": state.get("route_target", ""),
        "stock_name": stock_name,
        "rag_hit_count": len(rag_hits),
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        gaps = detect_stock_evidence_gaps(
            tool_result=tool_result,
            rag_hits=rag_hits,
            analysis_dimensions=analysis_dimensions if isinstance(analysis_dimensions, list) else [],
            stock_name=stock_name,
            query=str(state.get("normalized_query", "")).strip(),
        )
        should_enrich = bool(gaps)
        output = {
            "should_enrich_evidence": should_enrich,
            "evidence_gaps": gaps,
        }
        if should_enrich:
            summary = f"检测到 {len(gaps)} 项证据缺口，准备定向补数"
        else:
            summary = "证据充分，无需补数"
        return output, summary

    return await run_node_with_trace(
        state,
        node="evidence_gap_check",
        input_data=input_data,
        summary="完成证据缺口判断",
        fn=_execute,
    )
