"""High-level local knowledge-base RAG service."""

from __future__ import annotations

import asyncio
import re
import time

from pycore.core import get_logger

from ...integrations.embedding.client import EmbeddingClientError
from ...integrations.embedding.service import EmbeddingNotConfiguredError, EmbeddingService
from ...integrations.rerank.service import RerankService
from ...settings import BACKEND_ROOT, AppSettings, get_settings
from ..system_time import SystemTimeContext, resolve_system_time
from .chunker import (
    RAG_INDEX_VERSION,
    chunk_knowledge_base,
    count_markdown_files,
    file_fingerprint,
    list_markdown_files,
    resolve_kb_root,
)
from .company_index import load_company_aliases, resolve_query_filters
from .index_store import IndexSnapshot, IndexStore, StoredChunk
from .models import KnowledgeChunk, RagHit, RagRetrievalResult
from .retriever import (
    HOTSPOT_MIN_SCORE,
    filter_hits_by_entity,
    filter_hits_by_min_score,
    filter_stock_narrative_hits,
    search_chunks,
    search_chunks_bm25_only,
)

logger = get_logger()

_BUILD_LOCK = asyncio.Lock()
_EMBED_BATCH_SIZE = 4


def merge_rag_hit_lists(hit_groups: list[list[RagHit]], *, top_k: int) -> list[RagHit]:
    """Merge multiple hit lists by chunk_id, keeping the highest score."""
    merged: dict[str, RagHit] = {}
    for hits in hit_groups:
        for hit in hits:
            existing = merged.get(hit.chunk_id)
            if existing is None or hit.score > existing.score:
                merged[hit.chunk_id] = hit
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)[: max(top_k, 1)]


def _company_key_from_hit(hit: RagHit) -> str:
    doc_id = hit.doc_id.strip()
    match = re.match(r"(?:ann|q1|q)_(\d{6})_", doc_id)
    if match:
        return match.group(1)
    path_match = re.search(r"(\d{6})", hit.path)
    if path_match:
        return path_match.group(1)
    return doc_id or hit.path


def _is_financial_hit(hit: RagHit) -> bool:
    normalized_path = hit.path.replace("\\", "/")
    return hit.source_type == "financial" or "/financials/" in normalized_path


def diversify_hits_by_time_period(hits: list[RagHit], *, top_k: int) -> list[RagHit]:
    """Prefer one high-score chunk per (company, time_period) for financial evidence."""
    if len(hits) <= 1:
        return hits[:top_k]

    ranked = sorted(hits, key=lambda item: item.score, reverse=True)
    financial_hits = [hit for hit in ranked if _is_financial_hit(hit)]
    if len(financial_hits) < 2:
        return ranked[:top_k]

    best_by_period: dict[tuple[str, str], RagHit] = {}
    for hit in financial_hits:
        period = hit.time_period.strip() or hit.doc_id or hit.chunk_id
        company_key = _company_key_from_hit(hit)
        bucket = (company_key, period)
        existing = best_by_period.get(bucket)
        if existing is None or hit.score > existing.score:
            best_by_period[bucket] = hit

    if len(best_by_period) < 2:
        return ranked[:top_k]

    diversified = sorted(best_by_period.values(), key=lambda item: item.score, reverse=True)
    selected_ids = {hit.chunk_id for hit in diversified}
    merged = diversified + [hit for hit in ranked if hit.chunk_id not in selected_ids]
    return merged[:top_k]


class RagNotReadyError(RuntimeError):
    """Raised when embedding configuration or index is unavailable."""


