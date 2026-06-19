"""rag_retrieval node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.langgraph.status_phases import (
    emit_node_complete_status,
    emit_node_entry_status,
)
from ...integrations.llm.service import LLMService
from ...services.hotspot_recency import extract_hotspot_month_keys
from ...services.rag.models import RagHit, RagRetrievalResult
from ...services.rag.retriever import filter_hits_by_entity, filter_stock_narrative_hits
from ...services.rag.service import (
    RagService,
    diversify_hits_by_time_period,
    diversify_hotspot_hits_by_month,
    hits_to_source_refs,
    merge_rag_hit_lists,
)
from ...settings import AppSettings
from ..stock_tool_plan import build_stock_narrative_rag_queries, is_qualitative_business_query
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

    supplement_mode = bool(state.get("supplement_mode"))
    supplement_queries = state.get("supplement_rag_queries") or []
    if not isinstance(supplement_queries, list):
        supplement_queries = []
    supplement_filters = state.get("supplement_rag_filters") or {}
    if not isinstance(supplement_filters, dict):
        supplement_filters = {}

    slots = state.get("active_slots") or state.get("slots") or {}
    if not isinstance(slots, dict):
        slots = {}
    stock_name = str(slots.get("stock_name", "")).strip()

    input_data = {
        "query": normalized_query,
        "retrieval_config": retrieval_config,
        "supplement_mode": supplement_mode,
        "supplement_queries": supplement_queries,
        "hotspot_evidence_mode": (plan.get("hotspot_evidence_mode") if isinstance(plan, dict) else ""),
        "active_slots": slots,
        "stock_name": stock_name,
    }

    stock_narrative_mode = bool(plan.get("stock_narrative_mode")) or retrieval_strategy == "stock_narrative"
    if supplement_mode and supplement_queries:
        if stock_narrative_mode:
            hit_groups: list = []
            narrative_result: RagRetrievalResult | None = None
            for query in [str(item) for item in supplement_queries if str(item).strip()]:
                scoped = await rag.retrieve_stock_narrative(
                    query,
                    top_k=max(top_k, 6),
                    stock_name=stock_name,
                )
                if narrative_result is None:
                    narrative_result = scoped
                hit_groups.append(scoped.hits)
            merged_hits = merge_rag_hit_lists(hit_groups, top_k=max(top_k, 8))
            merged_hits = filter_stock_narrative_hits(
                merged_hits,
                stock_name=stock_name,
                query=normalized_query,
            )
            rag_result = narrative_result or RagRetrievalResult(
                query=" | ".join(str(q) for q in supplement_queries if str(q).strip()),
                mode="stock_narrative_supplement",
            )
            rag_result.hits = merged_hits
            rag_result.query = " | ".join(str(q) for q in supplement_queries if str(q).strip())
            rag_result.mode = "stock_narrative_supplement"
        else:
            rag_result = await rag.retrieve_targeted(
                [str(query) for query in supplement_queries if str(query).strip()],
                top_k=max(top_k, 4),
                filters=supplement_filters,
                entity_name=stock_name,
            )
    elif retrieval_strategy == "hotspot_dual":
        slots = state.get("slots") or {}
        if not isinstance(slots, dict):
            slots = {}
        month_keys = retrieval_config.get("hotspot_month_keys")
        if not isinstance(month_keys, list) or len(month_keys) < 2:
            month_keys = extract_hotspot_month_keys(
                " ".join(
                    [
                        normalized_query,
                        str(slots.get("time_range", "")),
                        str(slots.get("topic", "")),
                    ]
                )
            )
        topic = str(slots.get("topic") or slots.get("industry") or "").strip()
        if isinstance(month_keys, list) and len(month_keys) >= 2:
            rag_result = await rag.retrieve_hotspot_multi_month(
                normalized_query,
                month_keys=[str(item) for item in month_keys if str(item).strip()],
                top_k=top_k,
                topic=topic,
            )
        else:
            rag_result = await rag.retrieve_hotspot(normalized_query, top_k=top_k)
            rag_result.hits = diversify_hotspot_hits_by_month(rag_result.hits, top_k=top_k)
    elif retrieval_strategy == "hotspot_industry_only":
        rag_result = await rag.retrieve_hotspot_industry_only(normalized_query, top_k=top_k)
    elif stock_narrative_mode or (
        state.get("route_target") == "stock_analysis_agent"
        and is_qualitative_business_query(query=normalized_query)
    ):
        scoped_result = await rag.retrieve_stock_narrative(
            normalized_query,
            top_k=max(top_k, 8),
            stock_name=stock_name,
        )
        narrative_queries = build_stock_narrative_rag_queries(
            query=normalized_query,
            stock_name=stock_name,
        )
        targeted_result = await rag.retrieve_targeted(
            narrative_queries,
            top_k=max(top_k, 8),
            entity_name=stock_name,
            narrative_strict=True,
            narrative_query=normalized_query,
        )
        merged_hits = merge_rag_hit_lists(
            [scoped_result.hits, targeted_result.hits],
            top_k=max(top_k, 10),
        )
        merged_hits = filter_stock_narrative_hits(
            merged_hits,
            stock_name=stock_name,
            query=normalized_query,
        )
        rag_result = scoped_result
        rag_result.hits = merged_hits
        rag_result.query = normalized_query
        rag_result.mode = "stock_narrative"
    else:
        rag_result = await rag.retrieve(normalized_query, top_k=top_k)
        if stock_name and len(normalized_query) <= 12:
            rag_result.hits = filter_hits_by_entity(rag_result.hits, stock_name)
        if state.get("route_target") == "stock_analysis_agent":
            rag_result.hits = diversify_hits_by_time_period(rag_result.hits, top_k=top_k)
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
        if retrieval_strategy == "hotspot_industry_only":
            summary = (
                f"近期口径：跳过热点月报，仅检索行业研报背景 {len(rag_hits)} 条，"
                f"最高相关：{rag_hits[0].get('title', '未知文档')}。"
            )
        elif stock_narrative_mode or rag_result.mode in {"stock_narrative", "stock_narrative_supplement"}:
            top_path = str(rag_hits[0].get("path", ""))
            scope_label = "公司/行业研报"
            if "company-reports/" in top_path:
                scope_label = "公司研报"
            elif "industry-reports/" in top_path:
                scope_label = "行业研报"
            elif "financials/" in top_path:
                scope_label = "年报"
            summary = (
                f"叙事类问股：优先检索研报/年报 {len(rag_hits)} 条，"
                f"主证据类型：{scope_label}，最高相关：{rag_hits[0].get('title', '未知文档')}。"
            )
        elif rag_result.rerank_connected:
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
        if stock_narrative_mode or rag_result.mode in {"stock_narrative", "stock_narrative_supplement"}:
            summary = "叙事类问股：未命中本地公司/行业研报片段，不得编造管线品种；请声明本地未收录。"
        elif retrieval_strategy == "hotspot_industry_only":
            summary = "近期口径：未命中行业研报背景，回答将主要依赖数据接口。"
        else:
            summary = "本轮未命中本地知识库片段。"
    if supplement_mode:
        if rag_hits:
            summary = f"定向补数检索：{summary}"
        else:
            summary = (
                f"定向补数检索：本地知识库未找到与「{stock_name or '标的'}」直接相关的文档，"
                "已跳过无关行业片段，避免污染证据。"
            )

    trace = build_parallel_trace_update(
        state,
        node="rag_retrieval",
        input_data=input_data,
        output_data={"rag_hits": rag_hits, **rag_result.to_trace_payload()},
        summary=summary,
        latency_ms=rag_result.latency_ms,
        detail_sections=_build_rag_detail_sections(rag_result, rag_hits),
    )
    result = {
        **trace,
        "retrieval_config": retrieval_config,
        "retrieved_chunks": retrieved_chunks,
        "retrieval_score": retrieval_score,
        "citations": citations,
        "low_confidence_flag": low_confidence_flag,
        "rag_hits": rag_hits,
    }
    emit_node_complete_status(state, "rag_retrieval", result)
    return result
