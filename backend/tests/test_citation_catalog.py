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
        source_type=source_type,
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


def test_build_citation_catalog_includes_stock_api_tool() -> None:
    tool_result = {
        "stock_evidence_api_lookup": {
            "found": True,
            "stock_name": "中际旭创",
            "stock_code": "300308",
            "facts": [
                {
                    "kind": "announcement",
                    "title": "中际旭创：2026年第一季度报告",
                    "time": "2026-04-25",
                    "source": "巨潮资讯",
                }
            ],
        }
    }
    catalog = build_citation_catalog([], tool_result)
    assert any("公告与资讯" in entry.title for entry in catalog.entries)
    assert any(entry.origin == "stock_evidence_api" for entry in catalog.entries)


def test_sanitize_reference_keeps_only_body_cited_sources() -> None:
    rag_hits = [
        _hit(
            doc_id="event_ashare_202606",
            title="2026 年 6 月 A股月度热点",
            source_type="market",
            path="hotspots/2026-06-market-hotspots.md",
        ),
        _hit(
            doc_id="industry_textile_sleep",
            title="纺织业研报：睡眠经济与家纺行业新机遇",
            source_type="report",
            path="industry-reports/fangzhiye-industry-report-2026.md",
        ),
    ]
    catalog = build_citation_catalog(rag_hits, {}, response_kind="hotspot")
    content = (
        "本地对宠物经济覆盖有限，仅能从消费轮动角度作背景参考[citation:1]。\n\n"
        "### 参考来源\n\n"
        "- [citation:1]2026 年 6 月 A股月度热点\n"
        "- [citation:2]纺织业研报：睡眠经济与家纺行业新机遇\n"
    )
    normalized = normalize_assembly_citations(content, catalog)
    assert "纺织业研报" not in normalized
    assert "2026 年 6 月" in normalized
    assert normalized.count("[citation:1]") >= 2


def test_build_citation_catalog_includes_hotspot_api_tools() -> None:
    tool_result = {
        "hotspot_fact_lookup": {
            "tool": "hotspot_fact_lookup",
            "topic": "宠物",
            "facts": [],
            "fact_count": 0,
        },
        "hotspot_signal_lookup": {
            "tool": "hotspot_signal_lookup",
            "signal_mode": "ths_live",
            "topic": "宠物行业",
            "topic_matched": False,
            "trade_date": "2026-06-13",
            "stock_count": 0,
            "stocks": [],
            "themes": [],
        },
        "market_ranking_lookup": {
            "tool": "market_ranking_lookup",
            "ranking_mode": "board_stocks",
            "industry": "宠物经济",
            "rows": [{"rank": 1, "stock_name": "中宠股份", "pct_change": 2.1}],
            "row_count": 1,
        },
    }
    catalog = build_citation_catalog([], tool_result, response_kind="hotspot")
    titles = [entry.title for entry in catalog.entries]
    assert any("快讯与公告" in title for title in titles)
    assert any("同花顺" in title for title in titles)
    assert any("成分股涨幅" in title for title in titles)
    assert len(catalog.entries) == 3


def test_rebuild_reference_section_when_sanitizer_strips_orphan_refs() -> None:
    tool_result = {
        "hotspot_signal_lookup": {
            "tool": "hotspot_signal_lookup",
            "signal_mode": "ths_live",
            "topic": "宠物行业",
            "topic_matched": False,
            "trade_date": "2026-06-13",
            "stock_count": 0,
        }
    }
    catalog = build_citation_catalog([], tool_result, response_kind="hotspot")
    content = (
        "同花顺当日强势股列表未命中宠物主题，不宜把无关标签当热度[citation:1]。\n\n"
        "### 参考来源\n\n"
        "- [citation:2]虚构来源\n"
    )
    normalized = normalize_assembly_citations(content, catalog)
    assert "### 参考来源" in normalized
    assert "同花顺" in normalized
    assert "虚构来源" not in normalized
    assert normalized.count("[citation:1]") >= 2


def test_filter_hits_by_min_score_drops_weak_matches() -> None:
    from backend.src.services.rag.retriever import filter_hits_by_min_score

    hits = [
        _hit(doc_id="a", title="强相关", source_type="market"),
        _hit(doc_id="b", title="弱相关", source_type="report"),
    ]
    hits[0] = hits[0].model_copy(update={"score": 0.62})
    hits[1] = hits[1].model_copy(update={"score": 0.22})
    filtered = filter_hits_by_min_score(hits, 0.40)
    assert len(filtered) == 1
    assert filtered[0].doc_id == "a"
