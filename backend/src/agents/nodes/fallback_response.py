"""fallback_response node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.fallback import fallback_system_prompt
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ._helpers import call_intent_json, run_node_with_trace

_PREDICTION_FALLBACK = (
    "您的问题涉及涨跌预测或目标价测算。本系统仅提供客观信息整理，"
    "不提供未来价格预测、目标价或投资收益保证。\n\n"
    "建议您改为查询：公司基本面、行业热点、历史行情排行等可验证的公开信息。"
    "以上内容仅为信息整理，不构成投资建议。"
)

_QUALITY_REJECT_FALLBACK = (
    "当前证据不足以生成合规、可靠的回答，已切换为安全说明。\n\n"
    "请补充更具体的问题描述（如标的名称、时间范围、关注指标），"
    "或换一个可验证的信息查询问题。"
)

_TOOL_FAIL_FALLBACK = (
    "相关数据工具暂时不可用，且知识库命中不足，无法给出有依据的回答。\n\n"
    "请稍后重试，或改为查询其他公开信息。"
)


def _resolve_fallback_reason(state: AgentState) -> str:
    intent_id = str(state.get("intent_id", ""))
    if intent_id == "prediction_request" or state.get("risk_hint") == "prediction_boundary":
        return "prediction_request"
    if state.get("quality_status") == "reject":
        return "quality_reject"
    if state.get("tool_status") == "failed":
        return "tool_failure"
    if intent_id in {"chit_chat", "unknown"}:
        return "out_of_scope"
    return str(state.get("fallback_reason", "general"))


def _template_response(reason: str) -> tuple[str, str]:
    if reason == "prediction_request":
        return _PREDICTION_FALLBACK, "预测类请求拦截"
    if reason == "quality_reject":
        return _QUALITY_REJECT_FALLBACK, "质检未通过"
    if reason == "tool_failure":
        return _TOOL_FAIL_FALLBACK, "工具失败兜底"
    if reason == "out_of_scope":
        return (
            "您好，我是投研信息整理助手，可帮您查询热点解读、行情数据、个股基本面或文档内容。"
            "请描述您想了解的具体问题。",
            "闲聊或未知意图",
        )
    return (
        "当前无法基于可靠证据生成回答，请补充更多信息后再试。",
        "通用兜底",
    )


async def fallback_response(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Generate safe fallback without LLM-calculated financial numbers."""
    _ = rag
    normalized_query = str(state.get("normalized_query", "")).strip()
    reason_code = _resolve_fallback_reason(state)

    input_data = {
        "normalized_query": normalized_query,
        "fallback_reason_code": reason_code,
        "intent_id": state.get("intent_id", ""),
        "quality_status": state.get("quality_status", ""),
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        if reason_code in {"prediction_request", "quality_reject", "tool_failure", "out_of_scope"}:
            final_response, fallback_reason = _template_response(reason_code)
        else:
            time_ctx = resolve_system_time(settings)
            try:
                parsed = await call_intent_json(
                    llm,
                    system_prompt=fallback_system_prompt(time_ctx),
                    user_payload=input_data,
                )
                final_response = str(parsed.get("final_response", "")).strip()
                fallback_reason = str(parsed.get("fallback_reason", reason_code)).strip()
            except Exception:
                final_response, fallback_reason = _template_response(reason_code)
            if not final_response:
                final_response, fallback_reason = _template_response(reason_code)

        output = {
            "final_response": final_response,
            "fallback_reason": fallback_reason,
            "response_kind": state.get("response_kind", "data"),
            "rich_blocks": [],
            "response_meta": {"fallback": True, "reason_code": reason_code},
        }
        return output, f"兜底回复：{fallback_reason}"

    return await run_node_with_trace(
        state,
        node="fallback_response",
        input_data=input_data,
        summary="生成兜底回复",
        fn=_execute,
    )
