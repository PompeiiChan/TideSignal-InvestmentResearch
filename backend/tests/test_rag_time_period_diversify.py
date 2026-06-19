"""Tests for financial RAG hit diversification by time period."""

from __future__ import annotations

from backend.src.services.rag.models import RagHit
from backend.src.services.rag.service import diversify_hits_by_time_period


def _hit(
    *,
    chunk_id: str,
    doc_id: str,
    time_period: str,
    score: float,
    path: str = "financials/300296-liyade-financial.md",
) -> RagHit:
    return RagHit(
        chunk_id=chunk_id,
        doc_id=doc_id,
        title=f"{time_period} report",
        source_type="financial",
        path=path,
        score=score,
        snippet="snippet",
        relevance_reason="test",
        time_period=time_period,
    )


def test_diversify_hits_by_time_period_keeps_multiple_periods() -> None:
    hits = [
        _hit(chunk_id="c1", doc_id="q1_300296_2026", time_period="2026Q1", score=0.95),
        _hit(chunk_id="c2", doc_id="q1_300296_2026", time_period="2026Q1", score=0.90),
        _hit(chunk_id="c3", doc_id="ann_300296_2025", time_period="2025A", score=0.85),
        _hit(chunk_id="c4", doc_id="ann_300296_2024", time_period="2024A", score=0.80),
    ]
    diversified = diversify_hits_by_time_period(hits, top_k=4)
    periods = {hit.time_period for hit in diversified}
    assert periods == {"2026Q1", "2025A", "2024A"}
    assert diversified[0].time_period == "2026Q1"


def test_diversify_hits_by_time_period_noop_for_non_financial() -> None:
    hits = [
        RagHit(
            chunk_id="r1",
            doc_id="report_1",
            title="研报",
            source_type="report",
            path="company-reports/foo.md",
            score=0.9,
            snippet="x",
            relevance_reason="test",
        )
    ]
    assert diversify_hits_by_time_period(hits, top_k=3) == hits
