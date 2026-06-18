"""Tests for stock evidence API supplement tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.src.agents.tools.stock_evidence_api_lookup import lookup_stock_evidence_api


@patch("backend.src.agents.tools.stock_evidence_api_lookup.resolve_stock_code", return_value=("300308", "中际旭创"))
@patch("backend.src.agents.tools.stock_evidence_api_lookup.fetch_cninfo_announcements")
@patch("backend.src.agents.tools.stock_evidence_api_lookup.fetch_global_news")
def test_lookup_stock_evidence_api_merges_announcements_and_news(
    mock_news: MagicMock,
    mock_ann: MagicMock,
    _mock_resolve: MagicMock,
) -> None:
    mock_ann.return_value = [
        {
            "title": "中际旭创：2026年第一季度报告",
            "type": "季报",
            "date": "2026-04-25",
            "url": "https://example.com/ann",
        }
    ]
    mock_news.return_value = [
        {
            "title": "中际旭创获机构调研",
            "summary": "光模块需求旺盛",
            "time": "2026-06-01",
            "source": "东方财富全球资讯",
        },
        {"title": "无关快讯", "summary": "其他行业", "time": "2026-06-01", "source": "东方财富全球资讯"},
    ]

    result = lookup_stock_evidence_api(stock_name="中际旭创")

    assert result["found"] is True
    assert result["stock_code"] == "300308"
    assert result["fact_count"] >= 2
    kinds = {item["kind"] for item in result["facts"]}
    assert "announcement" in kinds
    assert "news" in kinds
    assert all("中际旭创" in item.get("title", "") for item in result["facts"] if item["kind"] == "news")


@patch("backend.src.agents.tools.stock_evidence_api_lookup.fetch_global_news")
def test_lookup_stock_evidence_api_empty_on_failure(mock_news: MagicMock) -> None:
    mock_news.side_effect = RuntimeError("network down")

    result = lookup_stock_evidence_api(stock_name="中际旭创", stock_code="300308.SZ")

    assert result["found"] is False
    assert result["facts"] == []
    assert result["fallback_used"] is True
