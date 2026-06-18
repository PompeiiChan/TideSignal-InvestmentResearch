"""Tests for citation marker helpers."""

from __future__ import annotations

from pathlib import Path

from backend.src.agents.nodes.citation_rules import (
    content_has_citation_markers,
    content_needs_citation_retry,
    count_citation_markers,
    evidence_requires_citations,
    paragraphs_missing_trailing_citations,
)
from backend.src.services.rag.chunker import resolve_kb_root
from backend.src.services.rag.company_index import enrich_stock_slots_from_kb
from backend.src.settings import BACKEND_ROOT, AppSettings


def test_content_has_citation_markers() -> None:
    assert content_has_citation_markers("营收增长 5%[citation:1]") is True
    assert content_has_citation_markers("利润改善[citation:财务]") is True
    assert content_has_citation_markers("没有引用标记") is False


def test_count_citation_markers() -> None:
    assert count_citation_markers("a[citation:1]b[citation:2][citation:财务]") == 3


def test_evidence_requires_citations() -> None:
    assert evidence_requires_citations(rag_hits=[{"title": "x"}], evidence_pack={}) is True
    assert evidence_requires_citations(rag_hits=[], evidence_pack={"tool_result": {"rows": []}}) is True
    assert evidence_requires_citations(rag_hits=[], evidence_pack={}) is False


def test_paragraphs_missing_trailing_citations() -> None:
    body = (
        "公司 2025A 营收 312 亿元，同比 +8%。\n\n"
        "盈利质量改善，毛利率回升[citation:财务]\n\n"
        "### 参考来源\n\n"
        "- [citation:财务]某公司年报"
    )
    missing = paragraphs_missing_trailing_citations(body)
    assert len(missing) == 1
    assert "312" in missing[0]


def test_content_needs_citation_retry_when_only_reference_section_has_citations() -> None:
    body = (
        "营收 100 亿元，利润 20 亿元。\n\n"
        "### 参考来源\n\n"
        "- [citation:1]测试年报"
    )
    assert content_needs_citation_retry(body) is True


def _kb_root() -> Path:
    settings = AppSettings()
    return resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)


def test_enrich_stock_slots_fills_haitian_code() -> None:
    kb_root = _kb_root()
    slots = enrich_stock_slots_from_kb(
        "海天味业基本面怎么样",
        {"stock_name": "海天味业", "analysis_dimension": "基本面"},
        kb_root,
    )
    assert slots["stock_name"] == "海天味业"
    assert slots["stock_code"] == "603288.SH"
