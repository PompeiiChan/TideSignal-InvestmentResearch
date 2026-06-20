"""Compact citation context helpers for assembly (T-027)."""

from __future__ import annotations

import json
from typing import Any

from .rag.models import RagHit

COMPACT_SNIPPET_MAX_CHARS = 800
COMPACT_MAX_RAG_HITS = 6
COMPACT_MAX_API_FACTS = 6
COMPACT_MAX_CONSENSUS_SCENARIOS = 4
COMPACT_MAX_RESEARCH_REPORTS = 3
COMPACT_MAX_QUARTERLY_POINTS = 4

_FINANCIAL_PERIOD_KEYS = (
    "time_period",
    "revenue",
    "revenue_yoy",
    "net_profit",
    "net_profit_yoy",
    "gross_margin",
    "net_margin",
    "roe",
    "operating_cash_flow",
    "debt_ratio",
    "pe_ttm",
    "stock_name",
    "ticker",
)

_VALUATION_SNAPSHOT_KEYS = (
    "price",
    "pe_ttm",
    "pb",
    "market_cap",
    "data_origin",
    "as_of",
)

_VALUATION_METRIC_KEYS = (
    "current",
    "percentile",
    "median",
    "min",
    "max",
    "sample_count",
)

_QUARTERLY_POINT_KEYS = ("trade_date", "pe_ttm", "pb")

_FACT_KEYS = ("kind", "title", "time", "source", "summary")

_REPORT_KEYS = ("title", "publish_date", "institution", "rating", "target_price")


def dump_citation_json(data: Any, *, compact: bool) -> str:
    if compact:
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(data, ensure_ascii=False, indent=2)


def truncate_snippet(snippet: str, *, max_chars: int = COMPACT_SNIPPET_MAX_CHARS) -> str:
    text = snippet.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def slim_financial_period(period: dict[str, Any]) -> dict[str, Any]:
    return {key: period[key] for key in _FINANCIAL_PERIOD_KEYS if key in period}


def slim_financial_periods(periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [slim_financial_period(item) for item in periods if isinstance(item, dict)]


def slim_financial_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return slim_financial_period(profile)


def slim_valuation_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {key: snapshot[key] for key in _VALUATION_SNAPSHOT_KEYS if key in snapshot}


def slim_valuation_metric_block(block: dict[str, Any]) -> dict[str, Any]:
    return {key: block[key] for key in _VALUATION_METRIC_KEYS if key in block}


def slim_valuation_history(history: dict[str, Any]) -> dict[str, Any]:
    slim: dict[str, Any] = {
        "found": history.get("found"),
        "data_origin": history.get("data_origin"),
        "as_of": history.get("as_of"),
    }
    for metric_key in ("pe_ttm", "pb"):
        block = history.get(metric_key)
        if isinstance(block, dict):
            slim[metric_key] = slim_valuation_metric_block(block)
    quarterly = history.get("quarterly_series")
    if isinstance(quarterly, list):
        tail = quarterly[-COMPACT_MAX_QUARTERLY_POINTS :]
        slim["quarterly_series"] = [
            {key: point[key] for key in _QUARTERLY_POINT_KEYS if key in point}
            for point in tail
            if isinstance(point, dict)
        ]
    return slim


def slim_api_facts(facts: list[Any], *, max_items: int = COMPACT_MAX_API_FACTS) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    for item in facts[:max_items]:
        if not isinstance(item, dict):
            continue
        trimmed.append({key: item[key] for key in _FACT_KEYS if key in item})
    return trimmed


def slim_research_reports(reports: list[Any]) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    for item in reports[:COMPACT_MAX_RESEARCH_REPORTS]:
        if not isinstance(item, dict):
            continue
        trimmed.append({key: item[key] for key in _REPORT_KEYS if key in item})
    return trimmed


def rag_hits_for_assembly(rag_hits: list[RagHit], *, compact: bool) -> list[RagHit]:
    if not compact:
        return rag_hits
    limited = rag_hits[:COMPACT_MAX_RAG_HITS]
    return [
        hit.model_copy(update={"snippet": truncate_snippet(hit.snippet)})
        for hit in limited
    ]
