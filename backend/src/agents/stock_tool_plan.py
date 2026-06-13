"""Dynamic stock-analysis tool orchestration with whitelist and rule fallback."""

from __future__ import annotations

import re

STOCK_TOOL_WHITELIST: frozenset[str] = frozenset(
    {
        "mock_financial_profile_lookup",
        "valuation_profile_lookup",
    }
)

_DEFAULT_STOCK_TOOLS: list[str] = ["mock_financial_profile_lookup"]

_VALUATION_KEYWORD_RE = re.compile(
    r"估值|市盈|市净|PE|PB|PS|PEG|市值|贵不贵|能不能拿|值不值得|支撑|透支|分位|目标价|涨跌后",
    re.IGNORECASE,
)

_FINANCIAL_ONLY_KEYWORD_RE = re.compile(
    r"财报|业绩|营收|利润|毛利率|ROE|现金流|负债|存货|应收|季报|年报|中报",
    re.IGNORECASE,
)


def _dedupe(names: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _filter_whitelisted(requested: list[str] | None) -> list[str]:
    if not requested:
        return []
    return [name for name in requested if name in STOCK_TOOL_WHITELIST]


def needs_valuation_tools(*, query: str, analysis_dimensions: list[str] | None = None) -> bool:
    haystack = " ".join([query, *(analysis_dimensions or [])])
    if _VALUATION_KEYWORD_RE.search(haystack):
        return True
    if _FINANCIAL_ONLY_KEYWORD_RE.search(haystack) and not _VALUATION_KEYWORD_RE.search(haystack):
        return False
    # 综合基本面问题默认也需要估值支撑。
    return True


def resolve_stock_tool_names(
    requested: list[str] | None,
    *,
    query: str,
    analysis_dimensions: list[str] | None = None,
) -> list[str]:
    """Validate agent-requested tools and apply deterministic fallback."""
    valid = _dedupe(_filter_whitelisted(requested))
    agent_specified = bool(valid)

    if not valid:
        valid = list(_DEFAULT_STOCK_TOOLS)
        if needs_valuation_tools(query=query, analysis_dimensions=analysis_dimensions):
            valid.append("valuation_profile_lookup")
        return _dedupe(valid)

    if "mock_financial_profile_lookup" not in valid:
        valid.insert(0, "mock_financial_profile_lookup")

    # Agent 已明确规划工具时尊重其选择，不强行追加估值工具。
    if agent_specified:
        return _dedupe(valid)

    if needs_valuation_tools(query=query, analysis_dimensions=analysis_dimensions):
        if "valuation_profile_lookup" not in valid:
            valid.append("valuation_profile_lookup")

    return _dedupe(valid)
