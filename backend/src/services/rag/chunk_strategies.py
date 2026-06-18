"""Type-specific knowledge-base chunking strategies."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .financial_summary import build_annual_summary, build_quarterly_summary
from .financial_units import convert_financial_yuan_to_yi
from .metadata import (
    DocMetadata,
    build_context_prefix,
    parse_all_metadata_tables,
    parse_metadata_table,
)
from .models import ChunkRole, KnowledgeChunk, SourceType
from .preprocess import (
    clean_financial_text,
    clean_report_text,
    merge_pages_for_statement,
    strip_table_tags,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_SKIP_H2 = frozenset({"迁移元数据", "文件说明", "数据表说明", "字段", "数据"})
_CHILD_MAX_CHARS = 900
_PARENT_MAX_CHARS = 4500
_PROSE_OVERLAP_CHARS = 120
_MIN_CHUNK_CHARS = 80

_REPORT_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\s*\.?\s+(.+)$", re.MULTILINE)
_FIN_REPORT_SPLIT_RE = re.compile(r"^## (2025 年年度报告|2026 年第一季度报告)\s*$", re.MULTILINE)
_FIN_SECTION_RE = re.compile(r"^第[一二三四五六七八九十百]+节 .+$", re.MULTILINE)
_STATEMENT_START_RE = re.compile(
    r"^(?:\d+[、．.]\s*)?(合并资产负债表|合并利润表|合并现金流量表|母公司资产负债表|母公司利润表|母公司现金流量表)",
    re.MULTILINE,
)
_MDA_SUBSECTION_RE = re.compile(r"^[一二三四五六七八九十]+、.+$", re.MULTILINE)
_PROFIT_FORECAST_RE = re.compile(
    r"\[Table_EPS\].*?P/E.*?(?=\n\[page |\n\d+\.\d+\s|\Z)",
    re.DOTALL,
)
_RAW_TEXT_MARKERS = ("## 原始解析文本", "### 原始解析文本")


def chunk_hotspot_file(path: Path, text: str, *, relative: str, file_meta: DocMetadata) -> list[KnowledgeChunk]:
    """Recursive heading split: ### child embed units, ## parent context."""
    doc_title = _extract_title(text) or path.stem.replace("-", " ")
    doc_id = file_meta.doc_id or path.stem
    chunks: list[KnowledgeChunk] = []

    for section_index, (h2_title, h2_body) in enumerate(_split_by_level(text, level=2)):
        if not h2_body.strip() or h2_title in _SKIP_H2:
            continue
        breadcrumb_base = f"{doc_title} > {h2_title}"
        parent_id = f"{doc_id}_h2_{section_index:03d}"
        parent_text = f"## {h2_title}\n\n{h2_body.strip()}"

        h3_sections = _split_by_level(h2_body, level=3)
        has_h3 = any(title for title, _ in h3_sections)

        if has_h3:
            for h3_index, (h3_title, h3_body) in enumerate(h3_sections):
                if not h3_title or not h3_body.strip():
                    continue
                breadcrumb = f"{breadcrumb_base} > {h3_title}"
                for part_index, part in enumerate(_split_prose(h3_body)):
                    chunk = _make_chunk(
                        chunk_id=f"{doc_id}_h2{section_index:03d}_h3{h3_index:03d}_{part_index:03d}",
                        doc_id=doc_id,
                        title=doc_title,
                        source_type="market",
                        path=relative,
                        body=part,
                        meta=file_meta,
                        breadcrumb=breadcrumb,
                        section_title=h3_title,
                        parent_chunk_id=parent_id,
                        parent_text=parent_text[:_PARENT_MAX_CHARS],
                        chunk_role="child",
                    )
                    if chunk:
                        chunks.append(chunk)
        else:
            for part_index, part in enumerate(_split_prose(h2_body)):
                chunk = _make_chunk(
                    chunk_id=f"{doc_id}_h2_{section_index:03d}_{part_index:03d}",
                    doc_id=doc_id,
                    title=doc_title,
                    source_type="market",
                    path=relative,
                    body=part,
                    meta=file_meta,
                    breadcrumb=breadcrumb_base,
                    section_title=h2_title,
                    parent_chunk_id=parent_id,
                    parent_text=parent_text[:_PARENT_MAX_CHARS],
                    chunk_role="child",
                )
                if chunk:
                    chunks.append(chunk)
    return chunks


