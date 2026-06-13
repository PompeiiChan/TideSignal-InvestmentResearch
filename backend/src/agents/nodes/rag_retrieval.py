"""rag_retrieval node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.langgraph.status_phases import emit_node_entry_status
from ...integrations.llm.service import LLMService
from ...services.rag.models import RagHit, RagRetrievalResult
from ...services.rag.service import RagService, hits_to_source_refs
from ...settings import AppSettings
from ._helpers import build_parallel_trace_update


def _hits_to_chunks(hits: list[RagHit]) -> list[dict[str, Any]]:
    return [hit.model_dump() for hit in hits]


def _build_rag_detail_sections(rag_result: RagRetrievalResult, rag_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rerank_label = "已启用" if rag_result.rerank_connected else "未启用"
    if rag_result.rerank_before and not rag_result.rerank_connected:
        rerank_label = "调用失败，已降级 hybrid"
    if rag_hits:
        top_hit = rag_hits[0]
        detail_items = [
            {"label": "模式", "value": rag_result.mode},
            {"label": "Rerank", "value": rerank_label},
            {"label": "命中数", "value": str(len(rag_hits))},
            {"label": "文档标题", "value": str(top_hit.get("title", ""))},
            {"label": "来源类型", "value": str(top_hit.get("source_type", ""))},
            {"label": "相似度", "value": str(top_hit.get("score", ""))},
        ]
    else:
        detail_items = [
            {"label": "模式", "value": rag_result.mode},
            {"label": "Rerank", "value": rerank_label},
            {"label": "命中数", "value": "0"},
            {"label": "Embedding", "value": "已连接" if rag_result.embedding_connected else "未连接"},
        ]
    sections: list[dict[str, Any]] = [{"title": "检索状态", "items": detail_items}]
    if rag_result.rerank_before:
        sections.append(
            {
                "title": "重排前候选",
                "items": [
                    {
                        "label": f"#{index}",
                        "value": (
                            f"{item.title}（chunk_id={item.chunk_id}，hybrid_score={item.score}）"
                        ),
                    }
                    for index, item in enumerate(rag_result.rerank_before, start=1)
                ],
            }
        )
    if rag_result.rerank_after:
        sections.append(
            {
                "title": "重排后结果",
                "items": [
                    {
                        "label": f"#{index}",
                        "value": (
                            f"{item.title}（chunk_id={item.chunk_id}，rerank_score={item.score}）"
                        ),
                    }
                    for index, item in enumerate(rag_result.rerank_after, start=1)
                ],
            }
        )
    return sections


async def rag_retrieval(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Retrieve knowledge-base chunks via RagService."""
    emit_node_entry_status(state, "rag_retrieval")
    _ = (llm, settings)
    normalized_query = str(state.get("normalized_query", state.get("user_query", ""))).strip()
    plan = state.get("execution_plan") or {}
    retrieval_config = plan.get("retrieval_config") or {}
    if not isinstance(retrieval_config, dict):
        retrieval_config = {}
    top_k = int(retrieval_config.get("top_k", 8))
    retrieval_strategy = str(retrieval_config.get("strategy", "default"))

    input_data = {"query": normalized_query, "retrieval_config": retrieval_config}

    if retrieval_strategy == "hotspot_dual":
        rag_result = await rag.retrieve_hotspot(normalized_query, top_k=top_k)
    else:
        rag_result = await rag.retrieve(normalized_query, top_k=top_k)
    rag_hits = _hits_to_chunks(rag_result.hits)
    retrieved_chunks = [
        {
            "chunk_id": hit.chunk_id,
            "doc_id": hit.doc_id,
            "title": hit.title,
            "snippet": hit.snippet,
            "source_type": hit.source_type,
            "path": hit.path,
            "score": hit.score,
            "time_period": hit.time_period,
        }
        for hit in rag_result.hits
    ]
    citations = hits_to_source_refs(rag_result.hits)
    retrieval_score = rag_result.hits[0].score if rag_result.hits else 0.0
    low_confidence_flag = not rag_result.hits or retrieval_score < 0.5

    if rag_hits:
        if rag_result.rerank_connected:
            summary = (
                f"混合检索命中 {len(rag_hits)} 条本地知识库片段，"
                f"经 Rerank 重排后最高相关文档：{rag_hits[0].get('title', '未知文档')}。"
            )
        elif rag_result.rerank_before:
            summary = (
                f"混合检索命中 {len(rag_hits)} 条本地知识库片段，"
                f"Rerank 失败后降级 hybrid，最高相关文档：{rag_hits[0].get('title', '未知文档')}。"
            )
        else:
            summary = (
                f"语义检索命中 {len(rag_hits)} 条本地知识库片段，"
                f"最高相关文档：{rag_hits[0].get('title', '未知文档')}。"
            )
    else:
        summary = "本轮未命中本地知识库片段。"

    trace = build_parallel_trace_update(
        state,
        node="rag_retrieval",
        input_data=input_data,
        output_data={"rag_hits": rag_hits, **rag_result.to_trace_payload()},
        summary=summary,
        latency_ms=rag_result.latency_ms,
        detail_sections=_build_rag_detail_sections(rag_result, rag_hits),
    )
    return {
        **trace,
        "retrieval_config": retrieval_config,
        "retrieved_chunks": retrieved_chunks,
        "retrieval_score": retrieval_score,
        "citations": citations,
        "low_confidence_flag": low_confidence_flag,
        "rag_hits": rag_hits,
    }
