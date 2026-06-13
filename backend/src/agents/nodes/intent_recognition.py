"""intent_recognition node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.intent import intent_system_prompt
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ._helpers import (
    call_intent_json,
    intent_display_name,
    normalize_candidate_intents,
    normalize_confidence,
    normalize_intent_id,
    normalize_string_list,
    run_node_with_trace,
)


async def intent_recognition(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Recognize user intent via LLM JSON output."""
    _ = (rag,)
    normalized_query = str(state.get("normalized_query", state.get("user_query", ""))).strip()
    context_pack = state.get("context_pack") or {}
    history_summary = str(state.get("history_summary", ""))

    input_data = {
        "normalized_query": normalized_query,
        "context_pack": context_pack,
        "history_summary": history_summary,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        parsed = await call_intent_json(
            llm,
            system_prompt=intent_system_prompt(time_ctx),
            user_payload=input_data,
        )
        intent_id = normalize_intent_id(parsed.get("intent_id"))
        intent_confidence = normalize_confidence(parsed.get("intent_confidence"))
        candidate_intents = normalize_candidate_intents(parsed.get("candidate_intents"))
        if not candidate_intents:
            candidate_intents = [{"intent_id": intent_id, "confidence": intent_confidence}]
        missing_slots = normalize_string_list(parsed.get("missing_slots"))
        intent_name = str(parsed.get("intent_name", "")).strip() or intent_display_name(intent_id)
        output = {
            "intent_id": intent_id,
            "intent_name": intent_name,
            "intent_confidence": intent_confidence,
            "candidate_intents": candidate_intents,
            "missing_slots": missing_slots,
        }
        return output, f"识别意图为 {intent_name}"

    return await run_node_with_trace(
        state,
        node="intent_recognition",
        input_data=input_data,
        summary="完成意图识别",
        fn=_execute,
    )
