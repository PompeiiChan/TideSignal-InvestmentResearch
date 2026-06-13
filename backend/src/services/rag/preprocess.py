"""Noise removal for PDF-parsed markdown bodies."""

from __future__ import annotations

import re

PAGE_MARKER_RE = re.compile(r"\[page \d+\]\s*")
FIGURE_CAPTION_RE = re.compile(r"^图\d+[：:].*?资料来源[：:].*$", re.MULTILINE)
DISCLAIMER_LINE_RE = re.compile(r"请务必阅读正文之后的免责声明部分.*")
REPORT_HEADER_RE = re.compile(
    r"^(证券研究报告|公司深度研究|行业研究报告|东吴证券研究所|请\s*务必阅读).*$",
    re.MULTILINE,
)
PAGE_FRACTION_RE = re.compile(r"^\d+/\d+\s*$", re.MULTILINE)
FIN_REPORT_BANNER_RE = re.compile(
    r"^[^\n]*(?:年度报告全文|年第一季度报告)\s*$",
    re.MULTILINE,
)
FIN_PAGE_NUMBER_RE = re.compile(r"^\d{1,3}\s*$", re.MULTILINE)
TABLE_TAG_RE = re.compile(r"\[Table_[A-Za-z]+\]")
CHART_NOISE_RE = re.compile(r"^[-\d.%\s]{8,}$", re.MULTILINE)


def clean_report_text(text: str) -> str:
    """Remove recurring PDF headers, footers and dangling figure captions."""
    cleaned = text
    cleaned = PAGE_MARKER_RE.sub("\n", cleaned)
    cleaned = FIGURE_CAPTION_RE.sub("", cleaned)
    cleaned = DISCLAIMER_LINE_RE.sub("", cleaned)
    cleaned = REPORT_HEADER_RE.sub("", cleaned)
    cleaned = PAGE_FRACTION_RE.sub("", cleaned)
    cleaned = CHART_NOISE_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def clean_financial_text(text: str) -> str:
    """Remove page markers and annual/quarterly report banners from financial text."""
    cleaned = PAGE_MARKER_RE.sub("\n", text)
    cleaned = FIN_REPORT_BANNER_RE.sub("", cleaned)
    cleaned = FIN_PAGE_NUMBER_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def merge_pages_for_statement(text: str) -> str:
    """Join statement pages into one continuous body without page noise."""
    return clean_financial_text(text)


def strip_table_tags(text: str) -> str:
    return TABLE_TAG_RE.sub("", text)
