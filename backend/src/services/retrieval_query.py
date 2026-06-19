"""Rule-based retrieval query builder for query_rewrite (T-014 Phase ①)."""

from __future__ import annotations

import re
from typing import Any, Literal

RewriteMethod = Literal["passthrough", "rule_slots", "rule_multiturn"]

_FINANCIAL_KEYWORDS = re.compile(
    r"年报|季报|财报|一季报|二季报|三季报|四季报|半年报|中报|业绩|营收|净利润|利润"
)
_YEAR_PATTERN = re.compile(r"20\d{2}")
_DEICTIC_PATTERN = re.compile(r"(呢|怎么样|如何|怎样|咋样|它|这个|那个|这家|该股|该公司)")

_QUARTER_LABELS = {
    "1": "一季报",
    "2": "二季报",
    "3": "三季报",
    "4": "四季报",
}


def _slot_text(slots: dict[str, Any], key: str) -> str:
    value = slots.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _is_short_or_deictic_query(query: str) -> bool:
    text = query.strip()
    if not text:
        return False
    if len(text) <= 12:
        return True
    return bool(_DEICTIC_PATTERN.search(text))


def _query_already_rich(query: str, stock_name: str) -> bool:
    if _FINANCIAL_KEYWORDS.search(query) and _YEAR_PATTERN.search(query):
        return True
    return bool(stock_name and stock_name in query and _FINANCIAL_KEYWORDS.search(query))


def _format_time_range(time_range: str) -> str:
    text = time_range.strip()
    if not text:
        return ""
    quarter_match = re.match(r"^(20\d{2})Q([1-4])$", text, re.IGNORECASE)
    if quarter_match:
        year, quarter = quarter_match.group(1), quarter_match.group(2)
        return f"{year}年{_QUARTER_LABELS[quarter]}"
    annual_match = re.match(r"^(20\d{2})A$", text, re.IGNORECASE)
    if annual_match:
        return f"{annual_match.group(1)}年年报"
    return text


def _period_hint_from_query(query: str) -> str:
    if "一季报" in query:
        return "一季报"
    if "二季报" in query or "中报" in query or "半年报" in query:
        return "二季报"
    if "三季报" in query:
        return "三季报"
    if "四季报" in query:
        return "四季报"
    if "年报" in query:
        return "年报"
    return ""


def _build_stock_retrieval_query(
    query: str,
    *,
    stock_name: str,
    time_range: str,
    analysis_dimension: str,
) -> tuple[str, RewriteMethod]:
    parts: list[str] = [stock_name]
    formatted_range = _format_time_range(time_range)
    if formatted_range:
        parts.append(formatted_range)
    else:
        period_hint = _period_hint_from_query(query)
        if period_hint:
            parts.append(period_hint)
    if analysis_dimension and analysis_dimension not in parts:
        parts.append(analysis_dimension)
    if ("财报" not in query and not any("报" in part for part in parts)) or (
        "财报" not in " ".join(parts) and _FINANCIAL_KEYWORDS.search(query)
    ):
        parts.append("财报")
    retrieval_query = " ".join(part for part in parts if part)
    method: RewriteMethod = (
        "rule_multiturn" if _is_short_or_deictic_query(query) else "rule_slots"
    )
    return retrieval_query, method


def build_retrieval_query(
    normalized_query: str,
    *,
    intent_id: str,
    slots: dict[str, Any],
    conversation_context: dict[str, Any] | None = None,
) -> tuple[str, RewriteMethod, bool]:
    """Return (retrieval_query, rewrite_method, changed)."""
    _ = conversation_context
    query = normalized_query.strip()
    if not query:
        return query, "passthrough", False

    stock_name = _slot_text(slots, "stock_name")
    time_range = _slot_text(slots, "time_range")
    topic = _slot_text(slots, "topic")
    industry = _slot_text(slots, "industry")
    document_id = _slot_text(slots, "document_id")
    analysis_dimension = _slot_text(slots, "analysis_dimension")

    if _query_already_rich(query, stock_name):
        return query, "passthrough", False

    if intent_id in {"stock_analysis", "document_qa"} and stock_name:
        needs_rewrite = _is_short_or_deictic_query(query) or stock_name not in query
        if needs_rewrite:
            retrieval_query, method = _build_stock_retrieval_query(
                query,
                stock_name=stock_name,
                time_range=time_range,
                analysis_dimension=analysis_dimension,
            )
            return retrieval_query, method, retrieval_query != query

    if intent_id == "stock_analysis" and stock_name and not time_range:
        dimension = analysis_dimension or ("基本面" if "基本面" in query else "")
        if dimension and (_is_short_or_deictic_query(query) or stock_name not in query):
            retrieval_query = f"{stock_name} {dimension} 财报".strip()
            return retrieval_query, "rule_slots", retrieval_query != query

    if intent_id == "hotspot_analysis":
        parts = [part for part in (topic, industry, _format_time_range(time_range)) if part]
        if parts and (_is_short_or_deictic_query(query) or not all(part in query for part in parts)):
            retrieval_query = " ".join(parts)
            if retrieval_query != query:
                return retrieval_query, "rule_slots", True

    if intent_id == "document_qa":
        parts = [part for part in (stock_name, document_id, _format_time_range(time_range)) if part]
        if parts and (_is_short_or_deictic_query(query) or stock_name not in query):
            retrieval_query = " ".join([*parts, query]) if query not in parts else " ".join(parts)
            doc_method: RewriteMethod = (
                "rule_multiturn" if _is_short_or_deictic_query(query) else "rule_slots"
            )
            if retrieval_query != query:
                return retrieval_query, doc_method, True

    return query, "passthrough", False


__all__ = [
    "RewriteMethod",
    "build_retrieval_query",
]
