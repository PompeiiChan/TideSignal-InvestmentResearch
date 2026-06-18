"""gap_planner node — build targeted supplement plan for stock evidence gaps."""

from __future__ import annotations

from typing import Any, cast

from ...integrations.langgraph.state import AgentState
from ...integrations.langgraph.status_phases import emit_node_entry_status
from ...integrations.llm.service import LLMService
from ...services.evidence_gaps import build_gap_enrichment_plan
from ...services.rag.service import RagService
from ...settings import AppSettings
from ._helpers import run_node_with_trace


async def gap_planner(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Plan targeted RAG queries and optional tool calls for detected gaps."""
    emit_node_entry_status(state, "gap_planner")
    _ = (llm, rag, settings)

    gaps = state.get("evidence_gaps") or []
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
    stock_code = str(slots.get("stock_code", "")).strip()
    analysis_dimensions = state.get("analysis_dimensions") or evidence_pack.get("analysis_dimensions") or []

    input_data = {
        "gap_count": len(gaps),
        "stock_name": stock_name,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        plan = build_gap_enrichment_plan(
            gaps if isinstance(gaps, list) else [],
            stock_name=stock_name,
            stock_code=stock_code,
            analysis_dimensions=analysis_dimensions if isinstance(analysis_dimensions, list) else [],
            existing_tool_result=tool_result,
            existing_rag_hits=rag_hits,
            query=str(state.get("normalized_query", "")).strip(),
        )
        has_work = bool(plan.get("rag_queries")) or bool(plan.get("tool_names"))
        output = {
            "gap_enrichment_plan": plan,
            "supplement_mode": has_work,
            "supplement_rag_queries": plan.get("rag_queries") or [],
            "supplement_rag_filters": plan.get("rag_filters") or {},
            "supplement_tool_names": plan.get("tool_names") or [],
            "should_enrich_evidence": has_work,
        }
        if not has_work:
            output["evidence_supplement_done"] = True
            return output, "缺口已识别，但当前无可用补数动作，跳过补数"
        query_count = len(plan.get("rag_queries") or [])
        tool_count = len(plan.get("tool_names") or [])
        return output, f"生成补数计划：RAG {query_count} 条查询，工具 {tool_count} 个"

    return await run_node_with_trace(
        state,
        node="gap_planner",
        input_data=input_data,
        summary="完成补数规划",
        fn=_execute,
    )
