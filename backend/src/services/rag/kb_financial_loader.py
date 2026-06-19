"""Load structured financial profiles from local knowledge-base Markdown files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ...integrations.market_data.sina_finance_client import sort_profiles_by_period
from ...integrations.market_data.stock_code_resolver import format_ticker

_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)


def find_financial_kb_file(kb_root: Path, stock_code: str) -> Path | None:
    financials_dir = kb_root / "financials"
    if not financials_dir.is_dir():
        return None
    code = stock_code.zfill(6)
    matches = sorted(financials_dir.glob(f"*{code}*financial*.md"))
    return matches[0] if matches else None


def _parse_metrics_table(section_text: str) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for row in _TABLE_ROW_RE.findall(section_text):
        left, middle, right = (cell.strip() for cell in row)
        if left in {"报表", "---", "字段"} or middle in {"科目", "内容", "---"}:
            continue
        metrics[middle] = right
    return metrics


def _parse_metric_number(raw: str) -> float | None:
    text = (raw or "").strip()
    if not text or text in {"—", "N/A"}:
        return None
    token = text.split()[0].replace(",", "")
    try:
        return float(token)
    except ValueError:
        return None


def _compute_debt_ratio_from_metrics(metrics: dict[str, str]) -> str | None:
    assets = _parse_metric_number(metrics.get("资产总计", ""))
    equity = _parse_metric_number(
        metrics.get("归属于母公司所有者权益合计")
        or metrics.get("所有者权益(或股东权益)合计")
        or ""
    )
    if assets is None or equity is None or assets <= 0:
        return None
    return f"{(assets - equity) / assets * 100:.2f}%"


def _all_metrics_sections(text: str) -> list[str]:
    parts = re.split(r"\n##\s+", text)
    return [part for part in parts if "### 主要财务数据" in part]


def _latest_metrics_section(text: str) -> str:
    sections = _all_metrics_sections(text)
    return sections[-1] if sections else ""


def _time_period_from_section(section_text: str) -> str:
    match = re.search(r"\|\s*时间口径\s*\|\s*([^|]+?)\s*\|", section_text)
    if match:
        return match.group(1).strip()
    if "年第一季度报告" in section_text:
        year_match = re.search(r"(20\d{2})\s*年第一季度报告", section_text)
        if year_match:
            return f"{year_match.group(1)}Q1"
    year_match = re.search(r"(20\d{2})\s*年年度报告", section_text)
    if year_match:
        return f"{year_match.group(1)}A"
    return ""


def _profile_from_metrics_section(
    section_text: str,
    *,
    stock_name: str,
    stock_code: str,
    source_note: str,
) -> dict[str, Any] | None:
    metrics = _parse_metrics_table(section_text)
    revenue = metrics.get("营业收入") or metrics.get("营业总收入", "")
    profit = metrics.get("归属于母公司所有者的净利润") or metrics.get("净利润", "")
    if not revenue and not profit:
        return None

    time_period = _time_period_from_section(section_text) or "未知"
    gross_margin = metrics.get("毛利率（推算）", "N/A")
    roe = metrics.get("净资产收益率 ROE（推算）", "N/A")
    operating_cash_flow = metrics.get("经营活动产生的现金流量净额", "N/A")
    debt_ratio = _compute_debt_ratio_from_metrics(metrics) or "N/A"
    highlights = [
        f"{time_period} 营收 {revenue}",
        f"归母净利润 {profit}",
        source_note,
    ]
    if operating_cash_flow != "N/A":
        highlights.append(f"经营现金流 {operating_cash_flow}")
    if debt_ratio != "N/A":
        highlights.append(f"资产负债率 {debt_ratio}")
    return {
        "company_id": f"company_{stock_code}",
        "ticker": format_ticker(stock_code),
        "stock_name": stock_name or stock_code,
        "industry": "未知",
        "time_period": time_period,
        "revenue": revenue,
        "net_profit": profit,
        "gross_margin": gross_margin,
        "roe": roe,
        "operating_cash_flow": operating_cash_flow,
        "debt_ratio": debt_ratio,
        "pe_ttm": "N/A",
        "highlights": highlights,
    }


def load_all_profiles_from_kb_file(
    path: Path,
    *,
    stock_name: str,
    stock_code: str,
) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    sections = _all_metrics_sections(text)
    source_note = f"数据来源：本地知识库 {path.name}"
    profiles: list[dict[str, Any]] = []
    for section in sections:
        profile = _profile_from_metrics_section(
            section,
            stock_name=stock_name,
            stock_code=stock_code,
            source_note=source_note,
        )
        if profile is not None:
            profiles.append(profile)
    return sort_profiles_by_period(profiles)


def load_profile_from_kb_file(
    path: Path,
    *,
    stock_name: str,
    stock_code: str,
) -> dict[str, Any] | None:
    profiles = load_all_profiles_from_kb_file(path, stock_name=stock_name, stock_code=stock_code)
    return profiles[0] if profiles else None
