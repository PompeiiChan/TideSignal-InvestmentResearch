"""Extract structured metadata from knowledge-base markdown tables."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
_FIELD_ALIASES = {
    "doc_id": "doc_id",
    "资料类型": "doc_type",
    "标题": "title",
    "公司id": "company_id",
    "公司ID": "company_id",
    "行业id": "industry_id",
    "行业ID": "industry_id",
    "时间口径": "time_period",
    "公司名称": "company_name",
    "股票代码": "ticker",
    "来源": "publisher",
}


@dataclass
class DocMetadata:
    """Normalized metadata extracted from migration tables."""

    doc_id: str = ""
    doc_type: str = ""
    title: str = ""
    company_id: str = ""
    industry_id: str = ""
    time_period: str = ""
    company_name: str = ""
    ticker: str = ""
    publisher: str = ""


def parse_metadata_table(text: str) -> DocMetadata:
    """Parse the first pipe-table block that contains doc_id."""
    for block in _iter_table_blocks(text):
        meta = _parse_table_block(block)
        if meta.doc_id or meta.company_id:
            return meta
    return DocMetadata()


def parse_all_metadata_tables(text: str) -> list[DocMetadata]:
    """Parse every metadata table in a document."""
    return [_parse_table_block(block) for block in _iter_table_blocks(text) if _parse_table_block(block).doc_id]


def build_context_prefix(meta: DocMetadata, breadcrumb: str = "") -> str:
    """Build a deterministic contextual prefix for embedding and display."""
    parts: list[str] = []
    if meta.company_name:
        ticker = f"({meta.ticker.split('.')[0]})" if meta.ticker else ""
        parts.append(f"{meta.company_name}{ticker}")
    elif meta.company_id:
        parts.append(meta.company_id.replace("company_", ""))

    if meta.time_period:
        parts.append(meta.time_period)
    elif meta.doc_type in {"annual_report", "quarterly_report"}:
        parts.append("年报" if meta.doc_type == "annual_report" else "一季报")

    if meta.title and not parts:
        parts.append(meta.title)
    elif breadcrumb and not parts:
        parts.append(breadcrumb.split(">")[-1].strip())

    doc_label = {
        "annual_report": "年报",
        "quarterly_report": "一季报",
        "company_research": "公司研报",
        "industry_research": "行业研报",
        "market_event": "市场热点",
    }.get(meta.doc_type, "")

    if doc_label and doc_label not in " ".join(parts):
        parts.append(doc_label)

    if breadcrumb:
        return f"{' '.join(parts)} | {breadcrumb}：".strip()
    if parts:
        return f"{' '.join(parts)}："
    return ""


def _iter_table_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            current.append(line)
            continue
        if current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def _parse_table_block(block: str) -> DocMetadata:
    meta = DocMetadata()
    for match in _TABLE_ROW_RE.finditer(block):
        raw_key = match.group(1).strip()
        if raw_key in {"字段", "---", "序号"} or set(raw_key) <= {"-"}:
            continue
        value = match.group(2).strip()
        if not value:
            continue
        field = _FIELD_ALIASES.get(raw_key)
        if field:
            setattr(meta, field, value)
    return meta
