"""Tests for financial KB ingest helpers (T-024)."""

from __future__ import annotations

from pathlib import Path

from backend.src.services.rag.financial_ingest import (
    count_financial_data_sections,
    kb_file_meets_t024_target,
    pick_financial_periods,
    summarize_financial_kb_file,
)


def test_pick_financial_periods_prefers_interim_and_three_annuals() -> None:
    keys = {
        "20260331": {},
        "20251231": {},
        "20241231": {},
        "20231231": {},
        "20221231": {},
    }
    assert pick_financial_periods(keys) == [
        "20260331",
        "20251231",
        "20241231",
        "20231231",
    ]


def test_count_financial_data_sections() -> None:
    markdown = "## 2025 年年度报告\n\n### 主要财务数据\n\nx\n\n## 2024 年年度报告\n\n### 主要财务数据\n\n"
    assert count_financial_data_sections(markdown) == 2


def test_summarize_liyade_kb_file_after_refresh() -> None:
    financials_dir = Path(__file__).resolve().parents[1] / "data/knowledge-base/financials"
    matches = sorted(financials_dir.glob("300296-*.md"))
    assert matches, "expected 利亚德 KB file"
    summary = summarize_financial_kb_file(matches[-1])
    assert summary["financial_sections"] >= 4
    assert summary["annual_sections"] >= 3
    assert summary["interim_sections"] >= 1
    assert kb_file_meets_t024_target(summary) is True
