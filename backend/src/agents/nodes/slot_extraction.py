"""slot_extraction node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...services.rag.chunker import resolve_kb_root
from ...services.rag.company_index import enrich_stock_slots_from_kb
from ...integrations.llm.prompts.slots import slots_system_prompt
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import BACKEND_ROOT, AppSettings
from ._helpers import (
    call_intent_json,
    normalize_slot_confidence,
    normalize_slots,
    normalize_string_list,
    run_node_with_trace,
)


async def slot_extraction(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Extract structured slots from the user query."""
    _ = (rag,)
    normalized_query = str(state.get("normalized_query", "")).strip()
    intent_id = str(state.get("intent_id", "unknown"))
    context_pack = state.get("context_pack") or {}
    prior_missing = normalize_string_list(state.get("missing_slots"))

    input_data = {
        "normalized_query": normalized_query,
        "intent_id": intent_id,
        "context_pack": context_pack,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        parsed = await call_intent_json(
            llm,
            system_prompt=slots_system_prompt(time_ctx),
            user_payload=input_data,
        )
        slots = normalize_slots(parsed.get("slots"))
        if intent_id == "stock_analysis":
            kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)
            slots = enrich_stock_slots_from_kb(normalized_query, slots, kb_root)
        slot_confidence = normalize_slot_confidence(parsed.get("slot_confidence"))
        missing_slots = normalize_string_list(parsed.get("missing_slots"))
        ambiguous_slots = normalize_string_list(parsed.get("ambiguous_slots"))

        if not missing_slots and prior_missing:
            remaining = [name for name in prior_missing if name not in slots]
            missing_slots = remaining

        output = {
            "slots": slots,
            "slot_confidence": slot_confidence,
            "missing_slots": missing_slots,
            "ambiguous_slots": ambiguous_slots,
        }
        return output, "完成槽位抽取"

    return await run_node_with_trace(
        state,
        node="slot_extraction",
        input_data=input_data,
        summary="完成槽位抽取",
        fn=_execute,
    )