def chunk_report_file(
    path: Path,
    text: str,
    *,
    relative: str,
    file_meta: DocMetadata,
    source_type: SourceType,
) -> list[KnowledgeChunk]:
    """Clean PDF noise, isolate profit table, split by numbered headings."""
    doc_id = file_meta.doc_id or path.stem
    title = file_meta.title or _extract_title(text) or path.stem
    raw_body = _extract_raw_body(text)
    if not raw_body:
        return _chunk_generic_sections(path, text, relative=relative, file_meta=file_meta, source_type=source_type)

    cleaned = clean_report_text(raw_body)
    chunks: list[KnowledgeChunk] = []

    profit_block = _extract_profit_forecast(cleaned)
    if profit_block:
        chunk = _make_chunk(
            chunk_id=f"{doc_id}_profit_forecast_000",
            doc_id=doc_id,
            title=title,
            source_type=source_type,
            path=relative,
            body=strip_table_tags(profit_block),
            meta=file_meta,
            breadcrumb=f"{title} > 盈利预测和财务指标",
            section_title="盈利预测和财务指标",
            chunk_role="child",
        )
        if chunk:
            chunks.append(chunk)

    sections = _split_report_sections(cleaned)
    for index, (section_no, section_title, section_body) in enumerate(sections):
        if profit_block and section_title in {"盈利预测", "盈利预测与估值"}:
            continue
        breadcrumb = f"{title} > {section_no} {section_title}".strip()
        parent_id = f"{doc_id}_sec_{index:03d}"
        parent_text = f"{section_no} {section_title}\n\n{section_body}"
        for part_index, part in enumerate(_split_prose(section_body)):
            chunk = _make_chunk(
                chunk_id=f"{doc_id}_sec_{index:03d}_{part_index:03d}",
                doc_id=doc_id,
                title=title,
                source_type=source_type,
                path=relative,
                body=part,
                meta=file_meta,
                breadcrumb=breadcrumb,
                section_title=section_title,
                parent_chunk_id=parent_id,
                parent_text=parent_text[:_PARENT_MAX_CHARS],
                chunk_role="child",
            )
            if chunk:
                chunks.append(chunk)
    return chunks


def chunk_financial_file(path: Path, text: str, *, relative: str) -> list[KnowledgeChunk]:
    """Split annual/Q1 reports, preserve whole statements, add NL summaries."""
    chunks: list[KnowledgeChunk] = []
    reports = _split_financial_reports(text)
    if not reports:
        meta = parse_metadata_table(text)
        return _chunk_generic_sections(path, text, relative=relative, file_meta=meta, source_type="financial")

    company_name = ""
    for report_title, report_body, meta in reports:
        if meta.company_name:
            company_name = meta.company_name
        doc_id = meta.doc_id or _slug(report_title)
        title = meta.title or report_title
        cleaned = clean_financial_text(report_body)

        summary_text = ""
        if meta.doc_type == "annual_report" and "主要会计数据和财务指标" in cleaned:
            summary_text = build_annual_summary(
                cleaned,
                company_name=company_name or meta.company_name,
                time_period=meta.time_period or "2025年",
            )
        elif meta.doc_type == "quarterly_report" and "主要财务数据" in cleaned:
            summary_text = build_quarterly_summary(
                cleaned,
                company_name=company_name or meta.company_name,
                time_period=meta.time_period or "2026Q1",
            )
        if summary_text:
            summary_chunk = _make_chunk(
                chunk_id=f"{doc_id}_nl_summary_000",
                doc_id=doc_id,
                title=title,
                source_type="financial",
                path=relative,
                body=summary_text,
                meta=meta,
                breadcrumb=f"{title} > 业绩摘要",
                section_title="业绩摘要",
                chunk_role="summary",
            )
            if summary_chunk:
                chunks.append(summary_chunk)

        fin_sections = _split_financial_sections(cleaned)
        for sec_index, (section_title, section_body) in enumerate(fin_sections):
            section_label = section_title or f"section_{sec_index}"
            breadcrumb = f"{title} > {section_label}"
            is_mda = "管理层讨论与分析" in section_label
            is_accounting_policy = "重要会计政策" in section_body or "会计政策及会计估计" in section_label
            is_financial_report = "第八节" in section_label or "财务报告" in section_label

            if is_financial_report:
                chunks.extend(
                    _chunk_financial_statements(
                        section_body,
                        doc_id=doc_id,
                        title=title,
                        path=relative,
                        meta=meta,
                        breadcrumb_base=breadcrumb,
                    )
                )
                policy_body = _strip_statements(section_body)
                if policy_body.strip():
                    chunks.extend(
                        _chunk_policy_section(
                            policy_body,
                            doc_id=doc_id,
                            title=title,
                            path=relative,
                            meta=meta,
                            breadcrumb=f"{breadcrumb} > 会计政策",
                            section_index=sec_index,
                        )
                    )
                continue

            if is_mda:
                subsections = _split_mda_subsections(section_body)
                for sub_index, (sub_title, sub_body) in enumerate(subsections):
                    sub_breadcrumb = f"{breadcrumb} > {sub_title}" if sub_title else breadcrumb
                    for part_index, part in enumerate(_split_prose(sub_body)):
                        chunk = _make_chunk(
                            chunk_id=f"{doc_id}_mda_{sec_index:03d}_{sub_index:03d}_{part_index:03d}",
                            doc_id=doc_id,
                            title=title,
                            source_type="financial",
                            path=relative,
                            body=part,
                            meta=meta,
                            breadcrumb=sub_breadcrumb,
                            section_title=sub_title or section_label,
                            parent_chunk_id=f"{doc_id}_sec_{sec_index:03d}",
                            parent_text=section_body[:_PARENT_MAX_CHARS],
                            chunk_role="child",
                        )
                        if chunk:
                            chunks.append(chunk)
                continue

            weight = 0.35 if is_accounting_policy else 1.0
            max_chars = _PARENT_MAX_CHARS if is_accounting_policy else _CHILD_MAX_CHARS
            for part_index, part in enumerate(_split_prose(section_body, max_chars=max_chars)):
                chunk = _make_chunk(
                    chunk_id=f"{doc_id}_sec_{sec_index:03d}_{part_index:03d}",
                    doc_id=doc_id,
                    title=title,
                    source_type="financial",
                    path=relative,
                    body=part,
                    meta=meta,
                    breadcrumb=breadcrumb,
                    section_title=section_label,
                    parent_chunk_id=f"{doc_id}_sec_{sec_index:03d}",
                    parent_text=section_body[:_PARENT_MAX_CHARS],
                    chunk_role="child",
                    retrieval_weight=weight,
                )
                if chunk:
                    chunks.append(chunk)
    return chunks


