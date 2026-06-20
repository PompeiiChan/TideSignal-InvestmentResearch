"""Tests for programmatic citation patching."""

from __future__ import annotations

from backend.src.agents.assembly.citation_fix import (
    CITATION_PATCH_PROMPT_MAX_CHARS,
    apply_citation_fix,
    build_citation_patch_prompt,
    patch_missing_citations,
    pick_best_citation_content,
    relocate_citations_from_headings,
)
from backend.src.agents.nodes.citation_rules import (
    content_needs_citation_retry,
    count_misplaced_heading_citations,
    count_paragraphs_missing_citations,
    paragraphs_missing_trailing_citations,
)
from backend.src.services.citation_catalog import CitationCatalog, CitationEntry


def _catalog_with_financial() -> CitationCatalog:
    catalog = CitationCatalog()
    catalog.entries.append(
        CitationEntry(index=1, title="测试公司 2025A 财务", source_type="financial", origin="local")
    )
    catalog.doc_index["__local_financial_tool__"] = 1
    return catalog


def _catalog_with_report() -> CitationCatalog:
    catalog = CitationCatalog()
    catalog.entries.append(
        CitationEntry(
            index=2,
            title="宁德时代公司研报：全球动力电池龙头",
            source_type="report",
            origin="local_kb",
            doc_id="report_catl",
        )
    )
    catalog.doc_index["report_catl"] = 2
    return catalog


def test_patch_missing_citations_adds_trailing_marker() -> None:
    catalog = _catalog_with_financial()
    content = "公司营收 100 亿元，净利润 20 亿元。\n\n### 参考来源\n\n- 测试"
    patched, count = patch_missing_citations(content, catalog)
    assert count >= 1
    assert "[citation:1]" in patched
    assert not content_needs_citation_retry(patched) or "[citation:1]" in patched


def test_apply_citation_fix_resolves_retry() -> None:
    catalog = _catalog_with_financial()
    content = "公司营收 100 亿元，净利润 20 亿元。"
    fixed, applied, count = apply_citation_fix(content, catalog)
    assert count >= 1
    assert "[citation:1]" in fixed
    if applied:
        assert not content_needs_citation_retry(fixed)


def test_build_citation_patch_prompt_allows_more_context() -> None:
    catalog = _catalog_with_financial()
    prompt = build_citation_patch_prompt(
        missing_paragraphs=["公司营收 100 亿元", "行业竞争格局持续变化，龙头份额提升"],
        catalog=catalog,
        needs_reference_section=True,
    )
    assert len(prompt) <= CITATION_PATCH_PROMPT_MAX_CHARS
    assert "引用修订" in prompt
    assert "行业竞争" in prompt
    assert "禁止在 `###`" in prompt


def test_relocate_citations_from_narrative_heading() -> None:
    content = (
        "### 一、行业竞争格局 [citation:2]\n\n"
        "从行业竞争格局看，宁德时代全球动力电池龙头地位仍较稳固，渠道与产能扩张持续推进。\n\n"
        "### 参考来源\n\n"
        "- [citation:2]测试"
    )
    relocated, count = relocate_citations_from_headings(content)
    assert count >= 1
    assert "### 一、行业竞争格局 [citation:2]" not in relocated
    assert count_misplaced_heading_citations(relocated) == 0
    assert "[citation:2]" in relocated


def test_relocate_does_not_duplicate_existing_paragraph_citation() -> None:
    content = (
        "### 一、当前估值水平 [citation:2]\n\n"
        "宁德时代当前 PE TTM 约 22.3 倍，处于近 3 年估值区间的中高位[citation:2]。\n\n"
        "### 参考来源\n\n"
        "- [citation:2]估值"
    )
    relocated, count = relocate_citations_from_headings(content)
    assert count >= 1
    assert "### 一、当前估值水平 [citation:2]" not in relocated
    assert "中高位[citation:2]" in relocated
    assert relocated.count("[citation:2]") == 2


def test_relocate_keeps_table_only_heading_citation() -> None:
    content = (
        "### 三、核心财务指标 [citation:1]\n\n"
        "| 指标 | 数值 |\n"
        "| --- | ---: |\n"
        "| 营业收入 | 312.5 亿元 |\n"
    )
    relocated, count = relocate_citations_from_headings(content)
    assert count == 0
    assert "### 三、核心财务指标 [citation:1]" in relocated


def test_pick_best_citation_content_penalizes_heading_only() -> None:
    heading_only = (
        "### 行业分析 [citation:1]\n\n"
        "公司营收 100 亿元，净利润 20 亿元。\n\n"
        "行业竞争加剧，龙头份额提升。"
    )
    paragraph_cited = (
        "### 行业分析\n\n"
        "公司营收 100 亿元，净利润 20 亿元[citation:1]。\n\n"
        "行业竞争加剧，龙头份额提升[citation:1]。"
    )
    best = pick_best_citation_content(heading_only, paragraph_cited)
    assert best == paragraph_cited


def test_narrative_paragraph_requires_citation() -> None:
    body = (
        "从行业竞争格局看，公司渠道改革持续推进，龙头地位在细分赛道仍较稳固。\n\n"
        "### 参考来源\n\n"
        "- [citation:1]测试"
    )
    missing = paragraphs_missing_trailing_citations(body)
    assert len(missing) == 1


def test_patch_narrative_paragraph_with_report_catalog() -> None:
    catalog = _catalog_with_report()
    content = (
        "从行业竞争格局看，宁德时代全球动力电池龙头地位仍较稳固，渠道与产能扩张持续推进。\n\n"
        "### 参考来源\n\n"
        "- 测试"
    )
    patched, count = patch_missing_citations(content, catalog)
    assert count >= 1
    assert "[citation:2]" in patched


def test_pick_best_citation_content_prefers_fewer_missing() -> None:
    draft = "公司营收 100 亿元，净利润 20 亿元。\n\n行业竞争加剧。"
    patched = "公司营收 100 亿元，净利润 20 亿元[citation:1]。\n\n行业竞争加剧。"
    revised = "公司营收 100 亿元，净利润 20 亿元。\n\n行业竞争加剧[citation:2]。"
    best = pick_best_citation_content(revised, patched, draft)
    assert count_paragraphs_missing_citations(best) <= count_paragraphs_missing_citations(draft)
