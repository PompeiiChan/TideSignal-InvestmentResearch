"""Shared citation marker helpers for assembly and quality checks."""

from __future__ import annotations

import re
from typing import Any

CITATION_MARKER_RE = re.compile(r"\[citation:(\d+|财务)\]")
TRAILING_CITATION_RE = re.compile(r"(?:\[citation:(?:\d+|财务)\])+\s*$")
REFERENCE_SECTION_RE = re.compile(r"\n###\s+参考来源\b")
FACTUAL_PARAGRAPH_RE = re.compile(
    r"[\d%％]|同比|环比|亿元|万亿|万股|pct|ROE|PE|营收|净利润|毛利率|涨跌幅|收盘"
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


def _paragraph_needs_citation(paragraph: str) -> bool:
    if paragraph.startswith(">"):
        paragraph = paragraph.lstrip(">").strip()
    return bool(FACTUAL_PARAGRAPH_RE.search(paragraph))


def _paragraph_has_trailing_citation(paragraph: str) -> bool:
    return bool(TRAILING_CITATION_RE.search(paragraph.strip()))


def paragraphs_missing_trailing_citations(content: str) -> list[str]:
    """Return factual body paragraphs that lack citation markers at paragraph end."""
    body = REFERENCE_SECTION_RE.split(content, maxsplit=1)[0]
    missing: list[str] = []
    for paragraph in _split_paragraph_units(body):
        if not _paragraph_needs_citation(paragraph):
            continue
        if _paragraph_has_trailing_citation(paragraph):
            continue
        missing.append(paragraph[:120])
    return missing


def content_needs_citation_retry(content: str) -> bool:
    if not content_has_citation_markers(content):
        return True
    return bool(paragraphs_missing_trailing_citations(content))
