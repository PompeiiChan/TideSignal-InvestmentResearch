"""quality_check node."""

from __future__ import annotations

from typing import Any, Literal, cast

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.models import AnswerResult, LLMCallMeta
from ...integrations.llm.service import LLMService
from ...services.rag.models import RagHit
from ...services.rag.service import RagService
from ...settings import AppSettings
from ._helpers import run_node_with_trace


def _map_quality_status(
    overall: str,
    *,
    risk_level: str,
    tool_status: str,
    low_confidence_flag: bool,
    blacklist: list[str],
) -> Literal["pass", "revise", "reject"]:
    if overall == "REVISE":
        return "revise"
    if overall == "FAIL":
        if blacklist or risk_level == "high":
            return "reject"
        return "revise"
    if tool_status == "failed" and low_confidence_flag:
        return "reject"
    return "pass"


def _draft_answer(state: AgentState) -> AnswerResult:
    evidence_pack = state.get("evidence_pack") or {}
    agent_summary = str(evidence_pack.get("agent_summary", state.get("agent_result", ""))).strip()
    response_kind = str(state.get("response_kind", "data"))
    if response_kind not in {"stock", "data", "hotspot", "calculator"}:
        response_kind = "data"
    content = agent_summary or "基于当前证据整理回答。"
    return AnswerResult(
        content=content,
        response_kind=cast(Any, response_kind),
        rich_blocks=[],
        meta=LLMCallMeta(
            model="draft",
            latency_ms=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            finish_reason="draft",
            raw_json={"draft": True},
        ),
    )


def _rag_hits_from_state(state: AgentState) -> list[RagHit]:
    hits: list[RagHit] = []
    for item in state.get("rag_hits") or []:
        if isinstance(item, dict):
            try:
                hits.append(RagHit.model_validate(item))
            except Exception:
                continue
    return hits


async def quality_check(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Run LLM quality check and map to pass/revise/reject."""
    _ = (rag, settings)
    normalized_query = str(state.get("normalized_query", "")).strip()
    evidence_pack = state.get("evidence_pack") or {}
    tool_status = str(state.get("tool_status", "skipped"))
    low_confidence_flag = bool(state.get("low_confidence_flag", False))

    input_data = {
        "query": normalized_query,
        "evidence_summary": str(evidence_pack.get("agent_summary", ""))[:200],
        "tool_status": tool_status,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        draft = _draft_answer(state)
        rag_hits = _rag_hits_from_state(state)
        result = await llm.quality_check(normalized_query, draft, rag_hits=rag_hits)
        overall = str(result.overall_result).upper()
        risk_level = "high" if result.blacklist_expressions_found else "low"
        quality_status = _map_quality_status(
            overall,
            risk_level=risk_level,
            tool_status=tool_status,
            low_confidence_flag=low_confidence_flag,
            blacklist=result.blacklist_expressions_found,
        )
        revision_suggestions: list[str] = list(result.revision_suggestions)
        if quality_status == "revise" and not revision_suggestions:
            revision_suggestions.append("请补充引用来源或弱化不确定表述")
        quality_payload = {
            "overall_result": result.overall_result,
            "compliance_scan": result.compliance_scan,
            "citation_check": result.citation_check,
            "data_consistency": result.data_consistency,
            "format_check": result.format_check,
            "writing_quality": result.writing_quality,
            "risk_tip_present": result.risk_tip_present,
            "blacklist_expressions_found": result.blacklist_expressions_found,
            "quality_status": quality_status,
        }
        output = {
            "quality_status": quality_status,
            "quality_score": 1.0 if quality_status == "pass" else 0.5 if quality_status == "revise" else 0.0,
            "risk_level": risk_level,
            "revision_suggestions": revision_suggestions,
            "quality_check_payload": quality_payload,
        }
        summary = f"质检结果：{quality_status}"
        return output, summary

    return await run_node_with_trace(
        state,
        node="quality_check",
        input_data=input_data,
        summary="完成质检合规",
        fn=_execute,
    )
