"""clarification_response node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.clarification import clarification_system_prompt
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ._helpers import call_intent_json, normalize_string_list, run_node_with_trace


async def clarification_response(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Generate structured clarification follow-up via LLM."""
    _ = (rag,)
    normalized_query = str(state.get("normalized_query", "")).strip()
    clarification_reason = str(state.get("clarification_reason", ""))
    clarification_questions = normalize_string_list(state.get("clarification_questions"))
    slots = state.get("slots") or {}
    intent_id = str(state.get("intent_id", "unknown"))

    input_data = {
        "normalized_query": normalized_query,
        "clarification_reason": clarification_reason,
        "clarification_questions": clarification_questions,
        "intent_id": intent_id,
        "slots": slots,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        parsed = await call_intent_json(
            llm,
            system_prompt=clarification_system_prompt(time_ctx),
            user_payload=input_data,
        )
        final_response = str(parsed.get("final_response", "")).strip()
        next_expected_slots = normalize_string_list(parsed.get("next_expected_slots"))
        llm_questions = normalize_string_list(parsed.get("clarification_questions"))

        if not final_response:
            question_lines = llm_questions or clarification_questions
            if question_lines:
                final_response = "为更准确回答您的问题，请补充以下信息：\n\n" + "\n".join(
                    f"- {item}" for item in question_lines
                )
            else:
                final_response = "为更准确回答您的问题，请补充关键信息后再试。"

        if not next_expected_slots:
            next_expected_slots = clarification_questions

        output = {
            "final_response": final_response,
            "next_expected_slots": next_expected_slots,
            "clarification_questions": llm_questions or clarification_questions,
        }
        return output, "生成澄清追问"

    return await run_node_with_trace(
        state,
        node="clarification_response",
        input_data=input_data,
        summary="生成澄清追问",
        fn=_execute,
    )
