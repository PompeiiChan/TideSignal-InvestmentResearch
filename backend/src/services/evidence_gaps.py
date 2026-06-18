"""Evidence gap detection and enrichment planning for stock analysis loop."""

from __future__ import annotations

from typing import Any

from ..agents.stock_tool_plan import (
    STOCK_TOOL_WHITELIST,
    build_stock_narrative_rag_queries,
    is_qualitative_business_query,
    resolve_stock_tool_names,
)

MAX_EVIDENCE_ENRICHMENT_PASSES = 1

_API_SUPPLEMENT_GAP_IDS = frozenset(
    {
        "company_rag_missing",
        "risk_signal_unexplained",
        "profitability_stress",
    }
)

_RISK_KEYWORDS = ("应收", "现金流", "负债", "承压", "下滑", "竞争", "存货", "毛利率下降")


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _rag_text(hits: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        parts.extend(
            [
                str(hit.get("title", "")),
                str(hit.get("path", "")),
                str(hit.get("snippet", "")),
            ]
        )
    return " ".join(parts)


def _company_rag_hits(rag_hits: list[dict[str, Any]], stock_name: str) -> list[dict[str, Any]]:
    if not stock_name.strip():
        return []
    needle = stock_name.strip()
    matched: list[dict[str, Any]] = []
    for hit in rag_hits:
        if not isinstance(hit, dict):
            continue
        haystack = _rag_text([hit])
        if needle in haystack:
            matched.append(hit)
    return matched


def _rag_covers_keywords(rag_hits: list[dict[str, Any]], keywords: tuple[str, ...]) -> bool:
    haystack = _rag_text(rag_hits)
    return any(keyword in haystack for keyword in keywords)


def detect_stock_evidence_gaps(
    *,
    tool_result: dict[str, Any],
    rag_hits: list[dict[str, Any]],
    analysis_dimensions: list[str] | None,
    stock_name: str,
    query: str = "",
) -> list[dict[str, Any]]:
    """Return structured evidence gaps that warrant a targeted supplement fetch."""
    gaps: list[dict[str, Any]] = []
    if is_qualitative_business_query(query=query, analysis_dimensions=analysis_dimensions):
        if stock_name and not _company_rag_hits(rag_hits, stock_name):
            gaps.append(
                {
                    "gap_id": "company_rag_missing",
                    "topic": f"{stock_name} 公司研报与年报",
                    "reason": "本地知识库未命中该公司研报/年报，需定向检索 company-reports / industry-reports。",
                }
            )
        return gaps

    dimensions = [str(item).strip() for item in (analysis_dimensions or []) if str(item).strip()]
    fin_payload = tool_result.get("mock_financial_profile_lookup")
    fin_payload = fin_payload if isinstance(fin_payload, dict) else {}
    profile = fin_payload.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    periods_raw = fin_payload.get("periods")
    periods = [item for item in periods_raw if isinstance(item, dict)] if isinstance(periods_raw, list) else []

    if stock_name and not _company_rag_hits(rag_hits, stock_name):
        gaps.append(
            {
                "gap_id": "company_rag_missing",
                "topic": f"{stock_name} 公告与研报",
                "reason": "本地知识库未命中该公司专属文档，难以解释经营细节。",
            }
        )

    if fin_payload.get("found") is True and len(periods) < 2 and any(
        token in "".join(dimensions) for token in ("基本面", "盈利", "财报", "业绩", "现金流")
    ):
        gaps.append(
            {
                "gap_id": "multi_period_thin",
                "topic": f"{stock_name or '标的'} 多期财务趋势",
                "reason": "结构化财报仅覆盖单期，缺少多期对比材料。",
            }
        )

    net_profit = str(profile.get("net_profit", "")).strip()
    if net_profit.startswith("-") or "亏损" in net_profit:
        gaps.append(
            {
                "gap_id": "profitability_stress",
                "topic": f"{stock_name or '标的'} 亏损与盈利质量",
                "reason": "利润端承压，需要补充成因与修复线索。",
            }
        )

    highlights = profile.get("highlights") or []
    highlight_text = " ".join(str(item) for item in highlights)
    if any(keyword in highlight_text for keyword in _RISK_KEYWORDS) and not _rag_covers_keywords(
        rag_hits, _RISK_KEYWORDS
    ):
        gaps.append(
            {
                "gap_id": "risk_signal_unexplained",
                "topic": f"{stock_name or '标的'} 经营风险与现金流",
                "reason": "财报摘要出现风险信号，但缺少公告/研报解释材料。",
            }
        )

    if any("估值" in dimension for dimension in dimensions) and "valuation_profile_lookup" not in tool_result:
        gaps.append(
            {
                "gap_id": "valuation_missing",
                "topic": f"{stock_name or '标的'} 估值画像",
                "reason": "分析维度包含估值，但首轮未获取实时估值工具结果。",
            }
        )

    return gaps


def build_gap_enrichment_plan(
    gaps: list[dict[str, Any]],
    *,
    stock_name: str,
    stock_code: str = "",
    analysis_dimensions: list[str] | None,
    existing_tool_result: dict[str, Any],
    existing_rag_hits: list[dict[str, Any]],
    query: str = "",
) -> dict[str, Any]:
    """Turn detected gaps into targeted RAG queries and optional tool calls."""
    narrative_mode = is_qualitative_business_query(
        query=query or stock_name,
        analysis_dimensions=analysis_dimensions,
    )
    rag_queries: list[str] = []
    tool_names: list[str] = []
    company_id = ""
    industry = ""
    fin_payload = existing_tool_result.get("mock_financial_profile_lookup")
    if isinstance(fin_payload, dict):
        profile = fin_payload.get("profile")
        if isinstance(profile, dict):
            company_id = str(profile.get("company_id", "")).strip()
            industry = str(profile.get("industry", "")).strip()

    for gap in gaps:
        gap_id = str(gap.get("gap_id", "")).strip()
        topic = str(gap.get("topic", "")).strip()
        if gap_id in {"company_rag_missing", "multi_period_thin"}:
            if narrative_mode:
                rag_queries.extend(
                    build_stock_narrative_rag_queries(
                        query=query or stock_name,
                        stock_name=stock_name,
                    )
                )
            else:
                # Avoid generic financial terms like「年报/营收/净利润」— they match unrelated
                # industry reports when the company has no dedicated KB document.
                rag_queries.extend(
                    [
                        f"{stock_name} 主营业务 产品 竞争力",
                        f"{stock_name} {industry} 行业地位 盈利模式" if industry else f"{stock_name} 行业地位 盈利模式",
                    ]
                )
        elif gap_id == "profitability_stress":
            rag_queries.extend(
                [
                    f"{stock_name} 净利润 亏损 原因",
                    f"{stock_name} 盈利能力 现金流",
                ]
            )
        elif gap_id == "risk_signal_unexplained":
            rag_queries.append(topic or f"{stock_name} 经营现金流 应收 负债")
        elif gap_id == "valuation_missing":
            tool_names.append("valuation_profile_lookup")

    gap_ids = {str(gap.get("gap_id", "")).strip() for gap in gaps}
    if gap_ids & _API_SUPPLEMENT_GAP_IDS and not narrative_mode:
        tool_names.append("stock_evidence_api_lookup")

    rag_queries = _dedupe_strings(rag_queries)[:6 if narrative_mode else 4]
    requested_tools = _dedupe_strings(
        [name for name in tool_names if name in STOCK_TOOL_WHITELIST and name not in existing_tool_result]
    )
    resolved_tools = resolve_stock_tool_names(
        requested_tools,
        query=query or stock_name,
        analysis_dimensions=analysis_dimensions,
    )
    if narrative_mode:
        resolved_tools = [
            name
            for name in resolved_tools
            if name not in {
                "mock_financial_profile_lookup",
                "valuation_profile_lookup",
                "consensus_valuation_lookup",
                "earnings_forecast_lookup",
            }
        ]
    resolved_tools = [name for name in resolved_tools if name not in existing_tool_result]

    rag_filters: dict[str, str] = {}
    if company_id:
        rag_filters["company_id"] = company_id

    return {
        "gap_ids": [str(gap.get("gap_id", "")) for gap in gaps],
        "rag_queries": rag_queries,
        "rag_filters": rag_filters,
        "tool_names": resolved_tools,
        "tool_params": {
            "stock_name": stock_name,
            "stock_code": stock_code,
        },
        "summary": "；".join(str(gap.get("reason", "")).strip() for gap in gaps if gap.get("reason"))[:500],
        "existing_rag_hit_count": len(existing_rag_hits),
    }


def merge_rag_hits(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge RAG hits by chunk_id, keeping the higher score."""
    merged: dict[str, dict[str, Any]] = {}
    for hit in [*existing, *incoming]:
        if not isinstance(hit, dict):
            continue
        chunk_id = str(hit.get("chunk_id", "")).strip() or str(hit.get("doc_id", "")).strip()
        if not chunk_id:
            continue
        current = merged.get(chunk_id)
        if current is None or float(hit.get("score", 0) or 0) > float(current.get("score", 0) or 0):
            merged[chunk_id] = hit
    return sorted(merged.values(), key=lambda item: float(item.get("score", 0) or 0), reverse=True)


def merge_tool_results(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Shallow-merge tool payloads while appending tool execution traces."""
    if not existing:
        return dict(incoming)
    if not incoming:
        return dict(existing)

    merged = dict(existing)
    existing_tools = list(merged.get("tools") or [])
    incoming_tools = list(incoming.get("tools") or [])
    if incoming_tools:
        merged["tools"] = [*existing_tools, *incoming_tools]

    for key, value in incoming.items():
        if key == "tools":
            continue
        if key not in merged or merged.get(key) in (None, {}, []):
            merged[key] = value
    return merged
