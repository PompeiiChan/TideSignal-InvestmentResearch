"""Tests for hotspot multi-month RAG diversification."""

from __future__ import annotations

from backend.src.services.rag.models import RagHit
from backend.src.services.rag.service import diversify_hotspot_hits_by_month


def _hit(*, chunk_id: str, period: str, score: float, path: str) -> RagHit:
    return RagHit(
        chunk_id=chunk_id,
        doc_id=chunk_id,
        title=f"热点 {period}",
        snippet="snippet",
        source_type="market",
        path=path,
        score=score,
        time_period=period,
        relevance_reason="test",
    )


def test_diversify_hotspot_hits_keeps_multiple_months() -> None:
    hits = [
        _hit(chunk_id="a1", period="2026-04", score=0.9, path="hotspots/2026-04-market-hotspots.md"),
        _hit(chunk_id="a2", period="2026-04", score=0.85, path="hotspots/2026-04-market-hotspots.md"),
        _hit(chunk_id="b1", period="2026-05", score=0.88, path="hotspots/2026-05-market-hotspots.md"),
        _hit(chunk_id="c1", period="2026-06", score=0.7, path="hotspots/2026-06-market-hotspots.md"),
    ]
    diversified = diversify_hotspot_hits_by_month(hits, top_k=4)
    periods = {hit.time_period for hit in diversified}
    assert periods == {"2026-04", "2026-05", "2026-06"}
    assert diversified[0].chunk_id == "a1"