class RagService:
    """Build, cache and query the local markdown knowledge base."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.embedding = EmbeddingService(self.settings)
        self.rerank = RerankService(self.settings)
        self.kb_root = resolve_kb_root(self.settings.local_kb_path, BACKEND_ROOT)
        self.store = IndexStore(self.kb_root)
        self._snapshot: IndexSnapshot | None = None
        self._company_aliases = load_company_aliases(self.kb_root)

    def kb_display_path(self) -> str:
        configured = self.settings.local_kb_path.strip() or "data/knowledge-base"
        return configured.strip("/")

    def markdown_file_count(self) -> int:
        return count_markdown_files(self.kb_root)

    def kb_breakdown(self) -> dict[str, int]:
        """Return markdown counts per knowledge-base subdirectory."""
        breakdown: dict[str, int] = {}
        for path in list_markdown_files(self.kb_root):
            folder = path.relative_to(self.kb_root).parts[0]
            breakdown[folder] = breakdown.get(folder, 0) + 1
        return breakdown

    def is_embedding_configured(self) -> bool:
        return self.embedding.is_configured()

    def has_index(self) -> bool:
        return self.store.is_complete()

    def is_ready(self) -> bool:
        return self.is_embedding_configured() and self.has_index()

    async def ensure_index(self, *, force: bool = False) -> IndexSnapshot:
        """Build or refresh the vector index when files or model change."""
        if not self.is_embedding_configured():
            raise RagNotReadyError("Embedding 配置不完整，无法构建知识库索引")

        async with _BUILD_LOCK:
            current_fingerprints = self._collect_fingerprints()
            snapshot = self._load_snapshot()
            if (
                not force
                and snapshot is not None
                and not snapshot.build_in_progress
                and snapshot.version == RAG_INDEX_VERSION
                and snapshot.embedding_model == self.settings.embedding_model
                and snapshot.embedding_dim == self.embedding.configured_dim()
                and snapshot.file_fingerprints == current_fingerprints
            ):
                return snapshot

            chunks = chunk_knowledge_base(self.kb_root)
            if not chunks:
                raise RagNotReadyError("知识库中没有可索引的 Markdown 文件")

            should_restart = force or not self._can_resume_build(current_fingerprints)
            embedded_ids: set[str] = set()
            if should_restart:
                self.store.clear_build()
            else:
                partial = self.store.load_partial()
                if partial is not None:
                    embedded_ids = {item.chunk.chunk_id for item in partial.chunks}

            pending = [chunk for chunk in chunks if chunk.chunk_id not in embedded_ids]
            if should_restart or not self.store.has_partial_build():
                self.store.start_build(
                    embedding_model=self.settings.embedding_model,
                    embedding_dim=self.embedding.configured_dim(),
                    file_fingerprints=current_fingerprints,
                    total_expected=len(chunks),
                )

            logger.info(
                "Building knowledge-base index",
                kb_root=str(self.kb_root),
                file_count=len(current_fingerprints),
                chunk_count=len(chunks),
                pending_count=len(pending),
                resumed_count=len(embedded_ids),
            )

            try:
                await self._embed_pending(pending)
            except EmbeddingClientError as exc:
                logger.error("Knowledge-base index build interrupted", detail=str(exc))
                raise RagNotReadyError("Embedding 请求失败，知识库索引构建中断") from exc
            except EmbeddingNotConfiguredError as exc:
                raise RagNotReadyError("Embedding 配置不完整，无法向量化知识库") from exc

            self.store.finalize_build(file_fingerprints=current_fingerprints)
            snapshot = self._load_snapshot(force_reload=True)
            if snapshot is None:
                raise RagNotReadyError("知识库索引写入失败")
            logger.info(
                "Knowledge-base index ready",
                chunk_count=len(snapshot.chunks),
                kb_root=str(self.kb_root),
            )
            return snapshot

    async def _search_with_filters(
        self,
        query: str,
        snapshot: IndexSnapshot,
        *,
        top_k: int,
        filters: dict[str, str],
        query_vector: list[float] | None,
    ) -> tuple[list[RagHit], bool, list, list, str]:
        """Run hybrid or BM25 retrieval against one filter set."""
        if query_vector is not None:
            hits, rerank_connected, rerank_before, rerank_after = await search_chunks(
                query,
                query_vector,
                snapshot.chunks,
                top_k=top_k,
                filters=filters,
                rerank_service=self.rerank,
            )
            return hits, rerank_connected, rerank_before, rerank_after, "hybrid"

        hits, rerank_connected, rerank_before, rerank_after = await search_chunks_bm25_only(
            query,
            snapshot.chunks,
            top_k=top_k,
            filters=filters,
            rerank_service=self.rerank,
        )
        return hits, rerank_connected, rerank_before, rerank_after, "bm25"

    async def _retrieve_from_snapshot(
        self,
        normalized: str,
        snapshot: IndexSnapshot,
        *,
        top_k: int,
        query_vector: list[float] | None,
        embedding_connected: bool,
        started: float,
    ) -> RagRetrievalResult:
        """Search snapshot with hybrid/BM25 and relaxed filter retries."""
        filters = resolve_query_filters(normalized, self._company_aliases)
        hits, rerank_connected, rerank_before, rerank_after, mode = await self._search_with_filters(
            normalized,
            snapshot,
            top_k=top_k,
            filters=filters,
            query_vector=query_vector,
        )

        if not hits and filters.get("doc_type"):
            relaxed = {key: value for key, value in filters.items() if key != "doc_type"}
            hits, rerank_connected, rerank_before, rerank_after, mode = await self._search_with_filters(
                normalized,
                snapshot,
                top_k=top_k,
                filters=relaxed,
                query_vector=query_vector,
            )

        if not hits and query_vector is not None:
            hits, rerank_connected, rerank_before, rerank_after, mode = await self._search_with_filters(
                normalized,
                snapshot,
                top_k=top_k,
                filters=filters,
                query_vector=None,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        return RagRetrievalResult(
            hits=hits,
            latency_ms=latency_ms,
            embedding_connected=embedding_connected,
            rerank_connected=rerank_connected,
            rerank_before=rerank_before,
            rerank_after=rerank_after,
            index_chunk_count=len(snapshot.chunks),
            query=normalized,
            model=self.settings.embedding_model if embedding_connected else "",
            mode=mode if hits else "mock",
        )

    async def retrieve(self, query: str, *, top_k: int = 6) -> RagRetrievalResult:
        """Embed the query and return hybrid hits from the local index."""
        started = time.perf_counter()
        normalized = query.strip()
        if not normalized:
            return RagRetrievalResult(query=query, mode="mock")

        snapshot = self._load_snapshot()
        embedding_configured = self.is_embedding_configured()

        if embedding_configured:
            try:
                snapshot = await self.ensure_index()
            except RagNotReadyError as exc:
                logger.warning("RAG index unavailable", detail=str(exc))
                if snapshot is None or not snapshot.chunks:
                    return RagRetrievalResult(
                        query=normalized,
                        mode="mock",
                        embedding_connected=False,
                    )
            else:
                try:
                    query_vector, _meta = await self.embedding.embed_text(normalized)
                except EmbeddingClientError as exc:
                    logger.warning("Query embedding failed, falling back to BM25", detail=str(exc))
                    return await self._retrieve_from_snapshot(
                        normalized,
                        snapshot,
                        top_k=top_k,
                        query_vector=None,
                        embedding_connected=False,
                        started=started,
                    )
                return await self._retrieve_from_snapshot(
                    normalized,
                    snapshot,
                    top_k=top_k,
                    query_vector=query_vector,
                    embedding_connected=True,
                    started=started,
                )

        if snapshot is None or not snapshot.chunks:
            logger.warning("RAG fallback unavailable: no local index")
            return RagRetrievalResult(
                query=normalized,
                mode="mock",
                embedding_connected=False,
            )

        logger.info("Embedding not configured; using BM25-only retrieval")
        return await self._retrieve_from_snapshot(
            normalized,
            snapshot,
            top_k=top_k,
            query_vector=None,
            embedding_connected=False,
            started=started,
        )

    async def retrieve_targeted(
        self,
        queries: list[str],
        *,
        top_k: int = 4,
        filters: dict[str, str] | None = None,
        entity_name: str = "",
        narrative_strict: bool = False,
        narrative_query: str = "",
    ) -> RagRetrievalResult:
        """Run one or more focused retrieval queries and merge unique hits."""
        started = time.perf_counter()
        normalized_queries = [query.strip() for query in queries if query.strip()]
        if not normalized_queries:
            return RagRetrievalResult(query="", mode="mock")

        snapshot = self._load_snapshot()
        if snapshot is None or not snapshot.chunks:
            return RagRetrievalResult(query=" | ".join(normalized_queries), mode="mock")

        merged: dict[str, RagHit] = {}
        rerank_connected = False
        rerank_before: list = []
        rerank_after: list = []
        mode = "bm25"
        embedding_connected = False
        query_vector: list[float] | None = None

        if self.is_embedding_configured():
            try:
                snapshot = await self.ensure_index()
                query_vector, _meta = await self.embedding.embed_text(normalized_queries[0])
                embedding_connected = True
            except (RagNotReadyError, EmbeddingClientError) as exc:
                logger.warning("Targeted retrieval embedding unavailable", detail=str(exc))

        active_filters = dict(filters or {})
        for query in normalized_queries:
            scoped_filters = dict(active_filters)
            if not scoped_filters:
                scoped_filters = resolve_query_filters(query, self._company_aliases)
            hits, scope_rerank, scope_before, scope_after, scope_mode = await self._search_with_filters(
                query,
                snapshot,
                top_k=top_k,
                filters=scoped_filters,
                query_vector=query_vector,
            )
            mode = scope_mode
            rerank_connected = rerank_connected or scope_rerank
            if not rerank_before:
                rerank_before = scope_before
            if scope_after:
                rerank_after = scope_after
            for hit in hits:
                existing = merged.get(hit.chunk_id)
                if existing is None or hit.score > existing.score:
                    merged[hit.chunk_id] = hit

        final_hits = sorted(merged.values(), key=lambda item: item.score, reverse=True)[: max(top_k, 4)]
        if entity_name.strip():
            if narrative_strict:
                final_hits = filter_stock_narrative_hits(
                    final_hits,
                    stock_name=entity_name.strip(),
                    query=narrative_query or " | ".join(normalized_queries),
                )
            else:
                final_hits = filter_hits_by_entity(final_hits, entity_name.strip())
        final_hits = diversify_hits_by_time_period(final_hits, top_k=max(top_k, 4))
        latency_ms = int((time.perf_counter() - started) * 1000)
        return RagRetrievalResult(
            hits=final_hits,
            latency_ms=latency_ms,
            embedding_connected=embedding_connected,
            rerank_connected=rerank_connected,
            rerank_before=rerank_before,
            rerank_after=rerank_after,
            index_chunk_count=len(snapshot.chunks),
            query=" | ".join(normalized_queries),
            model=self.settings.embedding_model if embedding_connected else "",
            mode=mode if final_hits else "mock",
        )

    async def retrieve_hotspot(self, query: str, *, top_k: int = 10) -> RagRetrievalResult:
        """Retrieve hotspot evidence from monthly hotspots + industry reports."""
        return await self._retrieve_path_scoped(
            query,
            top_k=top_k,
            scopes=[("hotspots/", 0.55), ("industry-reports/", 0.45)],
        )

    async def retrieve_hotspot_industry_only(self, query: str, *, top_k: int = 5) -> RagRetrievalResult:
        """Retrieve industry background only (skip stale monthly hotspot docs)."""
        return await self._retrieve_path_scoped(
            query,
            top_k=top_k,
            scopes=[("industry-reports/", 1.0)],
        )

    async def retrieve_stock_narrative(
        self,
        query: str,
        *,
        top_k: int = 10,
        stock_name: str = "",
    ) -> RagRetrievalResult:
        """Retrieve pipeline / business-narrative evidence: research reports first, then annual reports."""
        result = await self._retrieve_path_scoped(
            query,
            top_k=top_k,
            scopes=[
                ("company-reports/", 0.45),
                ("industry-reports/", 0.35),
                ("financials/", 0.20),
            ],
        )
        if stock_name.strip():
            result.hits = filter_stock_narrative_hits(
                result.hits,
                stock_name=stock_name.strip(),
                query=query,
            )
        return result

    async def _retrieve_path_scoped(
        self,
        query: str,
        *,
        top_k: int,
        scopes: list[tuple[str, float]],
    ) -> RagRetrievalResult:
        """Retrieve evidence from weighted path prefixes (hotspot, stock narrative, etc.)."""
        started = time.perf_counter()
        normalized = query.strip()
        if not normalized:
            return RagRetrievalResult(query=query, mode="mock")

        snapshot = self._load_snapshot()
        embedding_configured = self.is_embedding_configured()
        query_vector: list[float] | None = None
        embedding_connected = False

        if embedding_configured:
            try:
                snapshot = await self.ensure_index()
                query_vector, _meta = await self.embedding.embed_text(normalized)
                embedding_connected = True
            except (RagNotReadyError, EmbeddingClientError) as exc:
                logger.warning("Hotspot retrieval embedding unavailable", detail=str(exc))

        if snapshot is None or not snapshot.chunks:
            return RagRetrievalResult(
                query=normalized,
                mode="mock",
                embedding_connected=embedding_connected,
            )

        merged: dict[str, RagHit] = {}
        rerank_connected = False
        rerank_before: list = []
        rerank_after: list = []
        mode = "bm25"
        for path_prefix, weight in scopes:
            scope_k = max(int(top_k * weight), 2)
            hits, scope_rerank, scope_before, scope_after, scope_mode = await self._search_with_filters(
                normalized,
                snapshot,
                top_k=scope_k,
                filters={"path_prefix": path_prefix},
                query_vector=query_vector,
            )
            mode = scope_mode
            rerank_connected = rerank_connected or scope_rerank
            if not rerank_before:
                rerank_before = scope_before
            if scope_after:
                rerank_after = scope_after
            for hit in hits:
                existing = merged.get(hit.chunk_id)
                if existing is None or hit.score > existing.score:
                    merged[hit.chunk_id] = hit

        final_hits = sorted(merged.values(), key=lambda item: item.score, reverse=True)[:top_k]
        final_hits = filter_hits_by_min_score(final_hits, HOTSPOT_MIN_SCORE)

        latency_ms = int((time.perf_counter() - started) * 1000)
        return RagRetrievalResult(
            hits=final_hits,
            latency_ms=latency_ms,
            embedding_connected=embedding_connected,
            rerank_connected=rerank_connected,
            rerank_before=rerank_before,
            rerank_after=rerank_after,
            index_chunk_count=len(snapshot.chunks),
            query=normalized,
            model=self.settings.embedding_model if embedding_connected else "",
            mode=mode if final_hits else "mock",
        )

    def _can_resume_build(self, fingerprints: dict[str, str]) -> bool:
        if not self.store.has_partial_build():
            return False
        partial = self.store.load_partial()
        if partial is None:
            return False
        return (
            partial.embedding_model == self.settings.embedding_model
            and partial.embedding_dim == self.embedding.configured_dim()
            and partial.file_fingerprints == fingerprints
        )

    def _collect_fingerprints(self) -> dict[str, str]:
        return {
            path.relative_to(self.kb_root).as_posix(): file_fingerprint(path)
            for path in list_markdown_files(self.kb_root)
        }

    def _load_snapshot(self, *, force_reload: bool = False) -> IndexSnapshot | None:
        if force_reload:
            self._snapshot = None
        if self._snapshot is not None:
            return self._snapshot
        self._snapshot = self.store.load()
        return self._snapshot

    async def _embed_pending(self, pending: list[KnowledgeChunk]) -> None:
        for start in range(0, len(pending), _EMBED_BATCH_SIZE):
            batch_chunks = pending[start : start + _EMBED_BATCH_SIZE]
            batch_texts = [chunk.text_for_embedding() for chunk in batch_chunks]
            vectors, _meta = await self.embedding.embed_texts(batch_texts)
            batch_stored = [
                StoredChunk(chunk=chunk, vector=vector)
                for chunk, vector in zip(batch_chunks, vectors, strict=True)
            ]
            self.store.append_batch(batch_stored)
            if (start // _EMBED_BATCH_SIZE + 1) % 25 == 0:
                logger.info(
                    "Knowledge-base index progress",
                    embedded=min(start + len(batch_chunks), len(pending)),
                    pending_total=len(pending),
                )


def format_source_time(hit: RagHit, ctx: SystemTimeContext | None = None) -> str:
    """Build citation time label with document period when available."""
    if hit.time_period.strip():
        return f"{hit.time_period.strip()}，本地知识库"
    time_ctx = ctx or resolve_system_time()
    return f"截至 {time_ctx.current_date}，本地知识库"


def hits_to_source_refs(
    hits: list[RagHit],
    *,
    ctx: SystemTimeContext | None = None,
) -> list[dict[str, str]]:
    """Map retrieval hits to rich-block citation sources."""
    time_ctx = ctx or resolve_system_time()
    return [
        {
            "type": hit.source_type,
            "label": hit.title,
            "time": format_source_time(hit, time_ctx),
        }
        for hit in hits
    ]


def rag_citations_for_quality(hits: list[RagHit]) -> list[dict[str, str]]:
    """Compact citation list for quality-check payload."""
    return [
        {
            "title": hit.title,
            "source_type": hit.source_type,
            "time_period": hit.time_period,
            "path": hit.path,
            "doc_id": hit.doc_id,
        }
        for hit in hits
    ]


def format_rag_context(hits: list[RagHit], *, ctx: SystemTimeContext | None = None) -> str:
    """Format retrieved snippets for LLM answer prompts."""
    if not hits:
        return ""
    time_ctx = ctx or resolve_system_time()
    lines = [
        time_ctx.prompt_block(),
        "",
        "以下是从本地知识库检索到的参考片段，请优先基于这些内容回答；"
        "片段中的 time_period 表示已入库文档的数据口径，不代表未发布；"
        "若片段中包含营业收入、净利润、毛利率等数值，必须在回答中引用并说明 time_period 时间口径：",
    ]
    for index, hit in enumerate(hits, start=1):
        breadcrumb = f"，路径={hit.breadcrumb}" if hit.breadcrumb else ""
        period = f"，time_period={hit.time_period}" if hit.time_period.strip() else ""
        lines.append(
            f"【参考{index}】{hit.title}（来源类型：{hit.source_type}，doc_id={hit.doc_id}{period}{breadcrumb}）\n"
            f"文件：{hit.path}\n{hit.snippet}"
        )
    return "\n\n".join(lines)
