"""Unit and integration tests for local knowledge-base RAG."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from backend.src.integrations.embedding.service import EmbeddingService
from backend.src.services.rag.chunker import (
    chunk_knowledge_base,
    chunk_markdown_file,
    count_markdown_files,
    resolve_kb_root,
)
from backend.src.services.rag.index_store import IndexSnapshot, IndexStore, StoredChunk
from backend.src.services.rag.models import KnowledgeChunk
from backend.src.services.rag.retriever import (
    build_excerpt,
    cosine_similarity,
    is_financial_query,
    is_metadata_only_chunk,
    refine_scored_hits,
    search_chunks,
    search_chunks_bm25_only,
)
from backend.src.services.rag.service import RagNotReadyError, RagService
from backend.src.settings import BACKEND_ROOT, AppSettings


@pytest.fixture
def kb_root() -> Path:
    return resolve_kb_root("data/knowledge-base", BACKEND_ROOT)


@pytest.fixture
def live_rag_service(kb_root: Path, tmp_path: Path) -> RagService:
    """Use the real on-disk index when available to avoid rebuilding during REAL_API_TEST."""
    service = RagService()
    service.kb_root = kb_root
    real_store = IndexStore(kb_root)
    service.store = real_store if real_store.is_complete() else IndexStore(tmp_path)
    return service


def test_count_markdown_files_matches_repository(kb_root: Path) -> None:
    assert count_markdown_files(kb_root) == 86


def test_chunk_markdown_file_splits_by_section(kb_root: Path) -> None:
    sample = kb_root / "hotspots" / "2026-06-market-hotspots.md"
    chunks = chunk_markdown_file(sample, kb_root)
    assert chunks
    assert chunks[0].source_type == "market"
    assert chunks[0].title.startswith("2026 年 6 月")
    assert all(len(chunk.chunk_text) >= 80 for chunk in chunks if chunk.chunk_role != "summary")
    driver_chunks = [chunk for chunk in chunks if chunk.section_title == "多因素驱动"]
    assert driver_chunks
    assert "热点主线" in driver_chunks[0].breadcrumb
    assert driver_chunks[0].parent_text


def test_source_type_mapping_for_four_categories(kb_root: Path) -> None:
    mappings = {
        "hotspots/2026-06-market-hotspots.md": "market",
        "financials/300750-ningdeshidai-financial-2025A-2026Q1.md": "financial",
        "industry-reports/baijiu-industry-report-2026.md": "report",
        "company-reports/300750-ningdeshidai-company-report-2026.md": "report",
        "structured-data/companies.md": "knowledge",
    }
    for relative, expected in mappings.items():
        chunks = chunk_markdown_file(kb_root / relative, kb_root)
        assert chunks
        assert chunks[0].source_type == expected


@pytest.mark.asyncio
async def test_cosine_similarity_and_search_chunks() -> None:
    stored = [
        StoredChunk(
            chunk=KnowledgeChunk(
                chunk_id="a",
                doc_id="doc-a",
                title="热点文档",
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
                chunk_id="b",
                doc_id="doc-b",
                title="财报文档",
                source_type="financial",
                path="financials/b.md",
                chunk_text="营业收入同比增长。",
                embed_text="营业收入同比增长。",
                section_title="财务",
            ),
            vector=[0.0, 1.0, 0.0],
        ),
    ]
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)
    hits, _rerank_connected, _before, _after = await search_chunks(
        "机器人板块政策催化",
        [0.95, 0.05, 0.0],
        stored,
        top_k=1,
    )
    assert len(hits) == 1
    assert hits[0].title == "热点文档"
    assert hits[0].score > 0.5


def test_build_excerpt_prefers_financial_metrics() -> None:
    text = (
        "| 字段 | 内容 |\n|---|---|\n| doc_id | q1_603288_2026 |\n\n"
        "[page 1]\n一、主要财务数据\n营业收入 9,028,967,209.89\n"
        "归属于上市公司股东的净利润 2,443,715,832.21\n"
    )
    long_text = text + ("补充说明。" * 80)
    excerpt = build_excerpt(long_text, max_chars=200)
    assert "营业收入" in excerpt
    assert "9,028" in excerpt
    assert excerpt.startswith("一、主要财务数据")


def test_haitian_q1_chunks_split_by_page(kb_root: Path) -> None:
    sample = kb_root / "financials" / "603288-haitianweiye-financial-2025A-2026Q1.md"
    chunks = chunk_markdown_file(sample, kb_root)
    q1_metrics = [
        chunk
        for chunk in chunks
        if chunk.doc_id == "q1_603288_2026"
        and ("90.29亿元" in chunk.chunk_text or "营业收入 9,028,967,209.89" in chunk.chunk_text)
    ]
    assert q1_metrics, "Q1 revenue metrics should remain retrievable after financial chunking"
    assert not is_metadata_only_chunk(q1_metrics[0].chunk_text)
    balance_sheets = [
        chunk for chunk in chunks if chunk.doc_id.startswith("ann_") and chunk.section_title == "合并资产负债表"
    ]
    assert balance_sheets
    assert "货币资金" in balance_sheets[0].chunk_text


def test_refine_scored_hits_prefers_financial_metrics() -> None:
    metadata = StoredChunk(
        chunk=KnowledgeChunk(
            chunk_id="meta",
            doc_id="ann_603288_2025",
            title="海天味业2025年年度报告",
            source_type="financial",
            path="financials/a.md",
            chunk_text="| 字段 | 内容 |\n|---|---|\n| doc_id | ann_603288_2025 |",
            section_title="2025年报",
        ),
        vector=[1.0, 0.0],
    )
    metrics = StoredChunk(
        chunk=KnowledgeChunk(
            chunk_id="q1",
            doc_id="q1_603288_2026",
            title="海天味业2026年第一季度报告",
            source_type="financial",
            path="financials/a.md",
            chunk_text="一、主要财务数据\n营业收入 9,028,967,209.89\n归属于上市公司股东的净利润 2,443,715,832.21",
            section_title="2026 年第一季度报告",
        ),
        vector=[0.95, 0.05],
    )
    refined = refine_scored_hits(
        "海天味业2026年的一季报怎么样",
        [(0.73, metadata), (0.72, metrics)],
        top_k=1,
    )
    assert refined[0][1].chunk.chunk_id == "q1"


def test_index_store_checkpoint_append(tmp_path: Path) -> None:
    store = IndexStore(tmp_path)
    chunk = KnowledgeChunk(
        chunk_id="c1",
        doc_id="doc",
        title="标题",
        source_type="market",
        path="hotspots/a.md",
        chunk_text="机器人板块政策催化与订单预期提升，包含足够长度的正文片段。",
        section_title="热点",
    )
    store.start_build(
        embedding_model="mock",
        embedding_dim=2,
        file_fingerprints={"hotspots/a.md": "fp"},
        total_expected=2,
    )
    store.append_batch([StoredChunk(chunk=chunk, vector=[1.0, 0.0])])
    assert store.has_partial_build()
    store.append_batch(
        [
            StoredChunk(
                chunk=KnowledgeChunk(
                    chunk_id="c2",
                    doc_id="doc",
                    title="标题",
                    source_type="market",
                    path="hotspots/a.md",
                    chunk_text="第二段正文用于验证 jsonl 断点追加不会覆盖已有向量记录。",
                    section_title="热点",
                ),
                vector=[0.0, 1.0],
            )
        ]
    )
    store.finalize_build(file_fingerprints={"hotspots/a.md": "fp"})
    snapshot = store.load()
    assert snapshot is not None
    assert len(snapshot.chunks) == 2


@pytest.mark.asyncio
async def test_search_chunks_bm25_only_finds_financial_chunk() -> None:
    stored = [
        StoredChunk(
            chunk=KnowledgeChunk(
                chunk_id="q1_luolai",
                doc_id="q1_002293_2026",
                title="罗莱生活2026年第一季度报告",
                source_type="financial",
                path="financials/002293.md",
                chunk_text="一、主要财务数据\n营业收入11.58亿元，同比5.87%\n归母净利润1.48亿元，同比30.54%",
                embed_text="罗莱生活 2026Q1 一季报 营业收入 净利润",
                section_title="2026 年第一季度报告",
                company_id="company_002293",
                doc_type="quarterly_report",
                time_period="2026Q1",
            ),
            vector=[0.0, 0.0],
        ),
        StoredChunk(
            chunk=KnowledgeChunk(
                chunk_id="noise",
                doc_id="hotspot",
                title="市场热点",
                source_type="market",
                path="hotspots/a.md",
                chunk_text="机器人板块政策催化。",
                embed_text="机器人板块政策催化。",
            ),
            vector=[1.0, 0.0],
        ),
    ]
    hits, rerank_connected, _before, _after = await search_chunks_bm25_only(
        "罗莱生活2026年一季报分析",
        stored,
        top_k=1,
        filters={"company_id": "company_002293", "doc_type": "quarterly_report"},
    )
    assert not rerank_connected
    assert len(hits) == 1
    assert hits[0].doc_id == "q1_002293_2026"
    assert "11.58" in hits[0].snippet or "营业收入" in hits[0].snippet


@pytest.mark.asyncio
async def test_retrieve_bm25_fallback_without_embedding_config(live_rag_service: RagService) -> None:
    service = live_rag_service
    if not service.store.is_complete():
        pytest.skip("本地知识库索引不存在")
    service.is_embedding_configured = lambda: False  # type: ignore[method-assign]
    result = await service.retrieve("罗莱生活2026年一季报分析", top_k=6)
    assert result.mode == "bm25"
    assert result.embedding_connected is False
    assert result.hits
    assert any(hit.doc_id == "q1_002293_2026" for hit in result.hits)
    joined = "\n".join(hit.snippet for hit in result.hits)
    assert "营业收入" in joined or "11.58" in joined


@pytest.mark.asyncio
async def test_retrieve_degrades_when_index_unavailable(kb_root: Path, tmp_path: Path) -> None:
    service = RagService(AppSettings(local_kb_path=str(kb_root)))
    service.kb_root = kb_root
    service.store = IndexStore(tmp_path)
    service.is_embedding_configured = lambda: True  # type: ignore[method-assign]

    async def fail_index(force: bool = False) -> IndexSnapshot:
        raise RagNotReadyError("索引不可用")

    service.ensure_index = fail_index  # type: ignore[method-assign]
    result = await service.retrieve("机器人板块最近有哪些政策催化")
    assert result.mode == "mock"
    assert result.embedding_connected is False


@pytest.mark.asyncio
async def test_rag_service_retrieve_with_mocked_embedding(kb_root: Path, tmp_path: Path) -> None:
    settings = AppSettings(local_kb_path=str(kb_root))
    service = RagService(settings)
    service.kb_root = kb_root
    service.store = IndexStore(tmp_path)

    chunks = chunk_knowledge_base(kb_root)[:3]
    vectors = [[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]]
    service.store.save(
        embedding_model="mock-model",
        embedding_dim=2,
        file_fingerprints={"hotspots/a.md": "fp"},
        chunks=[StoredChunk(chunk=chunk, vector=vector) for chunk, vector in zip(chunks, vectors, strict=True)],
    )
    service.embedding.embed_text = AsyncMock(return_value=([0.95, 0.05], {"latency_ms": 10}))  # type: ignore[method-assign]
    service.is_embedding_configured = lambda: True  # type: ignore[method-assign]
    loaded = service.store.load()
    assert loaded is not None

    async def ensure_index(force: bool = False) -> IndexSnapshot:
        return loaded

    service.ensure_index = ensure_index  # type: ignore[method-assign]

    result = await service.retrieve("机器人板块最近有哪些政策催化", top_k=2)
    assert result.embedding_connected is True
    assert result.hits
    assert result.hits[0].source_type in {"market", "financial", "report", "knowledge"}


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("REAL_API_TEST") != "1", reason="REAL_API_TEST=1 required for live embedding smoke")
async def test_rag_service_real_embedding_smoke(live_rag_service: RagService) -> None:
    service = live_rag_service
    if not EmbeddingService().is_configured():
        pytest.skip("Embedding 配置不完整")
    if not service.store.is_complete():
        await service.ensure_index(force=True)
    result = await service.retrieve("2026年6月A股市场热点有哪些", top_k=3)
    assert result.embedding_connected is True
    assert result.hits
    assert any(hit.source_type == "market" for hit in result.hits)


@pytest.mark.parametrize(
    ("query", "expected_source_type"),
    [
        ("2026年6月A股市场热点有哪些", "market"),
        ("宁德时代2025年报营收和利润表现如何", "financial"),
        ("白酒行业2026年行业研报怎么看", "report"),
        ("海天味业2026年公司研报核心观点", "report"),
        ("海天味业2026年的一季报怎么样", "financial"),
    ],
)
@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("REAL_API_TEST") != "1", reason="REAL_API_TEST=1 required for live retrieval cases")
async def test_rag_category_hit_cases(
    live_rag_service: RagService,
    query: str,
    expected_source_type: str,
) -> None:
    service = live_rag_service
    if not EmbeddingService().is_configured():
        pytest.skip("Embedding 配置不完整")
    if not service.store.is_complete():
        await service.ensure_index(force=True)
    result = await service.retrieve(query, top_k=6)
    assert result.hits
    assert any(hit.source_type == expected_source_type for hit in result.hits)
    if "一季报" in query:
        joined = "\n".join(hit.snippet for hit in result.hits)
        assert "营业收入" in joined or "9,028" in joined


@pytest.mark.parametrize(
    "query",
    [
        "宁德时代基本面怎么样",
        "宁德时代总资产多少",
        "宁德时代资产规模和市值",
    ],
)
def test_is_financial_query_covers_stock_fundamentals(query: str) -> None:
    assert is_financial_query(query)


def test_catl_q1_chunk_total_assets_not_understated() -> None:
    kb_root = resolve_kb_root("data/knowledge-base", BACKEND_ROOT)
    path = kb_root / "financials/300750-ningdeshidai-financial-2025A-2026Q1.md"
    chunks = chunk_markdown_file(path, kb_root)
    q1_asset_chunks = [
        chunk
        for chunk in chunks
        if "总资产（千元）" in chunk.chunk_text or "资产总计" in chunk.chunk_text
    ]
    assert q1_asset_chunks
    joined = "\n".join(chunk.chunk_text for chunk in q1_asset_chunks)
    assert "10463.29亿元" in joined or "9748.28亿元" in joined
    assert "总资产（千元） 10.46亿元" not in joined
    assert "资产总计     10.46亿元" not in joined
