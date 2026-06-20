"""Tests for Eastmoney research-report metadata client and tool."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from backend.src.agents.tools.research_report_metadata_lookup import lookup_research_report_metadata
from backend.src.integrations.market_data.em_research_report_client import (
    fetch_em_research_reports,
)

_SAMPLE_ROWS = [
    {
        "title": "贵州茅台：业绩稳健增长",
        "orgSName": "中信证券",
        "publishDate": "2026-05-10",
        "emRatingName": "买入",
        "ratingChange": "维持",
        "predictThisYearEps": 68.5,
        "predictNextYearEps": 74.2,
        "infoCode": "AP123456",
    },
    {
        "title": "贵州茅台深度跟踪",
        "orgSName": "国泰君安",
        "publishDate": "2026-04-01",
        "emRatingName": "增持",
        "ratingChange": "上调",
        "predictThisYearEps": 67.0,
        "predictNextYearEps": 72.0,
        "infoCode": "AP654321",
    },
]


@patch("backend.src.integrations.market_data.em_research_report_client.em_get")
def test_fetch_em_research_reports_normalizes_rows(mock_em_get: object) -> None:
    mock_em_get.return_value.json.return_value = {
        "data": _SAMPLE_ROWS,
        "TotalPage": 1,
    }
    result = fetch_em_research_reports("600519")
    assert result["found"] is True
    assert result["report_count"] == 2
    assert result["data_origin"] == "eastmoney_reportapi"
    first = result["reports"][0]
    assert first["title"].startswith("贵州茅台")
    assert first["org_name"] == "中信证券"
    assert first["rating"] == "买入"
    assert first["predict_this_year_eps"] == 68.5
    assert "pdf_url" in first


@patch("backend.src.integrations.market_data.em_research_report_client.em_get")
def test_fetch_em_research_reports_empty(mock_em_get: object) -> None:
    mock_em_get.return_value.json.return_value = {"data": [], "TotalPage": 1}
    result = fetch_em_research_reports("600519")
    assert result["found"] is False
    assert result["reports"] == []


@patch("backend.src.agents.tools.research_report_metadata_lookup.fetch_em_research_reports")
@patch("backend.src.agents.tools.research_report_metadata_lookup.resolve_stock_code")
def test_lookup_research_report_metadata_success(
    mock_resolve: object,
    mock_fetch: object,
) -> None:
    mock_resolve.return_value = ("600519", "贵州茅台")
    mock_fetch.return_value = {
        "found": True,
        "reports": [
            {
                "title": "测试研报",
                "org_name": "测试券商",
                "publish_date": "2026-05-01",
                "rating": "买入",
                "rating_change": "维持",
                "predict_this_year_eps": 1.2,
                "predict_next_year_eps": 1.4,
                "pdf_url": "https://example.com/a.pdf",
            }
        ],
        "report_count": 1,
        "rating_summary": {"买入": 1},
        "source": "https://reportapi.eastmoney.com/report/list",
        "data_origin": "eastmoney_reportapi",
        "notes": "东财研报元数据 1 条",
    }
    result = lookup_research_report_metadata(stock_name="贵州茅台", stock_code="600519")
    assert result["found"] is True
    assert result["tool"] == "research_report_metadata_lookup"
    assert result["is_mock"] is False
    assert result["fallback_used"] is False
    assert result["attribution"] == "third_party/a-stock-data (Apache-2.0)"
    assert result["reports"][0]["rating"] == "买入"


@patch("backend.src.agents.tools.research_report_metadata_lookup.fetch_em_research_reports")
@patch("backend.src.agents.tools.research_report_metadata_lookup.resolve_stock_code")
def test_lookup_research_report_metadata_fallback_on_empty(
    mock_resolve: object,
    mock_fetch: object,
) -> None:
    mock_resolve.return_value = ("600519", "贵州茅台")
    mock_fetch.return_value = {
        "found": False,
        "notes": "东财研报列表无记录",
        "source": "https://reportapi.eastmoney.com/report/list",
        "data_origin": "eastmoney_reportapi",
    }
    result = lookup_research_report_metadata(stock_name="贵州茅台")
    assert result["found"] is False
    assert result["fallback_used"] is True
    assert result["data_origin"] == "eastmoney_reportapi"


@pytest.mark.skipif(not os.getenv("REAL_API_TEST"), reason="REAL_API_TEST not set")
def test_real_em_research_reports_600519() -> None:
    result = fetch_em_research_reports("600519", page_size=10, max_pages=1)
    assert result["found"] is True
    assert result["report_count"] >= 3
    sample = result["reports"][0]
    assert sample.get("title")
    assert sample.get("rating")


@pytest.mark.skipif(not os.getenv("REAL_API_TEST"), reason="REAL_API_TEST not set")
def test_real_lookup_research_report_metadata() -> None:
    result = lookup_research_report_metadata(stock_name="贵州茅台", stock_code="600519")
    assert result["found"] is True
    assert len(result["reports"]) >= 3
