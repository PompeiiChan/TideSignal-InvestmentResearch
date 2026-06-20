"""Dynamic stock-analysis tool orchestration with whitelist and rule fallback."""

from __future__ import annotations

import re

STOCK_TOOL_WHITELIST: frozenset[str] = frozenset(
    {
        "mock_financial_profile_lookup",
        "valuation_profile_lookup",
        "consensus_valuation_lookup",
        "research_report_metadata_lookup",
        "stock_evidence_api_lookup",
        "earnings_forecast_lookup",
    }
)

_DEFAULT_STOCK_TOOLS: list[str] = ["mock_financial_profile_lookup"]

_SCENARIO_RETURN_RE = re.compile(
    r"预期回报|预期收益|回报率|收益率|能赚多少|赚多少|现在买.*回报|买入.*回报|情景测算|收益测算",
    re.IGNORECASE,
)

_VALUATION_KEYWORD_RE = re.compile(
    r"估值|市盈|市净|PE|PB|PS|PEG|市值|贵不贵|能不能拿|值不值得|支撑|透支|分位|目标价|涨跌后",
    re.IGNORECASE,
)

_FINANCIAL_ONLY_KEYWORD_RE = re.compile(
    r"财报|业绩|营收|利润|毛利率|ROE|现金流|负债|存货|应收|季报|年报|中报",
    re.IGNORECASE,
)

_QUALITATIVE_BUSINESS_RE = re.compile(
    r"管线|在研|新药|创新药|仿制药|原研|适应症|临床|化合物|产品布局|业务结构|"
    r"主营业务|研发进展|研发投入|研发管线|商业化|上市申请|专利|产能布局|"
    r"产品矩阵|核心产品|在销品种|药品注册|生物药|化药",
    re.IGNORECASE,
)

_FINANCIAL_EXPLICIT_RE = re.compile(
    r"财报|业绩|营收|收入|利润|净利|毛利率|ROE|现金流|负债|估值|市盈|市净|PE|PB|"
    r"同比|环比|多期|财务数据|盈利能力",
    re.IGNORECASE,
)

_INSTITUTION_VIEW_RE = re.compile(
    r"机构怎么看|机构观点|一致预期|研报评级|卖方怎么看|分析师怎么看|目标价",
    re.IGNORECASE,
)

_FINANCIAL_TOOL_NAMES = frozenset(
    {
        "mock_financial_profile_lookup",
        "valuation_profile_lookup",
        "consensus_valuation_lookup",
        "earnings_forecast_lookup",
    }
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


def is_qualitative_business_query(
    *,
    query: str,
    analysis_dimensions: list[str] | None = None,
) -> bool:
    haystack = " ".join([query, *(analysis_dimensions or [])])
    return bool(_QUALITATIVE_BUSINESS_RE.search(haystack))


def build_stock_narrative_rag_queries(*, query: str, stock_name: str = "") -> list[str]:
    """Focused research-report / annual-report retrieval for pipeline and business-structure questions."""
    subject = stock_name.strip() or query.strip()
    queries: list[str] = []
    if "管线" in query or "创新药" in query or "在研" in query:
        queries.extend(
            [
                f"{subject} 研发管线 创新药 深度研究 公司研报",
                f"{subject} 创新药 管线 临床阶段 品种",
                f"{subject} 医药行业研报 创新药 管线",
            ]
        )
    queries.extend(
        [
            f"{subject} 公司研报 产品 竞争力",
            f"{subject} 行业研报 业务结构",
            f"{subject} 年报 研发 主要产品",
            f"{subject} 年度报告 经营情况讨论与分析",
        ]
    )
    return _dedupe([item for item in queries if item.strip()])[:6]


def narrative_prefers_research_reports(
    *,
    query: str,
    analysis_dimensions: list[str] | None = None,
) -> bool:
    """Pipeline / R&D / product-layout questions should prioritize research reports over API announcements."""
    return is_qualitative_business_query(query=query, analysis_dimensions=analysis_dimensions)


def needs_financial_tools(*, query: str, analysis_dimensions: list[str] | None = None) -> bool:
    haystack = " ".join([query, *(analysis_dimensions or [])])
    if is_qualitative_business_query(query=query, analysis_dimensions=analysis_dimensions) and not _FINANCIAL_EXPLICIT_RE.search(haystack):
        return False
    if _VALUATION_KEYWORD_RE.search(haystack):
        return True
    # 综合基本面问题默认也需要估值支撑。
    return not (_FINANCIAL_ONLY_KEYWORD_RE.search(haystack) and not _VALUATION_KEYWORD_RE.search(haystack))


def needs_valuation_tools(*, query: str, analysis_dimensions: list[str] | None = None) -> bool:
    if not needs_financial_tools(query=query, analysis_dimensions=analysis_dimensions):
        return False
    haystack = " ".join([query, *(analysis_dimensions or [])])
    if _VALUATION_KEYWORD_RE.search(haystack):
        return True
    return not (_FINANCIAL_ONLY_KEYWORD_RE.search(haystack) and not _VALUATION_KEYWORD_RE.search(haystack))


def needs_institution_tools(*, query: str, analysis_dimensions: list[str] | None = None) -> bool:
    haystack = " ".join([query, *(analysis_dimensions or [])])
    return bool(_INSTITUTION_VIEW_RE.search(haystack))


def resolve_stock_tool_names(
    requested: list[str] | None,
    *,
    query: str,
    analysis_dimensions: list[str] | None = None,
    scenario_return_mode: bool = False,
) -> list[str]:
    """Validate agent-requested tools and apply deterministic fallback."""
    if scenario_return_mode or _SCENARIO_RETURN_RE.search(query):
        return _dedupe(
            [
                "valuation_profile_lookup",
                "consensus_valuation_lookup",
            ]
        )

    if needs_institution_tools(query=query, analysis_dimensions=analysis_dimensions):
        return _dedupe(
            [
                "mock_financial_profile_lookup",
                "consensus_valuation_lookup",
                "research_report_metadata_lookup",
            ]
        )

    narrative_mode = is_qualitative_business_query(
        query=query,
        analysis_dimensions=analysis_dimensions,
    ) and not needs_financial_tools(query=query, analysis_dimensions=analysis_dimensions)

    valid = _dedupe(_filter_whitelisted(requested))
    agent_specified = bool(valid)

    if narrative_mode:
        narrative_tools = [name for name in valid if name not in _FINANCIAL_TOOL_NAMES]
        return _dedupe(narrative_tools)

    if not valid:
        valid = list(_DEFAULT_STOCK_TOOLS)
        if needs_valuation_tools(query=query, analysis_dimensions=analysis_dimensions):
            valid.append("valuation_profile_lookup")
        return _dedupe(valid)

    if "mock_financial_profile_lookup" not in valid:
        valid.insert(0, "mock_financial_profile_lookup")

    if agent_specified:
        return _dedupe(valid)

    if needs_valuation_tools(query=query, analysis_dimensions=analysis_dimensions) and "valuation_profile_lookup" not in valid:
        valid.append("valuation_profile_lookup")

    return _dedupe(valid)
