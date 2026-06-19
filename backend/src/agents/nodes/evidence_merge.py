"""evidence_merge node."""

from __future__ import annotations

from typing import Any, cast

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.service import LLMService
from ...services.consensus_valuation import lookup_consensus_valuation
from ...services.conversation_context import build_conversation_context
from ...services.evidence_gaps import merge_rag_hits, merge_tool_results
from ...services.rag.chunker import resolve_kb_root
from ...services.rag.company_index import is_kb_resolved_stock
from ...services.rag.service import RagService
from ...services.scenario_return import build_scenario_return_calculation, is_scenario_return_query
from ...settings import BACKEND_ROOT, AppSettings
from ._helpers import run_node_with_trace


def _detect_conflicts(
    tool_result: dict[str, Any] | None,
    retrieved_chunks: list[dict[str, Any]],
) -> list[str]:
    conflicts: list[str] = []
    if not retrieved_chunks and tool_result:
        conflicts.append("RAG 未命中但工具返回了数据，回答将标注数据来源差异")
    if retrieved_chunks and not tool_result:
        conflicts.append("工具未返回数据，回答将主要依赖知识库片段")
    return conflicts


async def evidence_merge(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Merge tool, RAG and sub-agent outputs into evidence_pack."""
    _ = (llm, rag, settings)
    agent_result = str(state.get("agent_result", "")).strip()
    raw_incoming_tool = state.get("tool_result")
    incoming_tool_result: dict[str, Any] = (
        cast(dict[str, Any], raw_incoming_tool) if isinstance(raw_incoming_tool, dict) else {}
    )
    incoming_rag_hits: list[dict[str, Any]] = [
        item for item in (state.get("rag_hits") or []) if isinstance(item, dict)
    ]
    retrieved_chunks = state.get("retrieved_chunks") or []
    citations = state.get("citations") or []
    evidence_list = state.get("evidence_list") or []
    analysis_dimensions = state.get("analysis_dimensions") or []
    data_table = state.get("data_table") or []
    supplement_mode = bool(state.get("supplement_mode"))
    force_supplement_done = bool(state.get("evidence_supplement_done"))
    active_slots = state.get("active_slots") or state.get("slots") or {}
    conversation_context = build_conversation_context(
        history_summary=str(state.get("history_summary", "")),
        active_slots=active_slots,
        inherited_slot_keys=state.get("inherited_slot_keys") or [],
        normalized_query=str(state.get("normalized_query", "")),
    )

    input_data = {
        "has_agent_result": bool(agent_result),
        "has_tool_result": bool(incoming_tool_result),
        "rag_chunk_count": len(retrieved_chunks),
        "supplement_mode": supplement_mode,
        "has_conversation_context": bool(conversation_context.get("has_context")),
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        if force_supplement_done and not incoming_rag_hits and not incoming_tool_result:
            existing_pack = state.get("evidence_pack") or {}
            output = {
                "evidence_pack": existing_pack,
                "citation_map": state.get("citation_map") or {},
                "conflict_points": state.get("conflict_points") or [],
                "accumulated_rag_hits": state.get("accumulated_rag_hits") or [],
                "accumulated_tool_result": state.get("accumulated_tool_result") or {},
                "evidence_supplement_done": True,
                "supplement_mode": False,
            }
            return output, "补数计划为空，沿用首轮证据"

        if supplement_mode:
            accumulated_rag = list(state.get("accumulated_rag_hits") or [])
            accumulated_tool = dict(state.get("accumulated_tool_result") or {})
            merged_rag_hits = merge_rag_hits(accumulated_rag, incoming_rag_hits)
            merged_tool_result = merge_tool_results(accumulated_tool, incoming_tool_result)
            supplement_done = True
            merge_label = "补数"
        else:
            supplement_done = False
            merged_rag_hits = list(incoming_rag_hits)
            merged_tool_result = dict(incoming_tool_result)
            multi_agent_mode = bool(state.get("multi_agent_mode"))
            stock_phase_done = bool(state.get("multi_agent_stock_phase_done"))
            if (
                multi_agent_mode
                and stock_phase_done
                and state.get("route_target") == "data_query_agent"
            ):
                accumulated_rag = list(state.get("accumulated_rag_hits") or [])
                accumulated_tool = dict(state.get("accumulated_tool_result") or {})
                merged_rag_hits = merge_rag_hits(accumulated_rag, incoming_rag_hits)
                merged_tool_result = merge_tool_results(accumulated_tool, incoming_tool_result)
                merge_label = "复合"
            else:
                merge_label = "首轮"

        merged_chunks = retrieved_chunks
        if supplement_mode and merged_rag_hits:
            merged_chunks = [
                {
                    "chunk_id": hit.get("chunk_id", ""),
                    "doc_id": hit.get("doc_id", ""),
                    "title": hit.get("title", ""),
                    "snippet": hit.get("snippet", ""),
                    "source_type": hit.get("source_type", ""),
                    "path": hit.get("path", ""),
                    "score": hit.get("score", 0),
                    "time_period": hit.get("time_period", ""),
                }
                for hit in merged_rag_hits
                if isinstance(hit, dict)
            ]

        conflict_points = _detect_conflicts(
            merged_tool_result if merged_tool_result else None,
            merged_chunks if isinstance(merged_chunks, list) else [],
        )
        citation_map: dict[str, Any] = {
            "rag_citations": citations,
            "doc_citations": state.get("doc_citations") or [],
        }
        for index, hit in enumerate(merged_rag_hits, start=1):
            citation_map[f"rag_{index}"] = hit

        execution_plan = state.get("execution_plan") or {}
        slots = active_slots
        scenario_mode = bool(
            execution_plan.get("scenario_return_mode")
            or slots.get("scenario_return_mode")
            or is_scenario_return_query(str(state.get("normalized_query", "")))
        )
        if scenario_mode and state.get("route_target") == "stock_analysis_agent":
            stock_name = str(slots.get("stock_name", ""))
            stock_code = str(slots.get("stock_code", ""))
            tool_result = merged_tool_result if isinstance(merged_tool_result, dict) else {}
            forecast = tool_result.get("consensus_valuation_lookup")
            if not isinstance(forecast, dict) or not forecast.get("found"):
                valuation_tool = tool_result.get("valuation_profile_lookup")
                current_price = None
                if isinstance(valuation_tool, dict):
                    valuation = valuation_tool.get("valuation")
                    if isinstance(valuation, dict):
                        price_raw = str(valuation.get("price", "")).replace("元", "").strip()
                        try:
                            current_price = float(price_raw)
                        except ValueError:
                            current_price = None
                forecast = lookup_consensus_valuation(
                    stock_name=stock_name,
                    stock_code=stock_code,
                    current_price=current_price,
                    rag_hits=merged_rag_hits,
                )
            merged_tool_result["consensus_valuation_lookup"] = forecast
            merged_tool_result["earnings_forecast_lookup"] = forecast
            share_count = int(slots.get("share_count") or 100)
            scenario_calc = build_scenario_return_calculation(
                valuation_tool=merged_tool_result.get("valuation_profile_lookup"),
                forecast_tool=forecast,
                rag_hits=merged_rag_hits,
                share_count=share_count,
            )
            if scenario_calc:
                merged_tool_result["local_return_calculator"] = scenario_calc

        agent_summary = agent_result
        multi_agent_mode = bool(state.get("multi_agent_mode"))
        stock_phase_done = bool(state.get("multi_agent_stock_phase_done"))
        if (
            multi_agent_mode
            and stock_phase_done
            and state.get("route_target") == "data_query_agent"
        ):
            summaries = dict(state.get("agent_summaries") or {})
            stock_summary = str(summaries.get("stock_analysis_agent", "")).strip()
            data_summary = agent_result
            if stock_summary and data_summary:
                agent_summary = f"【问股助手】\n{stock_summary}\n\n【问数助手】\n{data_summary}"
            elif stock_summary:
                agent_summary = stock_summary

        kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)
        stock_name = str(slots.get("stock_name", "")).strip()
        narrative_mode = bool(execution_plan.get("stock_narrative_mode"))
        kb_resolved = is_kb_resolved_stock(
            str(state.get("normalized_query", "")),
            slots,
            kb_root,
        )
        report_hits = [
            hit
            for hit in merged_rag_hits
            if isinstance(hit, dict)
            and str(hit.get("path", "")).startswith(("company-reports/", "industry-reports/"))
        ]

        evidence_pack: dict[str, Any] = {
            "agent_summary": agent_summary,
            "evidence_list": evidence_list,
            "analysis_dimensions": analysis_dimensions,
            "data_table": data_table,
            "tool_result": merged_tool_result,
            "retrieved_chunks": merged_chunks,
            "rag_hits": merged_rag_hits,
            "data_source": state.get("data_source", ""),
            "document_id": state.get("document_id", ""),
            "intent_id": state.get("intent_id", ""),
            "response_kind": state.get("response_kind", "data"),
            "evidence_round": 2 if supplement_done else 1,
            "hotspot_evidence_mode": execution_plan.get("hotspot_evidence_mode", ""),
            "hotspot_evidence_mode_reason": execution_plan.get("hotspot_evidence_mode_reason", ""),
            "scenario_return_mode": scenario_mode,
            "multi_agent_mode": multi_agent_mode,
            "agent_summaries": dict(state.get("agent_summaries") or {}),
            "stock_narrative_mode": narrative_mode,
            "stock_kb_uncovered": narrative_mode and not kb_resolved,
            "stock_narrative_evidence_missing": narrative_mode and not report_hits,
            "conversation_context": conversation_context,
            "active_slots": slots,
        }
        output = {
            "evidence_pack": evidence_pack,
            "citation_map": citation_map,
            "conflict_points": conflict_points,
            "accumulated_rag_hits": merged_rag_hits,
            "accumulated_tool_result": merged_tool_result,
            "rag_hits": merged_rag_hits,
            "tool_result": merged_tool_result,
            "retrieved_chunks": merged_chunks,
            "evidence_supplement_done": supplement_done,
            "supplement_mode": False,
        }
        if (
            multi_agent_mode
            and stock_phase_done
            and state.get("route_target") == "data_query_agent"
        ):
            output["multi_agent_data_phase_done"] = True
        chunk_count = len(merged_chunks) if isinstance(merged_chunks, list) else 0
        return output, f"{merge_label}聚合证据：RAG {chunk_count} 条，工具 {'有' if merged_tool_result else '无'}"

    return await run_node_with_trace(
        state,
        node="evidence_merge",
        input_data=input_data,
        summary="完成证据聚合",
        fn=_execute,
    )
