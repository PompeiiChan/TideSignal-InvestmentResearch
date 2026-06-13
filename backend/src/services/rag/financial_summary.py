"""Generate natural-language summary chunks from financial metric sections."""

from __future__ import annotations

import re

from .financial_units import format_yi as _to_yi

_REVENUE_RE = re.compile(
    r"营业收入[（(]元[）)]?\s*([\d,]+\.?\d*)",
)
_NET_PROFIT_RE = re.compile(
    r"归属于上市公司股东[\s\S]{0,40}?净利\s*润[（(]元[）)]?\s*([\d,]+\.?\d*)",
)
_YOY_RE = re.compile(r"([+-]?\d+\.?\d*)%")
_Q1_REVENUE_RE = re.compile(r"营业收入[（(]元[）)]?\s*([\d,]+\.?\d*)")
_Q1_PROFIT_RE = re.compile(
    r"归属于上市公司股东[\s\S]{0,40}?净利\s*润[（(]元[）)]?\s*([\d,]+\.?\d*)",
)


def _metrics_window(text: str, marker: str, *, max_chars: int = 5000) -> str:
    idx = text.find(marker)
    if idx < 0:
        return text[:max_chars]
    return text[idx : idx + max_chars]


def build_annual_summary(text: str, *, company_name: str, time_period: str) -> str:
    """Build a colloquial annual metrics summary from 主要会计数据和财务指标."""
    window = _metrics_window(text, "主要会计数据和财务指标")
    revenue_match = _REVENUE_RE.search(window)
    profit_match = _NET_PROFIT_RE.search(window)
    if not revenue_match or not profit_match:
        return ""

    revenue = revenue_match.group(1)
    profit = profit_match.group(1)
    yoy_matches = _YOY_RE.findall(window)
    revenue_yoy = yoy_matches[0] if yoy_matches else ""
    profit_yoy = yoy_matches[1] if len(yoy_matches) > 1 else ""

    label = company_name or "该公司"
    period = time_period or "2025年"
    lines = [
        f"{label}{period}业绩摘要：",
        f"营业收入{_to_yi(revenue)}",
    ]
    if revenue_yoy:
        lines[-1] += f"，同比{revenue_yoy}%"
    profit_line = f"归母净利润{_to_yi(profit)}"
    if profit_yoy:
        profit_line += f"，同比{profit_yoy}%"
    lines.append(profit_line + "。")

    if "毛利率" in text:
        margin_match = re.search(r"毛利率[：:\s]*([+-]?\d+\.?\d*)%?", text)
        if margin_match:
            lines.append(f"毛利率约{margin_match.group(1)}%。")

    return "\n".join(lines)


def build_quarterly_summary(text: str, *, company_name: str, time_period: str) -> str:
    """Build a colloquial Q1 summary from 一、主要财务数据."""
    window = _metrics_window(text, "一、主要财务数据")
    revenue_match = _Q1_REVENUE_RE.search(window)
    profit_match = _Q1_PROFIT_RE.search(window)
    if not revenue_match or not profit_match:
        return ""

    revenue = revenue_match.group(1)
    profit = profit_match.group(1)
    yoy_matches = _YOY_RE.findall(window)
    revenue_yoy = yoy_matches[0] if yoy_matches else ""
    profit_yoy = yoy_matches[1] if len(yoy_matches) > 1 else ""

    label = company_name or "该公司"
    period = time_period or "2026年一季度"
    lines = [
        f"{label}{period}业绩摘要：",
        f"营业收入{_to_yi(revenue)}",
    ]
    if revenue_yoy:
        lines[-1] += f"，同比{revenue_yoy}%"
    profit_line = f"归母净利润{_to_yi(profit)}"
    if profit_yoy:
        profit_line += f"，同比{profit_yoy}%"
    lines.append(profit_line + "。")
    return "\n".join(lines)
