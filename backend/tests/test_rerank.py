"""Unit tests for RAG rerank observability and fallback."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.integrations.rerank.service import RerankService
from backend.src.services.rag.index_store import IndexSnapshot, StoredChunk
from backend.src.services.rag.models import KnowledgeChunk, RerankCandidateSnapshot
from backend.src.services.rag.retriever import search_chunks
from backend.src.services.rag.service import RagService
from backend.src.services.trace_service import TraceService
from backend.src.settings import AppSettings


def _stored_chunks() -> list[StoredChunk]:
    return [
        StoredChunk(
            chunk=KnowledgeChunk(
                chunk_id="chunk-a",
                doc_id="doc-a",
                title="热点文档 A",
                source_type="market",
                path="hotspots/a.md",
                chunk_text="机器人板块政策催化与订单预期提升。",
                embed_text="机器人板块政策催化与订单预期提升。",
                section_title="热点",
            ),
            vector=[1.0, 0.0, 0.0],
        ),
        StoredChunk(
            chunk=KnowledgeChunk(
                chunk_id="chunk-b",
                doc_id="doc-b",
                title="财报文档 B",
                source_type="financial",
                path="financials/b.md",
                chunk_text="营业收入同比增长，净利润改善。",
                embed_text="营业收入同比增长，净利润改善。",
                section_title="财务",
            ),
            vector=[0.9, 0.1, 0.0],
        ),
        StoredChunk(
            chunk=KnowledgeChunk(
                chunk_id="chunk-c",
                doc_id="doc-c",
                title="行业研报 C",
                source_type="report",
                path="reports/c.md",
                chunk_text="白酒行业景气度与渠道库存分析。",
                embed_text="白酒行业景气度与渠道库存分析。",
                section_title="行业",
            ),
            vector=[0.8, 0.2, 0.0],
        ),
    ]


class _MockRerankService:
    def is_configured(self) -> bool:
        return True

    async def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[tuple[int, float]]:
        del query
        return [(len(documents) - 1 - index, 0.95 - index * 0.1) for index in range(top_n)]


@pytest.mark.asyncio
async def test_search_chunks_records_rerank_before_and_after() -> None:
    stored = _stored_chunks()
    hits, rerank_connected, rerank_before, rerank_after = await search_chunks(
        "机器人板块政策催化",
        [0.95, 0.05, 0.0],
        stored,
        top_k=2,
        rerank_service=_MockRerankService(),  # type: ignore[arg-type]
    )
    assert rerank_connected is True
    assert len(rerank_before) >= 2
    assert len(rerank_after) >= 2
    assert rerank_before[0].chunk_id != rerank_after[0].chunk_id
    assert all(isinstance(item, RerankCandidateSnapshot) for item in rerank_before)
    assert hits
    assert hits[0].retrieval_mode == "rerank"


@pytest.mark.asyncio
@patch("backend.src.services.rag.retriever.logger.warning")
async def test_search_chunks_rerank_failure_falls_back_with_warning(mock_warning: MagicMock) -> None:
    stored = _stored_chunks()

    class _FailingRerankService:
        def is_configured(self) -> bool:
            return True

        async def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[tuple[int, float]]:
            del query, documents, top_n
            raise RuntimeError("upstream rerank unavailable")

    hits, rerank_connected, rerank_before, rerank_after = await search_chunks(
        "机器人板块政策催化",
        [0.95, 0.05, 0.0],
        stored,
        top_k=2,
        rerank_service=_FailingRerankService(),  # type: ignore[arg-type]
    )
    assert rerank_connected is False
    assert rerank_before
    assert rerank_after == []
    assert hits
    assert hits[0].retrieval_mode == "hybrid"
    mock_warning.assert_called_once()
    assert "Rerank failed" in mock_warning.call_args.args[0]


@pytest.mark.asyncio
async def test_rag_service_retrieve_propagates_rerank_snapshots() -> None:
    service = RagService(AppSettings())
    stored = _stored_chunks()
    service.embedding.embed_text = AsyncMock(return_value=([0.95, 0.05, 0.0], {"latency_ms": 5}))  # type: ignore[method-assign]
    service.is_embedding_configured = lambda: True  # type: ignore[method-assign]
    service.rerank = _MockRerankService()  # type: ignore[assignment]

    snapshot = IndexSnapshot(
        version=6,
        embedding_model="mock",
        embedding_dim=3,
        built_at="2026-06-12T00:00:00+08:00",
        file_fingerprints={"a.md": "fp"},
        chunks=stored,
        build_in_progress=False,
    )

    async def ensure_index(force: bool = False) -> IndexSnapshot:
        del force
        return snapshot

    service.ensure_index = ensure_index  # type: ignore[method-assign]

    result = await service.retrieve("机器人板块政策催化", top_k=2)
    assert result.rerank_connected is True
    assert result.rerank_before
    assert result.rerank_after
    payload = result.to_trace_payload()
    assert "rerank_before" in payload
    assert "rerank_after" in payload
    assert payload["rerank_before"][0]["chunk_id"]


def test_trace_rag_step_exposes_rerank_sections() -> None:
    from backend.src.services.rag.models import RagHit, RagRetrievalResult

    rag_result = RagRetrievalResult(
        hits=[
            RagHit(
                chunk_id="chunk-c",
                doc_id="doc-c",
                title="行业研报 C",
                source_type="report",
                path="reports/c.md",
                score=0.91,
                snippet="snippet",
                relevance_reason="rerank 命中",
                retrieval_mode="rerank",
            )
        ],
        latency_ms=120,
        embedding_connected=True,
        rerank_connected=True,
        mode="hybrid",
        rerank_before=[
            RerankCandidateSnapshot(chunk_id="chunk-a", title="热点文档 A", score=0.88),
            RerankCandidateSnapshot(chunk_id="chunk-b", title="财报文档 B", score=0.82),
        ],
        rerank_after=[
            RerankCandidateSnapshot(chunk_id="chunk-c", title="行业研报 C", score=0.95),
            RerankCandidateSnapshot(chunk_id="chunk-a", title="热点文档 A", score=0.71),
        ],
    )
    step = TraceService.__new__(TraceService)._rag_step(
        "机器人板块",
        rag_result,
        [hit.model_dump() for hit in rag_result.hits],
    )
    titles = [section["title"] for section in step["detail_sections"]]
    assert "重排前候选" in titles
    assert "重排后结果" in titles
    assert "Rerank" in step["detail_sections"][0]["items"][1]["label"]
    assert "经 Rerank 重排" in step["summary"]
    assert step["raw_json"]["rerank_before"]
    assert step["raw_json"]["rerank_after"]


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("REAL_API_TEST") != "1", reason="REAL_API_TEST=1 required for live rerank smoke")
async def test_rerank_service_real_api_smoke() -> None:
    service = RerankService()
    if not service.is_configured():
        pytest.skip("Rerank 配置不完整")
    ranked = await service.rerank(
        "机器人板块政策催化",
        ["机器人订单预期提升", "白酒行业库存分析"],
        top_n=2,
    )
    assert ranked
    assert all(isinstance(index, int) and isinstance(score, float) for index, score in ranked)