def chunk_structured_file(path: Path, text: str, *, relative: str, file_meta: DocMetadata) -> list[KnowledgeChunk]:
    """Fallback chunking for structured-data markdown tables."""
    doc_id = file_meta.doc_id or path.stem
    title = _extract_title(text) or path.stem
    chunks: list[KnowledgeChunk] = []
    for section_index, (section_title, section_body) in enumerate(_split_by_level(text, level=2)):
        if section_title in _SKIP_H2 or not section_body.strip():
            continue
        for part_index, part in enumerate(_split_prose(section_body)):
            chunk = _make_chunk(
                chunk_id=f"{doc_id}_k_{section_index:03d}_{part_index:03d}",
                doc_id=doc_id,
                title=title,
                source_type="knowledge",
                path=relative,
                body=part,
                meta=file_meta,
                breadcrumb=f"{title} > {section_title}",
                section_title=section_title,
                chunk_role="child",
            )
            if chunk:
                chunks.append(chunk)
    return chunks


def _chunk_financial_statements(
    section_body: str,
    *,
    doc_id: str,
    title: str,
    path: str,
    meta: DocMetadata,
    breadcrumb_base: str,
) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    matches = list(_STATEMENT_START_RE.finditer(section_body))
    if not matches:
        return chunks

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section_body)
        statement_name = match.group(1)
        raw_statement = section_body[start:end]
        merged = merge_pages_for_statement(raw_statement)
        if len(merged.strip()) < _MIN_CHUNK_CHARS:
            continue
        breadcrumb = f"{breadcrumb_base} > {statement_name}"
        parent_id = f"{doc_id}_stmt_{index:03d}"
        embed_parts = _split_statement_for_embed(merged, max_chars=_CHILD_MAX_CHARS)
        for part_index, part in enumerate(embed_parts):
            chunk = _make_chunk(
                chunk_id=f"{parent_id}_{part_index:03d}",
                doc_id=doc_id,
                title=title,
                source_type="financial",
                path=path,
                body=part,
                meta=meta,
                breadcrumb=breadcrumb,
                section_title=statement_name,
                parent_chunk_id=parent_id,
                parent_text=merged,
                chunk_role="child",
            )
            if chunk:
                chunks.append(chunk)
    return chunks


