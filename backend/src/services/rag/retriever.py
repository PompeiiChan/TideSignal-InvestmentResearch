"""Hybrid dense + BM25 retrieval with parent-child expansion."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pycore.core import get_logger

from .bm25 import Bm25Index
from .index_store import StoredChunk
from .models import RagHit, RerankCandidateSnapshot

logger = get_logger()

if TYPE_CHECKING:
    from ...integrations.rerank.service import RerankService

RAG_SNIPPET_MAX_CHARS = 1200
RAG_CANDIDATE_POOL = 30
DEFAULT_TOP_K = 6
RERANK_TOP_N = 8
MIN_SCORE = 0.15
HYBRID_DENSE_WEIGHT = 0.65
HYBRID_BM25_WEIGHT = 0.35

FINANCIAL_QUERY_TERMS = (
    "财报",
    "一季报",
    "季报",
    "三季报",
    "年报",
    "营收",
    "净利润",
    "毛利率",
    "业绩",
    "财务",
    "收入",
    "利润",
    "基本面",
    "总资产",
    "资产规模",
    "净资产",
    "市值",
    "负债",
    "现金流",
    "资产负债表",
)
FINANCIAL_CONTENT_TERMS = (
    "营业收入",
    "净利润",
    "主要财务数据",
    "归属于上市公司股东的净利润",
    "毛利率",
    "基本每股收益",
    "业绩摘要",
)
METADATA_TABLE_RE = re.compile(r"^\|\s*字段\s*\|", re.MULTILINE)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return float(dot / (left_norm * right_norm))


def is_financial_query(query: str) -> bool:
    return any(term in query for term in FINANCIAL_QUERY_TERMS)


def is_metadata_only_chunk(text: str) -> bool:
    """Detect small metadata tables without substantive financial body."""
    stripped = text.strip()
    if not METADATA_TABLE_RE.search(stripped):
        return False
    return not any(term in stripped for term in FINANCIAL_CONTENT_TERMS)


def build_excerpt(chunk_text: str, *, max_chars: int = RAG_SNIPPET_MAX_CHARS) -> str:
    """Build a retrieval excerpt, preferring financial metric sections over headers."""
    text = chunk_text.strip()
    if len(text) <= max_chars:
        return text

    for marker in (
        "业绩摘要",
        "一、主要财务数据",
        "主要会计数据和财务指标",
        "营业收入",
        "归属于上市公司股东的净利润",
        "主要财务指标",
        "合并资产负债表",
        "合并利润表",
    ):
        idx = text.find(marker)
        if idx >= 0:
            return text[idx : idx + max_chars]

    return text[:max_chars]


def _financial_content_bonus(text: str) -> float:
    bonus = 0.0
    for term in FINANCIAL_CONTENT_TERMS:
        if term in text:
            bonus += 0.04
    if "2026Q1" in text or "2026 年第一季度" in text or "一季报" in text:
        bonus += 0.08
    if is_metadata_only_chunk(text):
        bonus -= 0.18
    return bonus


def _query_period_bonus(query: str, text: str) -> float:
    bonus = 0.0
    if "一季报" in query or "第一季度" in query:
        if "第一季度" in text or "2026Q1" in text or "一季报" in text or "业绩摘要" in text:
            bonus += 0.12
        if "2025年年度报告" in text and "第一季度" not in text:
            bonus -= 0.08
    if "年报" in query and ("年度报告" in text or "2025A" in text or "业绩摘要" in text):
        bonus += 0.08
    return bonus


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    max_score = max(scores.values())
    if max_score <= 0:
        return dict.fromkeys(scores, 0.0)
    return {key: value / max_score for key, value in scores.items()}


def _passes_metadata_filter(item: StoredChunk, filters: dict[str, str]) -> bool:
    company_id = filters.get("company_id", "")
    doc_type = filters.get("doc_type", "")
    path_prefix = filters.get("path_prefix", "")
    if company_id and item.chunk.company_id and item.chunk.company_id != company_id:
        return False
    if doc_type and item.chunk.doc_type and item.chunk.doc_type != doc_type:
        return False
    if path_prefix and not item.chunk.path.startswith(path_prefix):
        return False
    return True


def _eligible_chunks(chunks: list[StoredChunk], filters: dict[str, str] | None) -> list[StoredChunk]:
    active_filters = filters or {}
    eligible = [item for item in chunks if _passes_metadata_filter(item, active_filters)]
    if not eligible and active_filters.get("company_id"):
        eligible = chunks
    return eligible


def _hits_from_scored(
    query: str,
    scored: list[tuple[float, StoredChunk]],
    *,
    top_k: int,
    retrieval_mode: str,
) -> list[RagHit]:
    refined = refine_scored_hits(query, scored, top_k=top_k)
    hits: list[RagHit] = []
    for score, item in refined:
        context_text = _parent_context(item)
        snippet = build_excerpt(context_text)
        section = item.chunk.section_title or item.chunk.title
        hits.append(
            RagHit(
                chunk_id=item.chunk.chunk_id,
                doc_id=item.chunk.doc_id,
                title=item.chunk.title,
                source_type=item.chunk.source_type,
                path=item.chunk.path,
                score=round(score, 4),
                snippet=snippet,
                relevance_reason=f"{retrieval_mode} 命中 {score:.2f}，章节「{section}」",
                breadcrumb=item.chunk.breadcrumb,
                time_period=item.chunk.time_period,
                retrieval_mode=retrieval_mode,
            )
        )
    return hits


def _parent_context(item: StoredChunk) -> str:
    if item.chunk.parent_text.strip():
        return item.chunk.parent_text.strip()
    return item.chunk.chunk_text


def refine_scored_hits(
    query: str,
    scored: list[tuple[float, StoredChunk]],
    *,
    top_k: int = DEFAULT_TOP_K,
) -> list[tuple[float, StoredChunk]]:
    """Re-rank hybrid candidates with lightweight domain heuristics."""
    if not scored:
        return []

    financial_query = is_financial_query(query)
    adjusted: list[tuple[float, StoredChunk]] = []
    for score, item in scored:
        adjusted_score = score * item.chunk.retrieval_weight
        if financial_query:
            adjusted_score += _financial_content_bonus(item.chunk.chunk_text)
            adjusted_score += _query_period_bonus(query, item.chunk.chunk_text)
            if item.chunk.source_type == "financial":
                adjusted_score += 0.05
            if item.chunk.chunk_role == "summary":
                adjusted_score += 0.1
        adjusted.append((adjusted_score, item))

    adjusted.sort(key=lambda pair: pair[0], reverse=True)
    return adjusted[:top_k]


async def search_chunks_bm25_only(
    query: str,
    chunks: list[StoredChunk],
    *,
    top_k: int = DEFAULT_TOP_K,
    candidate_pool: int = RAG_CANDIDATE_POOL,
    filters: dict[str, str] | None = None,
    rerank_service: RerankService | None = None,
) -> tuple[list[RagHit], bool, list[RerankCandidateSnapshot], list[RerankCandidateSnapshot]]:
    """Return top-k BM25 hits when dense embedding is unavailable."""
    eligible = _eligible_chunks(chunks, filters)
    if not eligible:
        return [], False, [], []

    bm25 = Bm25Index.from_chunks(eligible)
    sparse_scores = _normalize_scores(bm25.score(query))
    ranked_ids = sorted(sparse_scores, key=lambda chunk_id: sparse_scores[chunk_id], reverse=True)[
        :candidate_pool
    ]
    chunk_by_id = {item.chunk.chunk_id: item for item in eligible}
    scored = [
        (sparse_scores[chunk_id], chunk_by_id[chunk_id])
        for chunk_id in ranked_ids
        if chunk_id in chunk_by_id and sparse_scores[chunk_id] > 0
    ]

    rerank_connected = False
    rerank_before: list[RerankCandidateSnapshot] = []
    rerank_after: list[RerankCandidateSnapshot] = []
    if rerank_service is not None and rerank_service.is_configured() and scored:
        rerank_pool_size = min(RERANK_TOP_N, len(scored))
        rerank_before = [
            RerankCandidateSnapshot(
                chunk_id=pair[1].chunk.chunk_id,
                title=pair[1].chunk.title,
                score=round(pair[0], 4),
            )
            for pair in scored[:rerank_pool_size]
        ]
        try:
            documents = [pair[1].chunk.text_for_embedding() for pair in scored]
            reranked = await rerank_service.rerank(query, documents, top_n=rerank_pool_size)
            rerank_connected = True
            reranked_scored: list[tuple[float, StoredChunk]] = []
            for index, score in reranked:
                if 0 <= index < len(scored):
                    item = scored[index][1]
                    reranked_scored.append((score, item))
                    rerank_after.append(
                        RerankCandidateSnapshot(
                            chunk_id=item.chunk.chunk_id,
                            title=item.chunk.title,
                            score=round(score, 4),
                        )
                    )
            if reranked_scored:
                scored = reranked_scored
        except Exception as exc:
            logger.warning("BM25 rerank failed, falling back to sparse order", detail=str(exc))
            rerank_connected = False

    mode = "rerank" if rerank_connected else "bm25"
    hits = _hits_from_scored(query, scored, top_k=top_k, retrieval_mode=mode)
    return hits, rerank_connected, rerank_before, rerank_after


async def search_chunks(
    query: str,
    query_vector: list[float],
    chunks: list[StoredChunk],
    *,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SCORE,
    candidate_pool: int = RAG_CANDIDATE_POOL,
    filters: dict[str, str] | None = None,
    rerank_service: RerankService | None = None,
) -> tuple[list[RagHit], bool, list[RerankCandidateSnapshot], list[RerankCandidateSnapshot]]:
    """Return top-k hybrid hits with optional rerank and parent expansion."""
    eligible = _eligible_chunks(chunks, filters)

    dense_scores: dict[str, float] = {}
    for item in eligible:
        score = cosine_similarity(query_vector, item.vector)
        if score >= min_score:
            dense_scores[item.chunk.chunk_id] = score

    bm25 = Bm25Index.from_chunks(eligible)
    sparse_scores = _normalize_scores(bm25.score(query))
    dense_norm = _normalize_scores(dense_scores)

    hybrid: dict[str, float] = {}
    for item in eligible:
        chunk_id = item.chunk.chunk_id
        dense = dense_norm.get(chunk_id, 0.0)
        sparse = sparse_scores.get(chunk_id, 0.0)
        if dense <= 0 and sparse <= 0:
            continue
        hybrid[chunk_id] = HYBRID_DENSE_WEIGHT * dense + HYBRID_BM25_WEIGHT * sparse

    ranked_ids = sorted(hybrid, key=lambda chunk_id: hybrid[chunk_id], reverse=True)[:candidate_pool]
    chunk_by_id = {item.chunk.chunk_id: item for item in eligible}
    scored = [(hybrid[chunk_id], chunk_by_id[chunk_id]) for chunk_id in ranked_ids if chunk_id in chunk_by_id]

    rerank_connected = False
    rerank_before: list[RerankCandidateSnapshot] = []
    rerank_after: list[RerankCandidateSnapshot] = []
    if rerank_service is not None and rerank_service.is_configured() and scored:
        rerank_pool_size = min(RERANK_TOP_N, len(scored))
        rerank_before = [
            RerankCandidateSnapshot(
                chunk_id=pair[1].chunk.chunk_id,
                title=pair[1].chunk.title,
                score=round(pair[0], 4),
            )
            for pair in scored[:rerank_pool_size]
        ]
        try:
            documents = [pair[1].chunk.text_for_embedding() for pair in scored]
            reranked = await rerank_service.rerank(query, documents, top_n=rerank_pool_size)
            rerank_connected = True
            reranked_scored: list[tuple[float, StoredChunk]] = []
            for index, score in reranked:
                if 0 <= index < len(scored):
                    item = scored[index][1]
                    reranked_scored.append((score, item))
                    rerank_after.append(
                        RerankCandidateSnapshot(
                            chunk_id=item.chunk.chunk_id,
                            title=item.chunk.title,
                            score=round(score, 4),
                        )
                    )
            if reranked_scored:
                scored = reranked_scored
        except Exception as exc:
            logger.warning("Rerank failed, falling back to hybrid order", detail=str(exc))
            rerank_connected = False

    mode = "rerank" if rerank_connected else "hybrid"
    hits = _hits_from_scored(query, scored, top_k=top_k, retrieval_mode=mode)
    return hits, rerank_connected, rerank_before, rerank_after
