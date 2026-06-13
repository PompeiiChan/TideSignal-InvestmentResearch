"""Markdown scanning and type-routed chunking for the local knowledge base."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .chunk_strategies import (
    chunk_financial_file,
    chunk_hotspot_file,
    chunk_report_file,
    chunk_structured_file,
)
from .company_index import load_company_aliases
from .metadata import parse_metadata_table
from .models import KnowledgeChunk, SourceType

KB_SUBDIRS = ("hotspots", "financials", "industry-reports", "company-reports", "structured-data")

FOLDER_SOURCE_TYPE: dict[str, SourceType] = {
    "hotspots": "market",
    "financials": "financial",
    "industry-reports": "report",
    "company-reports": "report",
    "structured-data": "knowledge",
}

RAG_INDEX_VERSION = 8


def resolve_kb_root(configured_path: str, backend_root: Path) -> Path:
    """Resolve LOCAL_KB_PATH relative to backend root."""
    path = Path(configured_path.strip() or "data/knowledge-base")
    return path if path.is_absolute() else (backend_root / path).resolve()


def list_markdown_files(kb_root: Path) -> list[Path]:
    """List indexable markdown files under the knowledge base."""
    if not kb_root.exists():
        return []
    files: list[Path] = []
    for subdir in KB_SUBDIRS:
        folder = kb_root / subdir
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*.md")):
            if path.is_file() and path.name.lower() != "readme.md":
                files.append(path)
    return files


def count_markdown_files(kb_root: Path) -> int:
    """Count markdown files eligible for indexing."""
    return len(list_markdown_files(kb_root))


def file_fingerprint(path: Path) -> str:
    """Build a stable fingerprint from file metadata and content hash prefix."""
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return f"{stat.st_mtime_ns}:{stat.st_size}:{digest}"


def chunk_markdown_file(path: Path, kb_root: Path) -> list[KnowledgeChunk]:
    """Split one markdown file using the strategy for its knowledge-base folder."""
    relative = path.relative_to(kb_root).as_posix()
    folder = path.relative_to(kb_root).parts[0] if path.relative_to(kb_root).parts else ""
    source_type = FOLDER_SOURCE_TYPE.get(folder, "knowledge")
    text = path.read_text(encoding="utf-8")
    file_meta = parse_metadata_table(text)

    if folder == "hotspots":
        return chunk_hotspot_file(path, text, relative=relative, file_meta=file_meta)
    if folder == "financials":
        return chunk_financial_file(path, text, relative=relative)
    if folder in {"company-reports", "industry-reports"}:
        return chunk_report_file(
            path,
            text,
            relative=relative,
            file_meta=file_meta,
            source_type=source_type,
        )
    if folder == "structured-data":
        return chunk_structured_file(path, text, relative=relative, file_meta=file_meta)
    return chunk_structured_file(path, text, relative=relative, file_meta=file_meta)


def _enrich_company_names(kb_root: Path, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
    aliases = load_company_aliases(kb_root)
    if not aliases:
        return chunks
    id_to_name = {
        company_id: name for name, company_id in aliases.items() if company_id.startswith("company_")
    }
    enriched: list[KnowledgeChunk] = []
    for chunk in chunks:
        company_name = id_to_name.get(chunk.company_id, "")
        if company_name and company_name not in chunk.chunk_text[:120]:
            prefix = f"{company_name}({chunk.company_id.replace('company_', '')})"
            enriched.append(
                chunk.model_copy(
                    update={
                        "chunk_text": f"{prefix} {chunk.chunk_text}",
                        "embed_text": f"{prefix} {chunk.text_for_embedding()}",
                    }
                )
            )
            continue
        enriched.append(chunk)
    return enriched


def chunk_knowledge_base(kb_root: Path) -> list[KnowledgeChunk]:
    """Chunk all markdown files under the configured knowledge base."""
    all_chunks: list[KnowledgeChunk] = []
    for path in list_markdown_files(kb_root):
        all_chunks.extend(chunk_markdown_file(path, kb_root))
    indexable = [chunk for chunk in all_chunks if chunk.is_indexable()]
    return _enrich_company_names(kb_root, indexable)
