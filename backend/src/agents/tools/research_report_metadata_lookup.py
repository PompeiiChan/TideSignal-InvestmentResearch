"""Eastmoney research-report metadata lookup for institutional view questions."""

from __future__ import annotations

from typing import Any

from ...integrations.market_data.em_research_report_client import (
    ATTRIBUTION,
    fetch_em_research_reports,
)
from ...integrations.market_data.stock_code_resolver import resolve_stock_code

_TOOL_NAME = "research_report_metadata_lookup"


def lookup_research_report_metadata(
    *,
    stock_name: str = "",
    stock_code: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Fetch recent sell-side report list (title, org, rating, EPS) from Eastmoney reportapi."""
    resolved_code, resolved_name = resolve_stock_code(stock_name, stock_code)
    code = (resolved_code or stock_code or "").zfill(6)
    if len(code) != 6 or not code.isdigit():
        return {
            "tool": _TOOL_NAME,
            "found": False,
            "stock_name": resolved_name or stock_name,
            "stock_code": code,
            "reports": [],
            "report_count": 0,
            "rating_summary": {},
            "is_mock": False,
            "data_origin": "",
            "fallback_used": True,
            "fallback_reason": "无法解析有效 A 股代码",
            "source": "",
            "attribution": ATTRIBUTION,
            "notes": "缺少有效股票代码，跳过东财研报元数据拉取",
        }

    try:
        payload = fetch_em_research_reports(code)
    except Exception as exc:
        return {
            "tool": _TOOL_NAME,
            "found": False,
            "stock_name": resolved_name or stock_name,
            "stock_code": code,
            "reports": [],
            "report_count": 0,
            "rating_summary": {},
            "is_mock": False,
            "data_origin": "eastmoney_reportapi",
            "fallback_used": True,
            "fallback_reason": str(exc),
            "source": "https://reportapi.eastmoney.com/report/list",
            "attribution": ATTRIBUTION,
            "notes": "东财研报元数据拉取失败",
        }

    if not payload.get("found"):
        return {
            "tool": _TOOL_NAME,
            "found": False,
            "stock_name": resolved_name or stock_name,
            "stock_code": code,
            "reports": [],
            "report_count": 0,
            "rating_summary": {},
            "is_mock": False,
            "data_origin": "eastmoney_reportapi",
            "fallback_used": True,
            "fallback_reason": str(payload.get("notes", "东财研报列表无记录")),
            "source": str(payload.get("source", "")),
            "attribution": ATTRIBUTION,
            "notes": str(payload.get("notes", "东财研报列表无记录")),
        }

    return {
        "tool": _TOOL_NAME,
        "found": True,
        "stock_name": resolved_name or stock_name,
        "stock_code": code,
        "reports": payload.get("reports") or [],
        "report_count": int(payload.get("report_count") or 0),
        "rating_summary": payload.get("rating_summary") or {},
        "is_mock": False,
        "data_origin": "eastmoney_reportapi",
        "fallback_used": False,
        "fallback_reason": "",
        "source": str(payload.get("source", "")),
        "attribution": ATTRIBUTION,
        "notes": str(payload.get("notes", "")),
    }
