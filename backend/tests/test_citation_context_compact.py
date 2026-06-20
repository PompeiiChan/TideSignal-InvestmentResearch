"""Tests for compact citation context (T-027)."""

from __future__ import annotations

from backend.src.agents.assembly.profile import (
    AssemblyProfile,
    use_compact_citation_context,
)
from backend.src.agents.tools.mock_financial_profile_lookup import lookup_financial_profile
from backend.src.services.citation_catalog import build_citation_catalog, format_citation_context
from backend.src.services.citation_context_compact import (
    COMPACT_MAX_QUARTERLY_POINTS,
    COMPACT_SNIPPET_MAX_CHARS,
    slim_valuation_history,
    truncate_snippet,
)
from backend.src.services.rag.models import RagHit

_FINANCIAL_KEY = "mock_financial_profile_lookup"


def _hit(*, doc_id: str, title: str, snippet: str = "snippet") -> RagHit:
    return RagHit(
        doc_id=doc_id,
        title=title,
        source_type="report",
        path=f"data/{doc_id}.md",
        score=0.9,
        snippet=snippet,
        relevance_reason="test",
        chunk_id=doc_id,
    )


def test_use_compact_citation_context_for_stock_profiles() -> None:
    assert use_compact_citation_context(AssemblyProfile.STOCK_FULL) is True
    assert use_compact_citation_context(AssemblyProfile.STOCK_NARRATIVE) is True
    assert use_compact_citation_context(AssemblyProfile.COMPOUND) is True
    assert use_compact_citation_context(AssemblyProfile.DATA_DEFAULT) is False
    assert use_compact_citation_context(AssemblyProfile.HOTSPOT_DEFAULT) is False


def test_compact_omits_time_block() -> None:
    fin_payload = lookup_financial_profile(stock_name="罗莱生活")
    catalog = build_citation_catalog([], {_FINANCIAL_KEY: fin_payload})
    full = format_citation_context(catalog, [], {_FINANCIAL_KEY: fin_payload}, compact=False)
    compact = format_citation_context(catalog, [], {_FINANCIAL_KEY: fin_payload}, compact=True)
    assert "系统时间" in full or "当前日期" in full or "交易日" in full
    assert "系统时间" not in compact and "当前日期" not in compact


def test_compact_truncates_rag_snippets() -> None:
    long_snippet = "段" * (COMPACT_SNIPPET_MAX_CHARS + 50)
    rag_hits = [_hit(doc_id="report_a", title="行业文档 A", snippet=long_snippet)]
    catalog = build_citation_catalog(rag_hits, {})
    compact = format_citation_context(catalog, rag_hits, {}, compact=True)
    assert long_snippet not in compact
    assert "…" in compact
    assert len(truncate_snippet(long_snippet)) <= COMPACT_SNIPPET_MAX_CHARS


def test_compact_slims_valuation_history() -> None:
    history = {
        "found": True,
        "data_origin": "eastmoney_valuation_history",
        "as_of": "2026-06-13",
        "trading_day_count": 800,
        "notes": "x" * 200,
        "pe_ttm": {
            "current": 22.1,
            "percentile": 72.5,
            "median": 18.0,
            "min": 10.0,
            "max": 40.0,
            "sample_count": 800,
            "extra": "drop-me",
        },
        "quarterly_series": [
            {"trade_date": f"202{i}-03-31", "pe_ttm": 20 + i, "pb": 3 + i, "noise": i}
            for i in range(8)
        ],
    }
    slim = slim_valuation_history(history)
    assert slim.get("trading_day_count") is None
    assert "extra" not in slim["pe_ttm"]
    assert len(slim["quarterly_series"]) == COMPACT_MAX_QUARTERLY_POINTS
    assert "noise" not in slim["quarterly_series"][0]


def test_compact_reduces_char_count_for_stock_payload() -> None:
    fin_payload = lookup_financial_profile(stock_name="罗莱生活")
    tool_result = {
        _FINANCIAL_KEY: fin_payload,
        "valuation_profile_lookup": {
            "found": True,
            "valuation": {
                "price": 12.3,
                "pe_ttm": 15.2,
                "pb": 1.8,
                "market_cap": "100亿",
                "data_origin": "tencent_quote_api",
                "as_of": "2026-06-13",
            },
            "valuation_history": {
                "found": True,
                "data_origin": "eastmoney_valuation_history",
                "as_of": "2026-06-13",
                "trading_day_count": 600,
                "notes": "n" * 300,
                "pe_ttm": {"current": 15.2, "percentile": 55.0, "median": 14.0},
                "pb": {"current": 1.8, "percentile": 40.0, "median": 1.9},
                "quarterly_series": [
                    {"trade_date": f"202{i}-03-31", "pe_ttm": 15 + i, "pb": 1.5 + i * 0.1}
                    for i in range(12)
                ],
            },
        },
        "stock_evidence_api_lookup": {
            "found": True,
            "stock_name": "罗莱生活",
            "facts": [
                {
                    "kind": "announcement",
                    "title": f"公告 {idx}",
                    "time": "2026-04-25",
                    "source": "巨潮资讯",
                    "summary": "s" * 200,
                }
                for idx in range(10)
            ],
        },
    }
    rag_hits = [
        _hit(doc_id=f"report_{idx}", title=f"研报 {idx}", snippet="段" * 800)
        for idx in range(8)
    ]
    catalog = build_citation_catalog(rag_hits, tool_result)
    full = format_citation_context(catalog, rag_hits, tool_result, compact=False)
    compact = format_citation_context(catalog, rag_hits, tool_result, compact=True)
    assert len(compact) < len(full) * 0.7
    assert "多期结构化财务数据" in compact
    assert "估值历史分位" in compact
    assert "API 公告与资讯" in compact


def test_truncate_snippet_respects_limit() -> None:
    assert truncate_snippet("abc") == "abc"
    assert len(truncate_snippet("x" * 1000)) <= COMPACT_SNIPPET_MAX_CHARS
