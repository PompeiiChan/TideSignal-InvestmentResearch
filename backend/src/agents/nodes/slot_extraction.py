"""slot_extraction node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.slots import slots_system_prompt
from ...integrations.llm.service import LLMService
from ...services.conversation_context import build_conversation_context
from ...services.rag.chunker import resolve_kb_root
from ...services.rag.company_index import enrich_stock_slots_from_kb
from ...services.rag.service import RagService
from ...services.scenario_return import enrich_scenario_return_slots
from ...services.slot_memory import filter_missing_after_inherit, merge_pending_slots
from ...services.system_time import resolve_system_time
from ...services.trading_calendar import enrich_trading_slots
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
    _ = rag
    normalized_query = str(state.get("normalized_query", "")).strip()
    intent_id = str(state.get("intent_id", "unknown"))
    context_pack = state.get("context_pack") or {}
    history_summary = str(state.get("history_summary", "")).strip()
    pending_slots = normalize_slots(state.get("pending_slots"))
    pending_intent_id = str(state.get("pending_intent_id", "")).strip() or None
    prior_missing = normalize_string_list(state.get("missing_slots"))

    input_data = {
        "normalized_query": normalized_query,
        "intent_id": intent_id,
        "context_pack": context_pack,
        "history_summary": history_summary,
        "pending_slots": pending_slots,
        "pending_intent_id": pending_intent_id or "",
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        parsed = await call_intent_json(
            llm,
            system_prompt=slots_system_prompt(time_ctx),
            user_payload=input_data,
        )
        extracted_slots = normalize_slots(parsed.get("slots"))
        merged_slots, inherited_keys, overridden_keys = merge_pending_slots(
            intent_id=intent_id,
            pending_slots=pending_slots,
            extracted_slots=extracted_slots,
            pending_intent_id=pending_intent_id,
        )
        if intent_id == "stock_analysis":
            kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)
            merged_slots = enrich_stock_slots_from_kb(normalized_query, merged_slots, kb_root)
        merged_slots = enrich_trading_slots(
            normalized_query,
            merged_slots,
            last_trading_day=time_ctx.last_trading_day,
            is_trading_day=time_ctx.is_trading_day,
        )
        merged_slots = enrich_scenario_return_slots(normalized_query, merged_slots)
        slot_confidence = normalize_slot_confidence(parsed.get("slot_confidence"))
        missing_slots = normalize_string_list(parsed.get("missing_slots"))
        ambiguous_slots = normalize_string_list(parsed.get("ambiguous_slots"))

        missing_slots = filter_missing_after_inherit(
            missing_slots,
            merged_slots,
            inherited_keys,
        )

        if not missing_slots and prior_missing:
            remaining = [name for name in prior_missing if name not in merged_slots]
            missing_slots = remaining

        conversation_context = build_conversation_context(
            history_summary=history_summary,
            active_slots=merged_slots,
            inherited_slot_keys=inherited_keys,
            normalized_query=normalized_query,
        )
        output = {
            "extracted_slots": extracted_slots,
            "pending_slots": pending_slots,
            "slots": merged_slots,
            "active_slots": merged_slots,
            "slot_confidence": slot_confidence,
            "missing_slots": missing_slots,
            "ambiguous_slots": ambiguous_slots,
            "inherited_slot_keys": inherited_keys,
            "overridden_slot_keys": overridden_keys,
            "conversation_context": conversation_context,
            "conversation_context_preview": {
                "has_context": conversation_context.get("has_context", False),
                "active_slot_keys": sorted(merged_slots.keys()),
                "inherited_slot_keys": inherited_keys,
            },
        }
        return output, "完成槽位抽取"

    return await run_node_with_trace(
        state,
        node="slot_extraction",
        input_data=input_data,
        summary="完成槽位抽取",
        fn=_execute,
    )
