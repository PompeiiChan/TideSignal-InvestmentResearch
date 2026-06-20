"""Programmatic citation patching for response_assembly."""

from __future__ import annotations

import re

from ...services.citation_catalog import CitationCatalog

_VALUATION_KEYWORDS = re.compile(r"PE|PB|估值|分位|市值|市盈率|市净率", re.IGNORECASE)
_FINANCIAL_KEYWORDS = re.compile(
    r"营收|净利润|毛利率|ROE|现金流|负债|同比|环比|亿元|利润|收入",
    re.IGNORECASE,
)
CITATION_PATCH_PROMPT_MAX_CHARS = 800
_TRAILING_CITATION_RE = re.compile(
    r"(?:\[citation:(?:\d+|财务)\])+(?:[。．.!！?？,，;；:：、]\s*)?\s*$"
)
_CITATION_MARKER_INLINE_RE = re.compile(r"\[citation:(\d+|财务)\]")
_TRAILING_PUNCT_RE = re.compile(r"([。．.!！?？,，;；:：、]\s*)$")


def append_citation_marker(segment: str, marker: str) -> str:
    """Append citation before trailing punctuation when present."""
    stripped = segment.rstrip()
    if _TRAILING_CITATION_RE.search(stripped) or _CITATION_MARKER_INLINE_RE.search(stripped):
        return stripped
    punct_match = _TRAILING_PUNCT_RE.search(stripped)
    if punct_match:
        punct = punct_match.group(1)
        base = stripped[: -len(punct)].rstrip()
        return f"{base}{marker}{punct}"
    return f"{stripped}{marker}"


def _pick_citation_index(paragraph: str, catalog: CitationCatalog) -> int | None:
    financial_index = catalog.doc_index.get("__local_financial_tool__")
    valuation_index = catalog.doc_index.get("__valuation_tool__")
    consensus_index = catalog.doc_index.get("__consensus_tool__")
    research_index = catalog.doc_index.get("__research_report_tool__")
    stock_api_index = catalog.doc_index.get("__stock_api_tool__")
    ranking_index = catalog.doc_index.get("__market_ranking_tool__")
    heatmap_index = catalog.doc_index.get("__sector_heatmap_tool__")

    if _FINANCIAL_KEYWORDS.search(paragraph) and financial_index is not None:
        return financial_index
    if _VALUATION_KEYWORDS.search(paragraph) and valuation_index is not None:
        return valuation_index
    if re.search(r"一致预期|机构|EPS|评级|研报", paragraph) and consensus_index is not None:
        return consensus_index
    if re.search(r"研报|卖方|评级", paragraph) and research_index is not None:
        return research_index
    if re.search(r"公告|快讯|资讯|巨潮|东财", paragraph) and stock_api_index is not None:
        return stock_api_index
    if re.search(r"涨幅|排行|板块", paragraph) and ranking_index is not None:
        return ranking_index
    if re.search(r"热力图|成交|板块", paragraph) and heatmap_index is not None:
        return heatmap_index

    best_index: int | None = None
    best_len = 0
    for entry in catalog.entries:
        if entry.origin in {"local_financial_db", "stock_evidence_api"}:
            continue
        for token_len in (24, 16, 12, 8):
            token = entry.title[:token_len].strip()
            if len(token) >= 4 and token in paragraph and len(token) > best_len:
                best_index = entry.index
                best_len = len(token)
    if best_index is not None:
        return best_index

    for entry in catalog.entries:
        title_token = entry.title[:12]
        if title_token and title_token in paragraph:
            return entry.index
    if catalog.entries:
        return catalog.entries[0].index
    return None


def _locate_paragraph_span(body: str, paragraph: str) -> tuple[int, int] | None:
    candidates = [paragraph.rstrip(), paragraph.strip()]
    from ..nodes.citation_rules import _normalize_paragraph_for_match

    normalized = _normalize_paragraph_for_match(paragraph)
    if normalized not in candidates:
        candidates.append(normalized)

    for candidate in candidates:
        if not candidate:
            continue
        escaped = re.escape(candidate)
        match = re.search(escaped, body)
        if match:
            return match.span()
        short = candidate[:120].rstrip()
        if len(short) >= 24:
            match = re.search(re.escape(short), body)
            if match:
                return match.span()
    return None


def patch_missing_citations(content: str, catalog: CitationCatalog) -> tuple[str, int]:
    """Append best-effort [citation:N] markers to factual paragraphs missing them."""
    from ..nodes.citation_rules import paragraphs_missing_trailing_citations

    missing = paragraphs_missing_trailing_citations(content)
    if not missing:
        return content, 0

    body, _, tail = content.partition("### 参考来源")
    patched_count = 0
    for paragraph in sorted(missing, key=len, reverse=True):
        index = _pick_citation_index(paragraph, catalog)
        if index is None:
            continue
        marker = f"[citation:{index}]"
        span = _locate_paragraph_span(body, paragraph)
        if span is None:
            continue
        start, end = span
        segment = body[start:end].rstrip()
        if _TRAILING_CITATION_RE.search(segment) or _CITATION_MARKER_INLINE_RE.search(segment):
            continue
        body = body[:start] + append_citation_marker(segment, marker) + body[end:]
        patched_count += 1

    rebuilt = body
    if tail:
        rebuilt = f"{body.rstrip()}\n\n### 参考来源{tail}"
    return rebuilt, patched_count


