"""Lightweight BM25 index for hybrid retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .index_store import StoredChunk

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|\d+\.?\d*%?|[A-Za-z]{2,}")


@dataclass
class Bm25Index:
    """In-memory BM25 corpus built from stored chunks."""

    chunk_ids: list[str]
    doc_freq: Counter[str]
    doc_terms: list[Counter[str]]
    avg_doc_len: float
    corpus_size: int

    @classmethod
    def from_chunks(cls, chunks: list[StoredChunk]) -> Bm25Index:
        doc_terms: list[Counter[str]] = []
        chunk_ids: list[str] = []
        doc_freq: Counter[str] = Counter()
        total_len = 0

        for item in chunks:
            tokens = tokenize(item.chunk.text_for_embedding())
            if not tokens:
                continue
            term_counts = Counter(tokens)
            doc_terms.append(term_counts)
            chunk_ids.append(item.chunk.chunk_id)
            total_len += sum(term_counts.values())
            for term in term_counts:
                doc_freq[term] += 1

        avg_doc_len = total_len / len(doc_terms) if doc_terms else 0.0
        return cls(
            chunk_ids=chunk_ids,
            doc_freq=doc_freq,
            doc_terms=doc_terms,
            avg_doc_len=avg_doc_len,
            corpus_size=len(doc_terms),
        )

    def score(self, query: str, *, k1: float = 1.5, b: float = 0.75) -> dict[str, float]:
        if not self.corpus_size:
            return {}

        query_terms = tokenize(query)
        if not query_terms:
            return {}

        scores: dict[str, float] = {}
        for chunk_id, term_counts in zip(self.chunk_ids, self.doc_terms, strict=True):
            doc_len = sum(term_counts.values())
            total = 0.0
            for term in query_terms:
                freq = term_counts.get(term, 0)
                if freq == 0:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(1 + (self.corpus_size - df + 0.5) / (df + 0.5))
                denom = freq + k1 * (1 - b + b * doc_len / (self.avg_doc_len or 1.0))
                total += idf * (freq * (k1 + 1)) / denom
            if total > 0:
                scores[chunk_id] = total
        return scores


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]