def _split_statement_for_embed(text: str, *, max_chars: int) -> list[str]:
    """Split a full financial statement for embedding while repeating table headers."""
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return [stripped]

    lines = [line for line in stripped.splitlines() if line.strip()]
    if not lines:
        return [stripped[:max_chars]]

    header_end = 0
    for index, line in enumerate(lines[:8]):
        if any(marker in line for marker in ("项目", "编制单位", "单位：元", "单位:元")) or index < 4:
            header_end = index + 1
    header_lines = lines[: max(header_end, 3)]
    header = "\n".join(header_lines)
    data_lines = lines[len(header_lines) :]

    parts: list[str] = []
    buffer = header
    for line in data_lines:
        candidate = f"{buffer}\n{line}" if buffer else line
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if len(buffer) > len(header):
            parts.append(buffer)
        buffer = f"{header}\n{line}" if header else line
    if buffer.strip():
        parts.append(buffer)
    return parts or [stripped[:max_chars]]


def _chunk_policy_section(
    body: str,
    *,
    doc_id: str,
    title: str,
    path: str,
    meta: DocMetadata,
    breadcrumb: str,
    section_index: int,
) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for part_index, part in enumerate(_split_prose(body, max_chars=_CHILD_MAX_CHARS)):
        chunk = _make_chunk(
            chunk_id=f"{doc_id}_policy_{section_index:03d}_{part_index:03d}",
            doc_id=doc_id,
            title=title,
            source_type="financial",
            path=path,
            body=part,
            meta=meta,
            breadcrumb=breadcrumb,
            section_title="会计政策及会计估计",
            chunk_role="child",
            retrieval_weight=0.35,
        )
        if chunk:
            chunks.append(chunk)
    return chunks


def _chunk_generic_sections(
    path: Path,
    text: str,
    *,
    relative: str,
    file_meta: DocMetadata,
    source_type: SourceType,
) -> list[KnowledgeChunk]:
    doc_id = file_meta.doc_id or path.stem
    title = file_meta.title or _extract_title(text) or path.stem
    chunks: list[KnowledgeChunk] = []
    for section_index, (section_title, section_body) in enumerate(_split_by_level(text, level=2)):
        if section_title in _SKIP_H2 or not section_body.strip():
            continue
        for part_index, part in enumerate(_split_prose(section_body)):
            chunk = _make_chunk(
                chunk_id=f"{doc_id}_g_{section_index:03d}_{part_index:03d}",
                doc_id=doc_id,
                title=title,
                source_type=source_type,
                path=relative,
                body=part,
                meta=file_meta,
                breadcrumb=f"{title} > {section_title}",
                section_title=section_title,
                chunk_role="child",
            )
            if chunk:
                chunks.append(chunk)
    return chunks


def _make_chunk(
    *,
    chunk_id: str,
    doc_id: str,
    title: str,
    source_type: SourceType,
    path: str,
    body: str,
    meta: DocMetadata,
    breadcrumb: str,
    section_title: str = "",
    parent_chunk_id: str = "",
    parent_text: str = "",
    chunk_role: ChunkRole = "child",
    retrieval_weight: float = 1.0,
) -> KnowledgeChunk | None:
    body = body.strip()
    min_chars = 40 if chunk_role == "summary" else _MIN_CHUNK_CHARS
    if len(body) < min_chars:
        return None

    if source_type == "financial":
        body = convert_financial_yuan_to_yi(body)
        if parent_text:
            parent_text = convert_financial_yuan_to_yi(parent_text.strip())

    prefix = build_context_prefix(meta, breadcrumb)
    chunk_text = f"{prefix}\n{body}" if prefix else body
    embed_text = chunk_text
    return KnowledgeChunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        title=title,
        source_type=source_type,
        path=path,
        chunk_text=chunk_text,
        embed_text=embed_text,
        section_title=section_title,
        parent_chunk_id=parent_chunk_id,
        parent_text=parent_text,
        chunk_role=chunk_role,
        company_id=meta.company_id,
        industry_id=meta.industry_id,
        doc_type=meta.doc_type,
        time_period=meta.time_period,
        publisher=meta.publisher,
        breadcrumb=breadcrumb,
        retrieval_weight=retrieval_weight,
    )


def _split_by_level(text: str, *, level: int) -> list[tuple[str, str]]:
    prefix = "#" * level
    matches = [match for match in _HEADING_RE.finditer(text) if match.group(1) == prefix]
    if not matches:
        return [("", text)]

    sections: list[tuple[str, str]] = []
    preamble_end = matches[0].start()
    if preamble_end > 0:
        preamble = text[:preamble_end].strip()
        if preamble:
            sections.append(("", preamble))

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body or match.group(2).strip():
            sections.append((match.group(2).strip(), body))
    return sections or [("", text)]


