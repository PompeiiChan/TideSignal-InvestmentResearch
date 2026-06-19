"""Rule-based retrieval query builder for query_rewrite (T-014 Phase ① / P2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

RewriteMethod = Literal[
    "passthrough",
    "rule_slots",
    "rule_multiturn",
    "rule_dimension_split",
]

MAX_DIMENSION_QUERIES = 4

_FINANCIAL_KEYWORDS = re.compile(
    r"年报|季报|财报|一季报|二季报|三季报|四季报|半年报|中报|业绩|营收|净利润|利润"
)
_ANALYSIS_DIMENSION_KEYWORDS = re.compile(
    r"基本面|估值|风险|盈利能力|现金流|负债|毛利率|ROE|竞争力|业务结构|财报|年报|季报|一季报"
)
_FINANCIAL_PERIOD_KEYWORDS = re.compile(r"年报|季报|一季报|半年报|业绩|营收|利润|财报")
_YEAR_PATTERN = re.compile(r"20\d{2}")
_DEICTIC_PATTERN = re.compile(r"(呢|怎么样|如何|怎样|咋样|它|这个|那个|这家|该股|该公司)")

_QUARTER_LABELS = {
    "1": "一季报",
    "2": "二季报",
    "3": "三季报",
    "4": "四季报",
}


@dataclass(frozen=True)
class RetrievalQueryPlan:
    retrieval_query: str
    retrieval_queries: list[str]
    rewrite_method: RewriteMethod
    changed: bool


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


def _query_has_stock_and_dimension(query: str, stock_name: str) -> bool:
    """公司名 + 分析维度 → 显性问句，应 passthrough 主 query。"""
    if not stock_name or stock_name not in query:
        return False
    return bool(_ANALYSIS_DIMENSION_KEYWORDS.search(query))


def _needs_follow_up_rewrite(query: str, stock_name: str) -> bool:
    """仅续问/指代/缺公司名时 True；显性完整问句 False。"""
    if _query_has_stock_and_dimension(query, stock_name):
        return False
    if stock_name and stock_name in query:
        return _is_short_or_deictic_query(query)
    return _is_short_or_deictic_query(query) or bool(stock_name)


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


def _detect_dimension(query: str, analysis_dimension: str) -> str:
    if analysis_dimension:
        return analysis_dimension
    for keyword in ("基本面", "估值", "风险", "盈利能力", "现金流", "负债", "竞争力"):
        if keyword in query:
            return keyword
    return ""


def _should_append_financial_keyword(
    query: str,
    *,
    formatted_range: str,
    period_hint: str,
    time_range: str,
) -> bool:
    if formatted_range or period_hint:
        return True
    if time_range.strip():
        return True
    return bool(_FINANCIAL_PERIOD_KEYWORDS.search(query))


def build_dimension_retrieval_queries(
    *,
    stock_name: str,
    dimension: str,
    time_range: str = "",
    normalized_query: str = "",
) -> list[str]:
    """按维度映射 2～4 条子 query，上限 MAX_DIMENSION_QUERIES=4。"""
    name = stock_name.strip()
    if not name:
        return []

    dim = dimension.strip()
    query = normalized_query.strip()
    period = _format_time_range(time_range) or _period_hint_from_query(query)
    queries: list[str] = []

    if period or re.search(r"Q[1-4]", time_range, re.IGNORECASE):
        queries.append(f"{name} {period} 财务".strip())
        if len(queries) < MAX_DIMENSION_QUERIES:
            queries.append(f"{name} {period} 公告".strip())
    elif "估值" in dim or "估值" in query:
        queries = [
            f"{name} 估值 PE PB 历史分位",
            f"{name} 市值 盈利预测",
        ]
    elif "风险" in dim or "风险" in query:
        queries = [f"{name} 风险 负债 现金流 年报"]
    else:
        queries = [
            f"{name} 财务 营收 利润 现金流 年报",
            f"{name} 盈利能力 ROE 毛利率",
            f"{name} 公司研报 竞争力 行业",
        ]

    return [item for item in queries if item][:MAX_DIMENSION_QUERIES]


def _build_stock_retrieval_query(
    query: str,
    *,
    stock_name: str,
    time_range: str,
    analysis_dimension: str,
) -> tuple[str, RewriteMethod]:
    parts: list[str] = [stock_name]
    formatted_range = _format_time_range(time_range)
    period_hint = ""
    if formatted_range:
        parts.append(formatted_range)
    else:
        period_hint = _period_hint_from_query(query)
        if period_hint:
            parts.append(period_hint)
    if analysis_dimension and analysis_dimension not in parts:
        parts.append(analysis_dimension)
    if _should_append_financial_keyword(
        query,
        formatted_range=formatted_range,
        period_hint=period_hint,
        time_range=time_range,
    ) and "财报" not in " ".join(parts):
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
) -> RetrievalQueryPlan:
    """Return retrieval query plan for RAG."""
    _ = conversation_context
    query = normalized_query.strip()
    if not query:
        return RetrievalQueryPlan(query, [], "passthrough", False)

    stock_name = _slot_text(slots, "stock_name")
    time_range = _slot_text(slots, "time_range")
    topic = _slot_text(slots, "topic")
    industry = _slot_text(slots, "industry")
    document_id = _slot_text(slots, "document_id")
    analysis_dimension = _slot_text(slots, "analysis_dimension")

    if _query_already_rich(query, stock_name):
        return RetrievalQueryPlan(query, [], "passthrough", False)

    if intent_id in {"stock_analysis", "document_qa"} and stock_name:
        if _query_has_stock_and_dimension(query, stock_name):
            dimension = _detect_dimension(query, analysis_dimension) or "基本面"
            extra_queries = build_dimension_retrieval_queries(
                stock_name=stock_name,
                dimension=dimension,
                time_range=time_range,
                normalized_query=query,
            )
            method: RewriteMethod = (
                "rule_dimension_split" if len(extra_queries) >= 2 else "passthrough"
            )
            changed = len(extra_queries) >= 2
            return RetrievalQueryPlan(query, extra_queries, method, changed)

        if _needs_follow_up_rewrite(query, stock_name):
            retrieval_query, method = _build_stock_retrieval_query(
                query,
                stock_name=stock_name,
                time_range=time_range,
                analysis_dimension=analysis_dimension,
            )
            return RetrievalQueryPlan(
                retrieval_query,
                [],
                method,
                retrieval_query != query,
            )

    if intent_id == "hotspot_analysis":
        parts = [part for part in (topic, industry, _format_time_range(time_range)) if part]
        if parts and (_is_short_or_deictic_query(query) or not all(part in query for part in parts)):
            retrieval_query = " ".join(parts)
            if retrieval_query != query:
                return RetrievalQueryPlan(retrieval_query, [], "rule_slots", True)

    if intent_id == "document_qa":
        parts = [part for part in (stock_name, document_id, _format_time_range(time_range)) if part]
        if parts and (_is_short_or_deictic_query(query) or stock_name not in query):
            retrieval_query = " ".join([*parts, query]) if query not in parts else " ".join(parts)
            doc_method: RewriteMethod = (
                "rule_multiturn" if _is_short_or_deictic_query(query) else "rule_slots"
            )
            if retrieval_query != query:
                return RetrievalQueryPlan(retrieval_query, [], doc_method, True)

    return RetrievalQueryPlan(query, [], "passthrough", False)


__all__ = [
    "MAX_DIMENSION_QUERIES",
    "RetrievalQueryPlan",
    "RewriteMethod",
    "build_dimension_retrieval_queries",
    "build_retrieval_query",
]