def _append_citations_to_section(section_body: str, citation_suffix: str) -> tuple[str, int]:
    from ..nodes.citation_rules import (
        _paragraph_has_trailing_citation,
        _paragraph_needs_citation,
        _split_paragraph_units,
        paragraph_has_citation_marker,
    )

    marker = citation_suffix.strip()
    if not marker:
        return section_body, 0

    patched_count = 0
    updated = section_body
    for paragraph in sorted(_split_paragraph_units(section_body), key=len, reverse=True):
        if not _paragraph_needs_citation(paragraph):
            continue
        if _paragraph_has_trailing_citation(paragraph) or paragraph_has_citation_marker(paragraph):
            continue
        span = _locate_paragraph_span(updated, paragraph)
        if span is None:
            continue
        start, end = span
        segment = updated[start:end].rstrip()
        updated = updated[:start] + append_citation_marker(segment, marker) + updated[end:]
        patched_count += 1
    return updated, patched_count


def relocate_citations_from_headings(content: str) -> tuple[str, int]:
    """Move citations from ### headings to factual paragraphs unless the section is table-only."""
    from ..nodes.citation_rules import (
        _extract_trailing_citation_suffix,
        _section_is_table_only,
    )

    body, _, tail = content.partition("### 参考来源")
    if not body.strip():
        return content, 0

    lines = body.split("\n")
    output_lines: list[str] = []
    relocated = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("### ") and not stripped.startswith("### 参考来源"):
            heading_clean, citation_suffix = _extract_trailing_citation_suffix(stripped)
            if citation_suffix:
                section_lines: list[str] = []
                scan = index + 1
                while scan < len(lines):
                    next_stripped = lines[scan].strip()
                    if next_stripped.startswith("### ") and not next_stripped.startswith("### 参考来源"):
                        break
                    section_lines.append(lines[scan])
                    scan += 1
                section_text = "\n".join(section_lines)
                if section_text.strip() and not _section_is_table_only(section_text):
                    output_lines.append(heading_clean)
                    patched_body, count = _append_citations_to_section(section_text, citation_suffix)
                    if patched_body:
                        output_lines.extend(patched_body.split("\n"))
                    relocated += count
                    if count == 0 and citation_suffix:
                        relocated += 1
                    index = scan
                    continue
        output_lines.append(line)
        index += 1

    new_body = "\n".join(output_lines)
    if tail:
        return f"{new_body.rstrip()}\n\n### 参考来源{tail}", relocated
    return new_body, relocated


def build_citation_patch_prompt(
    *,
    missing_paragraphs: list[str],
    catalog: CitationCatalog,
    needs_reference_section: bool,
) -> str:
    """Compact incremental prompt for citation-only LLM retry."""
    valid_nums = ", ".join(str(entry.index) for entry in catalog.entries) or "1"
    hints = "；".join(item[:100] for item in missing_paragraphs[:4])
    lines = [
        "【引用修订】仅补缺失 citation，不重写正文结构。",
        f"可用编号：{valid_nums}。",
        "禁止在 `###` 章节标题行写 citation；只在叙述段落/列表行段末标注。",
        "仅当该节只有 Markdown 表、无表后解读段时，才允许 citation 标在表标题 `###` 行末。",
    ]
    if hints:
        lines.append(f"缺 citation 段落：{hints[:320]}。")
    if needs_reference_section:
        lines.append("文末须有 `### 参考来源`。")
    lines.append("段末写 `[citation:N]`，禁止 `[citation:财务]`。")
    prompt = "\n".join(lines)
    return prompt[:CITATION_PATCH_PROMPT_MAX_CHARS]


def pick_best_citation_content(*candidates: str) -> str:
    """Prefer the candidate with the lowest citation compliance score."""
    from ..nodes.citation_rules import citation_compliance_score

    best = candidates[0]
    best_score = citation_compliance_score(best)
    for candidate in candidates[1:]:
        if not candidate.strip():
            continue
        score = citation_compliance_score(candidate)
        if score < best_score:
            best = candidate
            best_score = score
    return best


def apply_citation_fix(
    content: str,
    catalog: CitationCatalog,
) -> tuple[str, bool, int]:
    """Patch citations programmatically; return patched content, applied flag, paragraph count."""
    from ..nodes.citation_rules import content_needs_citation_retry

    patched, count = patch_missing_citations(content, catalog)
    applied = count > 0 and not content_needs_citation_retry(patched)
    if applied:
        return patched, True, count
    if count > 0:
        return patched, False, count
    return content, False, 0
