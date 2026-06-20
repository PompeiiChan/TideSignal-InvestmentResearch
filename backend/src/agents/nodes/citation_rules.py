"""Shared citation marker helpers for assembly and quality checks."""

from __future__ import annotations

import re
from typing import Any

CITATION_MARKER_RE = re.compile(r"\[citation:(\d+|财务)\]")
TRAILING_CITATION_RE = re.compile(
    r"(?:\[citation:(?:\d+|财务)\])+(?:[。．.!！?？,，;；:：、]\s*)?\s*$"
)
REFERENCE_SECTION_RE = re.compile(r"\n###\s+参考来源\b")
FACTUAL_PARAGRAPH_RE = re.compile(
    r"[\d%％]|同比|环比|亿元|万亿|万股|pct|ROE|PE|营收|净利润|毛利率|涨跌幅|收盘"
    r"|报告|披露|公告|分析师|机构|研报|季度|年报|份额|市占|产能|订单"
    r"|增长|下滑|提升|改善|预期|目标价|评级|龙头|竞争|行业",
    re.IGNORECASE,
)
NARRATIVE_EVIDENCE_RE = re.compile(
    r"(公司|行业|市场|业务|产品|渠道|客户|战略|板块|赛道).{6,}",
    re.IGNORECASE,
)
TRANSITION_ONLY_RE = re.compile(
    r"^(综上|总之|由此可见|换言之|另一方面|与此同时|需要注意的是)[，,：:]?\s*$"
)


def count_citation_markers(content: str) -> int:
    return len(CITATION_MARKER_RE.findall(content))


def content_has_citation_markers(content: str) -> bool:
    return bool(CITATION_MARKER_RE.search(content))


def evidence_requires_citations(
    *,
    rag_hits: list[Any],
    evidence_pack: dict[str, Any],
) -> bool:
    if rag_hits:
        return True
    tool_result = evidence_pack.get("tool_result")
    if isinstance(tool_result, dict) and tool_result:
        return True
    retrieved = evidence_pack.get("retrieved_chunks")
    return isinstance(retrieved, list) and bool(retrieved)


def _is_table_block(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    return all(line.startswith("|") for line in lines)


def _split_paragraph_units(text: str) -> list[str]:
    units: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        stripped = block.strip()
        if not stripped or stripped.startswith("###"):
            continue
        if _is_table_block(stripped):
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            for line in stripped.splitlines():
                item = line.strip()
                if item:
                    units.append(item)
            continue
        if re.match(r"^\d+\.\s", stripped):
            for line in stripped.splitlines():
                item = line.strip()
                if item:
                    units.append(item)
            continue
        units.append(stripped)
    return units


def _normalize_paragraph_for_match(paragraph: str) -> str:
    text = paragraph.strip()
    if text.startswith(">"):
        text = text.lstrip(">").strip()
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def _paragraph_needs_citation(paragraph: str) -> bool:
    normalized = _normalize_paragraph_for_match(paragraph)
    if len(normalized) < 12:
        return False
    if TRANSITION_ONLY_RE.match(normalized):
        return False
    if FACTUAL_PARAGRAPH_RE.search(normalized):
        return True
    return len(normalized) >= 48 and bool(NARRATIVE_EVIDENCE_RE.search(normalized))


def _paragraph_has_trailing_citation(paragraph: str) -> bool:
    return bool(TRAILING_CITATION_RE.search(paragraph.strip()))


def paragraph_has_citation_marker(paragraph: str) -> bool:
    """Whether the paragraph already contains any numeric citation marker."""
    return bool(CITATION_MARKER_RE.search(paragraph))


def paragraphs_missing_trailing_citations(content: str) -> list[str]:
    """Return factual body paragraphs that lack citation markers at paragraph end."""
    body = REFERENCE_SECTION_RE.split(content, maxsplit=1)[0]
    missing: list[str] = []
    for paragraph in _split_paragraph_units(body):
        if not _paragraph_needs_citation(paragraph):
            continue
        if _paragraph_has_trailing_citation(paragraph):
            continue
        missing.append(paragraph)
    return missing


def count_paragraphs_missing_citations(content: str) -> int:
    """Count body paragraphs that should have trailing citations but do not."""
    return len(paragraphs_missing_trailing_citations(content))


def _section_content_blocks(section_body: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", section_body.strip()) if block.strip()]


def _section_is_table_only(section_body: str) -> bool:
    blocks = _section_content_blocks(section_body)
    return bool(blocks) and all(_is_table_block(block) for block in blocks)


def _extract_trailing_citation_suffix(text: str) -> tuple[str, str]:
    stripped = text.rstrip()
    match = TRAILING_CITATION_RE.search(stripped)
    if not match:
        return stripped, ""
    return stripped[: match.start()].rstrip(), stripped[match.start() :].strip()


def iter_body_sections(content: str) -> list[tuple[str, str]]:
    """Split body (before 参考来源) into (heading_line, section_body) tuples."""
    body = REFERENCE_SECTION_RE.split(content, maxsplit=1)[0]
    parts = re.split(r"^(###\s+(?!参考来源).+)$", body, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    if parts and parts[0].strip():
        sections.append(("", parts[0]))
    index = 1
    while index < len(parts):
        heading = parts[index]
        section_body = parts[index + 1] if index + 1 < len(parts) else ""
        sections.append((heading, section_body))
        index += 2
    return sections


def count_misplaced_heading_citations(content: str) -> int:
    """Headings with trailing citation when the section has non-table narrative content."""
    misplaced = 0
    for heading, section_body in iter_body_sections(content):
        if not heading.strip().startswith("### "):
            continue
        _, citation_suffix = _extract_trailing_citation_suffix(heading.strip())
        if not citation_suffix:
            continue
        if not section_body.strip():
            continue
        if _section_is_table_only(section_body):
            continue
        misplaced += 1
    return misplaced


def citation_compliance_score(content: str) -> int:
    """Lower is better: missing paragraph citations + misplaced heading citations."""
    return (
        count_paragraphs_missing_citations(content) * 10
        + count_misplaced_heading_citations(content) * 25
    )


def content_needs_citation_retry(content: str) -> bool:
    if not content_has_citation_markers(content):
        return True
    if count_misplaced_heading_citations(content):
        return True
    return bool(paragraphs_missing_trailing_citations(content))