def _split_prose(text: str, *, max_chars: int = _CHILD_MAX_CHARS) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return []

    merged: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            merged.append(buffer)
        if len(paragraph) <= max_chars:
            buffer = paragraph
            continue
        merged.extend(_hard_split_with_overlap(paragraph, max_chars))
        buffer = ""
    if buffer:
        merged.append(buffer)
    return merged


def _hard_split_with_overlap(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        parts.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - _PROSE_OVERLAP_CHARS, start + 1)
    return parts


def _split_financial_reports(text: str) -> list[tuple[str, str, DocMetadata]]:
    matches = list(_FIN_REPORT_SPLIT_RE.finditer(text))
    if not matches:
        return []

    all_meta = parse_all_metadata_tables(text)
    meta_by_doc: dict[str, DocMetadata] = {item.doc_id: item for item in all_meta if item.doc_id}
    reports: list[tuple[str, str, DocMetadata]] = []

    for index, match in enumerate(matches):
        title = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        section_meta = parse_metadata_table(body)
        if not section_meta.doc_id:
            for candidate in meta_by_doc.values():
                if title.startswith("2025") and candidate.doc_type == "annual_report":
                    section_meta = candidate
                    break
                if title.startswith("2026") and candidate.doc_type == "quarterly_report":
                    section_meta = candidate
                    break
        reports.append((title, body, section_meta))
    return reports


def _split_financial_sections(text: str) -> list[tuple[str, str]]:
    matches = list(_FIN_SECTION_RE.finditer(text))
    if not matches:
        return [("", text)]

    sections: list[tuple[str, str]] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(("前言", preamble))

    for index, match in enumerate(matches):
        title = match.group(0).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title, body))
    return sections


def _split_mda_subsections(text: str) -> list[tuple[str, str]]:
    matches = list(_MDA_SUBSECTION_RE.finditer(text))
    if not matches:
        return [("", text)]

    sections: list[tuple[str, str]] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))

    for index, match in enumerate(matches):
        title = match.group(0).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title, body))
    return sections


def _split_report_sections(text: str) -> list[tuple[str, str, str]]:
    """Split report body by numbered headings like 1.1. 动力."""
    matches: list[re.Match[str]] = []
    for line_match in _REPORT_SECTION_RE.finditer(text):
        if line_match.start() > 0 and text[line_match.start() - 1] not in "\n":
            continue
        num = line_match.group(1)
        if "." not in num and int(num) > 20:
            continue
        matches.append(line_match)

    if not matches:
        return [("", "正文", text)]

    sections: list[tuple[str, str, str]] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(("", "前言", preamble))

    for index, match in enumerate(matches):
        section_no = match.group(1)
        section_title = re.sub(r"\s+", " ", match.group(2)).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((section_no, section_title, body))
    return sections


def _extract_raw_body(text: str) -> str:
    for marker in _RAW_TEXT_MARKERS:
        idx = text.find(marker)
        if idx >= 0:
            return text[idx + len(marker) :].strip()
    return ""


def _extract_profit_forecast(text: str) -> str:
    match = _PROFIT_FORECAST_RE.search(text)
    if match:
        return _trim_profit_forecast(match.group(0))
    if "[Table_EPS]" in text:
        start = text.find("[Table_EPS]")
        end = text.find("[page 2]", start)
        snippet = text[start:end if end > start else start + 2500]
        return _trim_profit_forecast(strip_table_tags(snippet))
    return ""


def _trim_profit_forecast(text: str, *, max_chars: int = 1800) -> str:
    """Keep only the high-value profit-forecast table region."""
    cleaned = strip_table_tags(text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    for marker in ("投资要点", "内容目录", "[page 2]"):
        idx = cleaned.find(marker)
        if idx > 0:
            cleaned = cleaned[:idx].strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
    return cleaned


def _strip_statements(section_body: str) -> str:
    matches = list(_STATEMENT_START_RE.finditer(section_body))
    if not matches:
        return section_body
    kept: list[str] = []
    last_end = 0
    for index, match in enumerate(matches):
        kept.append(section_body[last_end : match.start()])
        last_end = matches[index + 1].start() if index + 1 < len(matches) else len(section_body)
    return "".join(kept)


def _extract_title(text: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _slug(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return digest
