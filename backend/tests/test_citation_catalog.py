"""Tests for deterministic citation catalog."""

from __future__ import annotations

from backend.src.agents.tools.mock_financial_profile_lookup import lookup_financial_profile
from backend.src.services.citation_catalog import (
    build_citation_catalog,
    compact_used_citations,
    financial_tool_is_usable,
    normalize_assembly_citations,
)
from backend.src.services.rag.models import RagHit

_FINANCIAL_KEY = "mock_financial_profile_lookup"


def _hit(
    *,
    doc_id: str,
    title: str,
    source_type: str,
    path: str = "",
    chunk_id: str = "",
) -> RagHit:
    return RagHit(
        doc_id=doc_id,
        title=title,
        source_type=source_type,  # type: ignore[arg-type]
        path=path or f"data/{doc_id}.md",
        score=0.9,
        snippet="snippet",
        relevance_reason="test",
        chunk_id=chunk_id or doc_id,
    )


def test_financial_tool_not_usable_when_not_found() -> None:
    payload = {
        "found": False,
        "profile": None,
    }
    assert financial_tool_is_usable({_FINANCIAL_KEY: payload}) is False


def test_financial_tool_usable_for_luolai() -> None:
    payload = lookup_financial_profile(stock_name="罗莱生活")
    assert payload["found"] is True
    assert financial_tool_is_usable({_FINANCIAL_KEY: payload}) is True


def test_catalog_puts_local_financial_first_then_kb_docs() -> None:
    fin_payload = lookup_financial_profile(stock_name="罗莱生活")
    tool_result = {_FINANCIAL_KEY: fin_payload}
    rag_hits = [
        _hit(
            doc_id="report_luolai",
            title="罗莱生活公司研报：产品渠道供应链营销齐发力",
            source_type="report",
            chunk_id="chunk_report_1",
        ),
        _hit(
            doc_id="fin_luolai",
            title="罗莱生活 2026Q1 财务摘要",
            source_type="financial",
            path="financials/002293-luolaishenghuo-financial-2025A-2026Q1.md",
            chunk_id="chunk_fin_1",
        ),
    ]
    catalog = build_citation_catalog(rag_hits, tool_result)
    assert catalog.entries[0].index == 1
    assert "罗莱生活" in catalog.entries[0].title
    assert catalog.entries[0].origin == "local_financial_db"
    assert any(entry.title.startswith("罗莱生活公司研报") for entry in catalog.entries)
    assert catalog.doc_index["fin_luolai"] == 1


def test_catalog_without_local_financial_starts_from_rag() -> None:
    tool_result = {
        _FINANCIAL_KEY: {
            "found": False,
            "profile": None,
        }
    }
    rag_hits = [
        _hit(doc_id="report_ccgx", title="长春高新深度研报", source_type="report"),
    ]
    catalog = build_citation_catalog(rag_hits, tool_result)
    assert catalog.entries[0].index == 1
    assert catalog.entries[0].title == "长春高新深度研报"
    assert "__local_financial_tool__" not in catalog.doc_index


def test_normalize_replaces_financial_marker_and_drops_bogus_reference() -> None:
    fin_payload = lookup_financial_profile(stock_name="罗莱生活")
    catalog = build_citation_catalog([], {_FINANCIAL_KEY: fin_payload})
    content = (
        "营收增长[citation:财务]\n\n"
        "### 参考来源\n\n"
        "- [citation:财务]罗莱生活 2026Q1 财务数据\n"
        "- [citation:财务]长春高新 2025 年年度报告（本地知识库未覆盖，工具返回 N/A）\n"
    )
    normalized = normalize_assembly_citations(content, catalog)
    assert "[citation:财务]" not in normalized
    assert "[citation:1]" in normalized
    assert "长春高新" not in normalized
    assert "未覆盖" not in normalized


def test_hotspot_catalog_prioritizes_market_docs_over_reports() -> None:
    rag_hits = [
        _hit(
            doc_id="building_materials_dgzq_20260330",
            title="建材行业研报：玻璃纤维周期复苏与结构增长",
            source_type="report",
        ),
        _hit(
            doc_id="event_ashare_202606",
            title="2026 年 6 月 A股月度热点文档（截至 2026-06-11）",
            source_type="market",
            path="hotspots/2026-06-market-hotspots.md",
        ),
        _hit(
            doc_id="event_ashare_202605",
            title="2026 年 5 月 A股月度热点文档",
            source_type="market",
            path="hotspots/2026-05-market-hotspots.md",
        ),
    ]
    catalog = build_citation_catalog(rag_hits, {}, response_kind="hotspot")
    assert catalog.entries[0].index == 1
    assert catalog.entries[0].source_type == "market"
    assert catalog.entries[0].origin == "local_kb"
    assert catalog.entries[1].source_type == "market"
    report_indices = [entry.index for entry in catalog.entries if entry.source_type == "report"]
    market_indices = [entry.index for entry in catalog.entries if entry.source_type == "market"]
    assert market_indices and report_indices
    assert min(market_indices) < min(report_indices)


def test_compact_used_citations_renumbers_gaps() -> None:
    content = (
        "AI 硬件分化[citation:4]，重组题材博弈[citation:5]。\n\n"
        "### 参考来源\n\n"
        "- [citation:4]《2026 年 6 月 A 股月度热点文档》\n"
        "- [citation:5]《2026 年 5 月 A 股月度热点文档》\n"
    )
    normalized = compact_used_citations(content)
    assert "[citation:4]" not in normalized
    assert "[citation:5]" not in normalized
    assert normalized.count("[citation:1]") == 2
    assert normalized.count("[citation:2]") == 2


def test_normalize_compacts_skipped_catalog_slots() -> None:
    rag_hits = [
        _hit(doc_id="report_a", title="行业研报 A", source_type="report"),
        _hit(doc_id="event_ashare_202606", title="2026 年 6 月热点", source_type="market"),
    ]
    catalog = build_citation_catalog(rag_hits, {}, response_kind="hotspot")
    content = (
        "热点回顾[citation:1]。\n\n"
        "### 参考来源\n\n"
        "- [citation:1]2026 年 6 月热点\n"
    )
    normalized = normalize_assembly_citations(content, catalog)
    assert "[citation:1]" in normalized
    assert "[citation:2]" not in normalized
