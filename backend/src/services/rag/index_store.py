"""Persist vector index metadata under knowledge-base/.index/."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .chunker import RAG_INDEX_VERSION
from .models import KnowledgeChunk


@dataclass
class StoredChunk:
    """One indexed chunk with its embedding vector."""

    chunk: KnowledgeChunk
    vector: list[float]


@dataclass
class IndexSnapshot:
    """Full on-disk index payload."""

    version: int
    embedding_model: str
    embedding_dim: int
    built_at: str
    file_fingerprints: dict[str, str]
    chunks: list[StoredChunk]
    build_in_progress: bool = False


class IndexStore:
    """Read and write the local JSON / JSONL index cache with checkpoint support."""

    INDEX_DIR_NAME = ".index"
    META_FILE = "index_meta.json"
    CHUNKS_FILE = "chunks.jsonl"
    VECTORS_FILE = "vectors.jsonl"
    LEGACY_CHUNKS_FILE = "chunks.json"
    LEGACY_VECTORS_FILE = "vectors.json"

    def __init__(self, kb_root: Path) -> None:
        self.kb_root = kb_root
        self.index_dir = kb_root / self.INDEX_DIR_NAME

    def exists(self) -> bool:
        """Return True when a complete index is available."""
        return self.is_complete()

    def is_complete(self) -> bool:
        meta = self._read_meta()
        if meta is None:
            return self._legacy_exists()
        return not bool(meta.get("build_in_progress", True)) and int(meta.get("chunk_count", 0)) > 0

    def has_partial_build(self) -> bool:
        meta = self._read_meta()
        return bool(meta and meta.get("build_in_progress"))

    def load(self) -> IndexSnapshot | None:
        """Load a complete index snapshot."""
        if self.is_complete():
            return self._load_snapshot(include_partial=False)
        legacy = self._load_legacy()
        if legacy is not None and not legacy.build_in_progress:
            return legacy
        return None

    def load_partial(self) -> IndexSnapshot | None:
        """Load an in-progress or complete snapshot for resume."""
        if self._meta_path().exists() or self._chunks_path().exists():
            return self._load_snapshot(include_partial=True)
        return self._load_legacy()

    def start_build(
        self,
        *,
        embedding_model: str,
        embedding_dim: int,
        file_fingerprints: dict[str, str],
        total_expected: int,
    ) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._chunks_path().write_text("", encoding="utf-8")
        self._vectors_path().write_text("", encoding="utf-8")
        self._write_meta(
            {
                "version": RAG_INDEX_VERSION,
                "embedding_model": embedding_model,
                "embedding_dim": embedding_dim,
                "built_at": "",
                "file_fingerprints": file_fingerprints,
                "chunk_count": 0,
                "total_expected": total_expected,
                "build_in_progress": True,
            }
        )

    def append_batch(self, batch: list[StoredChunk]) -> None:
        if not batch:
            return
        self.index_dir.mkdir(parents=True, exist_ok=True)
        with self._chunks_path().open("a", encoding="utf-8") as chunk_file:
            for item in batch:
                chunk_file.write(json.dumps(item.chunk.model_dump(), ensure_ascii=False))
                chunk_file.write("\n")
        with self._vectors_path().open("a", encoding="utf-8") as vector_file:
            for item in batch:
                vector_file.write(
                    json.dumps(
                        {"chunk_id": item.chunk.chunk_id, "vector": item.vector},
                        ensure_ascii=False,
                    )
                )
                vector_file.write("\n")
        meta = self._read_meta() or {}
        meta["chunk_count"] = int(meta.get("chunk_count", 0)) + len(batch)
        self._write_meta(meta)

    def finalize_build(self, *, file_fingerprints: dict[str, str]) -> None:
        meta = self._read_meta()
        if meta is None:
            return
        meta["build_in_progress"] = False
        meta["built_at"] = datetime.now(UTC).isoformat()
        meta["file_fingerprints"] = file_fingerprints
        self._write_meta(meta)

    def clear_build(self) -> None:
        if not self.index_dir.exists():
            return
        for path in (
            self._meta_path(),
            self._chunks_path(),
            self._vectors_path(),
            self.index_dir / self.LEGACY_CHUNKS_FILE,
            self.index_dir / self.LEGACY_VECTORS_FILE,
        ):
            if path.exists():
                path.unlink()

    def save(
        self,
        *,
        embedding_model: str,
        embedding_dim: int,
        file_fingerprints: dict[str, str],
        chunks: list[StoredChunk],
    ) -> None:
        """Atomically write a complete index (used by tests and small builds)."""
        self.clear_build()
        self.start_build(
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            file_fingerprints=file_fingerprints,
            total_expected=len(chunks),
        )
        self.append_batch(chunks)
        self.finalize_build(file_fingerprints=file_fingerprints)

    def _meta_path(self) -> Path:
        return self.index_dir / self.META_FILE

    def _chunks_path(self) -> Path:
        return self.index_dir / self.CHUNKS_FILE

    def _vectors_path(self) -> Path:
        return self.index_dir / self.VECTORS_FILE

    def _legacy_exists(self) -> bool:
        return (
            self._meta_path().exists()
            and (self.index_dir / self.LEGACY_CHUNKS_FILE).exists()
            and (self.index_dir / self.LEGACY_VECTORS_FILE).exists()
        )

    def _read_meta(self) -> dict[str, Any] | None:
        if not self._meta_path().exists():
            return None
        payload = self._read_json(self._meta_path())
        return payload if isinstance(payload, dict) else None

    def _write_meta(self, payload: dict[str, Any]) -> None:
        self._write_json(self._meta_path(), payload)

    def _load_snapshot(self, *, include_partial: bool) -> IndexSnapshot | None:
        meta = self._read_meta()
        if meta is None:
            return None
        if not include_partial and bool(meta.get("build_in_progress", True)):
            return None
        stored = self._read_jsonl_chunks()
        if not stored and not include_partial:
            return None
        return IndexSnapshot(
            version=int(meta.get("version", 2)),
            embedding_model=str(meta.get("embedding_model", "")),
            embedding_dim=int(meta.get("embedding_dim", 0)),
            built_at=str(meta.get("built_at", "")),
            file_fingerprints={
                str(key): str(value) for key, value in dict(meta.get("file_fingerprints", {})).items()
            },
            chunks=stored,
            build_in_progress=bool(meta.get("build_in_progress", False)),
        )

    def _read_jsonl_chunks(self) -> list[StoredChunk]:
        if not self._chunks_path().exists() or not self._vectors_path().exists():
            return []
        vectors_by_id: dict[str, list[float]] = {}
        for line in self._vectors_path().read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            chunk_id = str(row.get("chunk_id", ""))
            vector = row.get("vector")
            if chunk_id and isinstance(vector, list):
                vectors_by_id[chunk_id] = [float(value) for value in vector]

        stored: list[StoredChunk] = []
        for line in self._chunks_path().read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            chunk = KnowledgeChunk.model_validate(row)
            vector = vectors_by_id.get(chunk.chunk_id)
            if vector is None:
                continue
            stored.append(StoredChunk(chunk=chunk, vector=vector))
        return stored

    def _load_legacy(self) -> IndexSnapshot | None:
        if not self._legacy_exists():
            return None
        meta = self._read_meta()
        chunk_rows = self._read_json(self.index_dir / self.LEGACY_CHUNKS_FILE)
        vector_rows = self._read_json(self.index_dir / self.LEGACY_VECTORS_FILE)
        if not isinstance(meta, dict) or not isinstance(chunk_rows, list) or not isinstance(vector_rows, dict):
            return None
        stored: list[StoredChunk] = []
        for row in chunk_rows:
            if not isinstance(row, dict):
                continue
            chunk_id = str(row.get("chunk_id", ""))
            vector = vector_rows.get(chunk_id)
            if not isinstance(vector, list):
                continue
            stored.append(
                StoredChunk(
                    chunk=KnowledgeChunk.model_validate(row),
                    vector=[float(value) for value in vector],
                )
            )
        return IndexSnapshot(
            version=int(meta.get("version", 1)),
            embedding_model=str(meta.get("embedding_model", "")),
            embedding_dim=int(meta.get("embedding_dim", 0)),
            built_at=str(meta.get("built_at", "")),
            file_fingerprints={
                str(key): str(value) for key, value in dict(meta.get("file_fingerprints", {})).items()
            },
            chunks=stored,
            build_in_progress=bool(meta.get("build_in_progress", False)),
        )

    @staticmethod
    def _read_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
