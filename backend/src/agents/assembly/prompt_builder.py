"""Deduplicated user prompt builder for response_assembly."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ...services.citation_catalog import CitationCatalog
from ...services.conversation_context import format_conversation_context_for_prompt
from ...services.system_time import SystemTimeContext
from ..heatmap_intent import wants_sector_heatmap


@dataclass(frozen=True)
class AssemblyPromptParts:
    user_prompt: str
    citation_context: str
    prompt_stats: dict[str, int]


def _compact_analysis_dimensions(evidence_pack: dict[str, Any]) -> str:
    dims = evidence_pack.get("analysis_dimensions")
    if not isinstance(dims, list) or not dims:
        return ""
    trimmed = [str(item).strip() for item in dims[:8] if str(item).strip()]
    if not trimmed:
        return ""
    return json.dumps(trimmed, ensure_ascii=False)


def _meta_flags_json(evidence_pack: dict[str, Any]) -> str:
    flags: dict[str, Any] = {}
    for key in (
        "stock_narrative_evidence_missing",
        "stock_kb_uncovered",
        "scenario_return_mode",
        "hotspot_evidence_mode",
        "stock_narrative_mode",
    ):
        if key in evidence_pack:
            flags[key] = evidence_pack.get(key)
    if not flags:
        return ""
    return json.dumps(flags, ensure_ascii=False)


def _heatmap_tool_has_tiles(tool_result: dict[str, Any]) -> bool:
    heatmap_tool = tool_result.get("sector_heatmap_lookup")
    return isinstance(heatmap_tool, dict) and bool(heatmap_tool.get("tiles"))


def build_assembly_user_prompt(
    *,
    normalized_query: str,
    evidence_pack: dict[str, Any],
    citation_context: str,
    catalog: CitationCatalog,
    conversation_context: dict[str, Any],
    revision_suggestions: list[str],
    time_ctx: SystemTimeContext,
) -> AssemblyPromptParts:
    """Build deduplicated assembly user prompt (citation context is the sole data source)."""
    _ = catalog
    _ = time_ctx
    tool_result = evidence_pack.get("tool_result") if isinstance(evidence_pack.get("tool_result"), dict) else {}
    agent_summary = str(evidence_pack.get("agent_summary") or evidence_pack.get("agent_result") or "").strip()

    parts: list[str] = [f"用户问题：{normalized_query}", ""]
    if agent_summary:
        parts.extend(["【分析骨架】", agent_summary, ""])

    dims_json = _compact_analysis_dimensions(evidence_pack)
    if dims_json:
        parts.extend(["【分析维度】", dims_json, ""])

    if citation_context.strip():
        parts.extend(["【结构化引用与证据】（唯一数据源）", citation_context.strip(), ""])

    flags_json = _meta_flags_json(evidence_pack)
    if flags_json:
        parts.extend(["【元信息 flags】", flags_json, ""])

    if conversation_context.get("has_context"):
        context_block = format_conversation_context_for_prompt(conversation_context)
        parts.extend(
            [
                "【多轮对话上下文】",
                context_block,
                "须延续上述标的与时间口径作答，不得要求用户重复提供公司名称。",
                "",
            ]
        )

    if revision_suggestions:
        parts.append(f"质检修订建议：{'; '.join(revision_suggestions)}")
        parts.append("")

    if evidence_pack.get("stock_narrative_evidence_missing") or evidence_pack.get("stock_kb_uncovered"):
        parts.extend(
            [
                "【强制约束】本地未收录该公司券商深度研报或本轮未命中 company-reports/industry-reports 片段。"
                "不得编造具体药品、靶点或管线品种名称；须先声明证据不足。",
                "",
            ]
        )

    heatmap_primary = wants_sector_heatmap(normalized_query) and _heatmap_tool_has_tiles(tool_result)
    if heatmap_primary:
        parts.extend(
            [
                "【热力图优先】用户核心是查看行业板块热力图交互组件。正文控制在 3～6 行："
                "说明统计口径（交易日）并点出 1～2 个成交或涨跌突出的板块即可；"
                "勿逐块复述热力图全部数据，热力图由前端组件展示。",
                "",
            ]
        )

    parts.append("请直接输出 Markdown 正文。")
    user_prompt = "\n".join(parts)

    prompt_stats = {
        "user_chars": len(user_prompt),
        "citation_context_chars": len(citation_context),
    }
    return AssemblyPromptParts(
        user_prompt=user_prompt,
        citation_context=citation_context,
        prompt_stats=prompt_stats,
    )
