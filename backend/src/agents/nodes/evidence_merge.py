"""evidence_merge node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...settings import AppSettings
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
    tool_result = state.get("tool_result") or {}
    retrieved_chunks = state.get("retrieved_chunks") or []
    rag_hits = state.get("rag_hits") or []
    citations = state.get("citations") or []
    evidence_list = state.get("evidence_list") or []
    analysis_dimensions = state.get("analysis_dimensions") or []
    data_table = state.get("data_table") or []

    input_data = {
        "has_agent_result": bool(agent_result),
        "has_tool_result": bool(tool_result),
        "rag_chunk_count": len(retrieved_chunks),
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        conflict_points = _detect_conflicts(
            tool_result if isinstance(tool_result, dict) else None,
            retrieved_chunks if isinstance(retrieved_chunks, list) else [],
        )
        citation_map: dict[str, Any] = {
            "rag_citations": citations,
            "doc_citations": state.get("doc_citations") or [],
        }
        for index, hit in enumerate(rag_hits if isinstance(rag_hits, list) else [], start=1):
            citation_map[f"rag_{index}"] = hit

        evidence_pack: dict[str, Any] = {
            "agent_summary": agent_result,
            "evidence_list": evidence_list,
            "analysis_dimensions": analysis_dimensions,
            "data_table": data_table,
            "tool_result": tool_result,
            "retrieved_chunks": retrieved_chunks,
            "rag_hits": rag_hits,
            "data_source": state.get("data_source", ""),
            "document_id": state.get("document_id", ""),
            "intent_id": state.get("intent_id", ""),
            "response_kind": state.get("response_kind", "data"),
        }
        output = {
            "evidence_pack": evidence_pack,
            "citation_map": citation_map,
            "conflict_points": conflict_points,
        }
        chunk_count = len(retrieved_chunks) if isinstance(retrieved_chunks, list) else 0
        return output, f"聚合证据：RAG {chunk_count} 条，工具 {'有' if tool_result else '无'}"

    return await run_node_with_trace(
        state,
        node="evidence_merge",
        input_data=input_data,
        summary="完成证据聚合",
        fn=_execute,
    )
