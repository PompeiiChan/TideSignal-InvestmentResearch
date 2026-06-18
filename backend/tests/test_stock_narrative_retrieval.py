"""Tests for stock narrative RAG filtering (pipeline / R&D questions)."""

from __future__ import annotations

from backend.src.services.rag.models import RagHit
from backend.src.services.rag.retriever import filter_stock_narrative_hits


def _hit(*, path: str, title: str, snippet: str = "", score: float = 0.9) -> RagHit:
    return RagHit(
        chunk_id=path,
        doc_id=path,
        title=title,
        source_type="report",
        path=path,
        score=score,
        snippet=snippet,
        relevance_reason="",
    )


def test_filter_stock_narrative_drops_other_company_financials() -> None:
    hits = [
        _hit(
            path="financials/688256-hanwuji-financial-2025A-2026Q1.md",
            title="寒武纪2025年年度报告",
            snippet="寒武纪营业收入",
        ),
        _hit(
            path="company-reports/000568-luzhoulaojiao-company-report-2026.md",
            title="泸州老窖公司研报",
            snippet="泸州老窖产品渠道",
        ),
    ]
    filtered = filter_stock_narrative_hits(
        hits,
        stock_name="恒瑞医药",
        query="恒瑞医药的创新药管线？",
    )
    assert filtered == []


def test_filter_stock_narrative_keeps_matching_company_report() -> None:
    hits = [
        _hit(
            path="company-reports/600276-hengrui-company-report-2026.md",
            title="恒瑞医药深度研究",
            snippet="恒瑞医药创新药研发管线",
        )
    ]
    filtered = filter_stock_narrative_hits(
        hits,
        stock_name="恒瑞医药",
        query="恒瑞医药的创新药管线？",
    )
    assert len(filtered) == 1
    assert "恒瑞" in filtered[0].snippet


def test_filter_stock_narrative_allows_industry_report_on_topic() -> None:
    hits = [
        _hit(
            path="industry-reports/yiyao-industry-report-2026.md",
            title="创新药行业深度",
            snippet="创新药研发管线与临床申报趋势",
        ),
        _hit(
            path="industry-reports/jixie-industry-report-20260509.md",
            title="机械行业",
            snippet="石油天然气管线阀门出口项目",
        ),
    ]
    filtered = filter_stock_narrative_hits(
        hits,
        stock_name="恒瑞医药",
        query="恒瑞医药的创新药管线？",
    )
    assert len(filtered) == 1
    assert "创新药" in filtered[0].snippet
