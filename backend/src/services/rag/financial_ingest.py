"""Helpers for ChiNext financial KB ingest and validation (T-024)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

FINANCIAL_DATA_HEADING = "### 主要财务数据"
ANNUAL_SECTION_RE = re.compile(r"^## \d{4} 年年度报告", re.MULTILINE)
INTERIM_SECTION_RE = re.compile(
    r"^## \d{4} 年(?:第一|第二|第三|第四)?季度报告|^## \d{4} 年\d{2}月\d{2}日报告",
    re.MULTILINE,
)


def pick_financial_periods(report_lists: dict[str, dict[str, Any]]) -> list[str]:
    """Return latest interim plus up to three annual report keys (newest first)."""
    keys = sorted(report_lists.keys(), reverse=True)
    annuals = [key for key in keys if key.endswith("1231")][:3]
    interim = next((key for key in keys if not key.endswith("1231")), None)
    selected: list[str] = []
    if interim:
        selected.append(interim)
    for annual in annuals:
        if annual not in selected:
            selected.append(annual)
    if not selected and keys:
        selected.append(keys[0])
    return selected


def count_financial_data_sections(markdown: str) -> int:
    return markdown.count(FINANCIAL_DATA_HEADING)


def summarize_financial_kb_file(path: Path) -> dict[str, int | str]:
    """Count financial sections and report-period headings in a KB markdown file."""
    text = path.read_text(encoding="utf-8")
    return {
        "path": path.name,
        "financial_sections": count_financial_data_sections(text),
        "annual_sections": len(ANNUAL_SECTION_RE.findall(text)),
        "interim_sections": len(INTERIM_SECTION_RE.findall(text)),
    }


def kb_file_meets_t024_target(summary: dict[str, int | str], *, min_annuals: int = 3) -> bool:
    """True when file has latest interim and at least min_annuals annual periods (or max available)."""
    financial_sections = int(summary.get("financial_sections", 0))
    annual_sections = int(summary.get("annual_sections", 0))
    interim_sections = int(summary.get("interim_sections", 0))
    if financial_sections < 2:
        return False
    if interim_sections < 1:
        return False
    # Accept when we have 3 annuals, or fewer if the file already merged all available periods.
    return annual_sections >= min_annuals or financial_sections >= min_annuals + 1
