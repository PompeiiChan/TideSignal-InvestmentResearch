"""Tests for stock evidence gap detection and enrichment planning."""

from __future__ import annotations

from backend.src.services.evidence_gaps import (
    build_gap_enrichment_plan,
    detect_stock_evidence_gaps,
    merge_rag_hits,
)


def test_detect_gaps_when_company_rag_missing() -> None:
    gaps = detect_stock_evidence_gaps(
        tool_result={"mock_financial_profile_lookup": {"found": True, "profile": {"stock_name": "寒武纪"}, "periods": [{"time_period": "2025A"}]}},
        rag_hits=[{"title": "白酒行业研报", "path": "industry-reports/a.md", "chunk_id": "a"}],
        analysis_dimensions=["基本面", "盈利能力"],
        stock_name="寒武纪",
    )
    gap_ids = {gap["gap_id"] for gap in gaps}
    assert "company_rag_missing" in gap_ids
    assert "multi_period_thin" in gap_ids


def test_detect_gaps_skips_when_company_rag_present() -> None:
    gaps = detect_stock_evidence_gaps(
        tool_result={"mock_financial_profile_lookup": {"found": True, "profile": {"stock_name": "泸州老窖"}, "periods": [{"time_period": "2025A"}, {"time_period": "2024A"}]}},
        rag_hits=[
            {
                "title": "泸州老窖 2025 年年度报告",
                "path": "financials/000568.md",
                "chunk_id": "fin_1",
            }
        ],
        analysis_dimensions=["基本面"],
        stock_name="泸州老窖",
    )
    assert "company_rag_missing" not in {gap["gap_id"] for gap in gaps}


def test_build_gap_plan_includes_targeted_queries() -> None:
    gaps = [
        {
            "gap_id": "company_rag_missing",
            "topic": "寒武纪 公告与研报",
            "reason": "缺少公司文档",
        }
    ]
    plan = build_gap_enrichment_plan(
        gaps,
        stock_name="寒武纪",
        stock_code="688256.SH",
        analysis_dimensions=["基本面"],
        existing_tool_result={
            "mock_financial_profile_lookup": {
                "profile": {"industry": "AI芯片"},
            }
        },
        existing_rag_hits=[],
    )
    assert plan["rag_queries"]
    assert all("寒武纪" in query for query in plan["rag_queries"])
    assert not any("年报" in query for query in plan["rag_queries"])
    assert "stock_evidence_api_lookup" in plan["tool_names"]


def test_build_gap_plan_includes_api_for_risk_gap() -> None:
    gaps = [
        {
            "gap_id": "risk_signal_unexplained",
            "topic": "寒武纪 经营现金流 应收 负债",
            "reason": "风险未解释",
        }
    ]
    plan = build_gap_enrichment_plan(
        gaps,
        stock_name="寒武纪",
        stock_code="688256.SH",
        analysis_dimensions=["基本面"],
        existing_tool_result={},
        existing_rag_hits=[],
    )
    assert "stock_evidence_api_lookup" in plan["tool_names"]


def test_detect_gaps_for_pipeline_query_only_checks_rag() -> None:
    gaps = detect_stock_evidence_gaps(
        tool_result={},
        rag_hits=[{"title": "医药行业研报", "path": "industry-reports/a.md", "chunk_id": "a"}],
        analysis_dimensions=["研发管线布局"],
        stock_name="恒瑞医药",
        query="恒瑞医药的创新药管线？",
    )
    gap_ids = {gap["gap_id"] for gap in gaps}
    assert gap_ids == {"company_rag_missing"}
    assert "multi_period_thin" not in gap_ids
    assert "valuation_missing" not in gap_ids


def test_build_gap_plan_uses_pipeline_queries_for_narrative_gap() -> None:
    gaps = [
        {
            "gap_id": "company_rag_missing",
            "topic": "恒瑞医药 年报与公告",
            "reason": "缺少公司文档",
        }
    ]
    plan = build_gap_enrichment_plan(
        gaps,
        stock_name="恒瑞医药",
        stock_code="600276.SH",
        analysis_dimensions=["研发管线布局"],
        existing_tool_result={},
        existing_rag_hits=[],
        query="恒瑞医药的创新药管线？",
    )
    assert plan["rag_queries"]
    assert any("管线" in query or "研发" in query or "研报" in query for query in plan["rag_queries"])
    assert "mock_financial_profile_lookup" not in plan["tool_names"]
    assert "stock_evidence_api_lookup" not in plan["tool_names"]


def test_merge_rag_hits_keeps_best_score() -> None:
    merged = merge_rag_hits(
        [{"chunk_id": "a", "score": 0.4, "title": "old"}],
        [{"chunk_id": "a", "score": 0.9, "title": "new"}, {"chunk_id": "b", "score": 0.7, "title": "b"}],
    )
    assert len(merged) == 2
    assert merged[0]["title"] == "new"
