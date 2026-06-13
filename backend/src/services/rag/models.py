"""RAG domain models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["announcement", "report", "financial", "market", "qa", "knowledge"]
ChunkRole = Literal["child", "parent", "summary"]


class KnowledgeChunk(BaseModel):
    """One indexed markdown chunk."""

    chunk_id: str
    doc_id: str
    title: str
    source_type: SourceType
    path: str
    chunk_text: str
    section_title: str = ""
    embed_text: str = ""
    parent_chunk_id: str = ""
    parent_text: str = ""
    chunk_role: ChunkRole = "child"
    company_id: str = ""
    industry_id: str = ""
    doc_type: str = ""
    time_period: str = ""
    breadcrumb: str = ""
    retrieval_weight: float = 1.0

    def text_for_embedding(self) -> str:
        return self.embed_text.strip() or self.chunk_text

    def is_indexable(self) -> bool:
        return self.chunk_role in {"child", "summary"}


class RagHit(BaseModel):
    """One retrieval hit exposed to chat, trace and citations."""

    doc_id: str
    title: str
    source_type: SourceType
    path: str
    score: float
    snippet: str
    relevance_reason: str
    chunk_id: str = ""
    breadcrumb: str = ""
    time_period: str = ""
    retrieval_mode: str = "hybrid"


class RerankCandidateSnapshot(BaseModel):
    """One rerank candidate for trace observability."""

    chunk_id: str
    title: str
    score: float


class RagRetrievalResult(BaseModel):
    """Retriever output with observability metadata."""

    hits: list[RagHit] = Field(default_factory=list)
    latency_ms: int = 0
    embedding_connected: bool = False
    index_chunk_count: int = 0
    query: str = ""
    model: str = ""
    mode: Literal["semantic", "hybrid", "bm25", "mock"] = "semantic"
    rerank_connected: bool = False
    rerank_before: list[RerankCandidateSnapshot] = Field(default_factory=list)
    rerank_after: list[RerankCandidateSnapshot] = Field(default_factory=list)

    def to_trace_payload(self) -> dict[str, Any]:
        return {
            "rag_hits": [hit.model_dump() for hit in self.hits],
            "embedding_connected": self.embedding_connected,
            "rerank_connected": self.rerank_connected,
            "rerank_before": [item.model_dump() for item in self.rerank_before],
            "rerank_after": [item.model_dump() for item in self.rerank_after],
            "mode": self.mode,
            "index_chunk_count": self.index_chunk_count,
            "latency_ms": self.latency_ms,
            "model": self.model,
        }
