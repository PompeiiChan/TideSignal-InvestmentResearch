"""Tests for financial profile lookup fallbacks."""

from __future__ import annotations

from unittest.mock import patch

from backend.src.agents.tools.mock_financial_profile_lookup import lookup_financial_profile
from backend.src.integrations.market_data.sina_finance_client import (
    PeriodSnapshot,
    build_profile_from_snapshot,
    paper_code_for,
)
from backend.src.integrations.market_data.stock_code_resolver import (
    format_ticker,
    normalize_stock_code,
    resolve_stock_code,
)
from backend.src.services.rag.chunker import resolve_kb_root
from backend.src.services.rag.kb_financial_loader import (
    find_financial_kb_file,
    load_profile_from_kb_file,
)
from backend.src.settings import BACKEND_ROOT, AppSettings


def test_normalize_stock_code() -> None:
    assert normalize_stock_code("603027.SH") == "603027"
    assert normalize_stock_code("sz300750") == "300750"


def test_paper_code_for_shanghai() -> None:
    assert paper_code_for("603027") == "sh603027"
    assert paper_code_for("300750") == "sz300750"


def test_build_profile_from_snapshot() -> None:
    snapshot = PeriodSnapshot(
        period_key="20260331",
        lrb={
            "营业收入": "817563396.16",
            "营业成本": "483456789.12",
            "归属于母公司所有者的净利润": "148143506.60",
        },
        fzb={"归属于母公司所有者权益合计": "3500000000.00"},
    )
    profile = build_profile_from_snapshot(snapshot, stock_name="千禾味业", stock_code="603027")
    assert profile is not None
    assert profile["time_period"] == "2026Q1"
    assert profile["revenue"].endswith("亿元")
    assert profile["ticker"] == format_ticker("603027")


def test_kb_loader_reads_chinext_financial_file() -> None:
    settings = AppSettings()
    kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)
    path = find_financial_kb_file(kb_root, "300033")
    assert path is not None
    profile = load_profile_from_kb_file(path, stock_name="同花顺", stock_code="300033")
    assert profile is not None
    assert "亿元" in profile["revenue"]


@patch("backend.src.agents.tools.mock_financial_profile_lookup.fetch_multi_period_profiles")
@patch("backend.src.integrations.market_data.stock_code_resolver._resolve_from_eastmoney_suggest")
def test_lookup_falls_back_to_sina_when_local_missing(
    mock_suggest: object,
    mock_sina: object,
) -> None:
    mock_suggest.return_value = "603027"
    mock_sina.return_value = [
        {
            "company_id": "company_603027",
            "ticker": "603027.SH",
            "stock_name": "千禾味业",
            "industry": "未知",
            "time_period": "2026Q1",
            "revenue": "8.18亿元",
            "net_profit": "1.48亿元",
            "gross_margin": "40.82%",
            "roe": "4.22%",
            "pe_ttm": "N/A",
            "highlights": ["2026Q1 营收 8.18亿元"],
        },
        {
            "company_id": "company_603027",
            "ticker": "603027.SH",
            "stock_name": "千禾味业",
            "time_period": "2025A",
            "revenue": "30.00亿元",
            "net_profit": "5.00亿元",
            "gross_margin": "41.00%",
            "roe": "15.00%",
            "pe_ttm": "N/A",
            "highlights": ["2025A 营收 30.00亿元"],
        },
    ]
    result = lookup_financial_profile(stock_name="千禾味业")
    assert result["found"] is True
    assert result["data_origin"] == "sina_api"
    assert result["profile"]["stock_name"] == "千禾味业"
    assert len(result["periods"]) == 2


@patch("backend.src.agents.tools.mock_financial_profile_lookup.fetch_multi_period_profiles")
@patch("backend.src.integrations.market_data.stock_code_resolver._resolve_from_eastmoney_suggest")
def test_lookup_not_found_when_all_sources_empty(
    mock_suggest: object,
    mock_sina: object,
) -> None:
    mock_suggest.return_value = "000661"
    mock_sina.return_value = []
    result = lookup_financial_profile(stock_name="长春高新", stock_code="000661.SZ")
    assert result["found"] is False
    assert result["profile"] is None


def test_resolve_stock_code_from_kb_haitian() -> None:
    settings = AppSettings()
    code, name = resolve_stock_code("海天味业", "", settings=settings)
    assert code == "603288"
    assert name == "海天味业"
