"""query_rewrite node — rule-based retrieval_query builder (T-014 Phase ①)."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.retrieval_query import build_retrieval_query
from ...settings import AppSettings
from ._helpers import run_node_with_trace


async def query_rewrite(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Build retrieval_query from normalized_query and slots without LLM."""
    _ = (llm, rag, settings)
    normalized_query = str(state.get("normalized_query", state.get("user_query", ""))).strip()
    slots = state.get("active_slots") or state.get("slots") or {}
    if not isinstance(slots, dict):
        slots = {}
    active_slots = state.get("active_slots") or {}
    if not isinstance(active_slots, dict):
        active_slots = {}

    input_data = {
        "normalized_query": normalized_query,
        "intent_id": state.get("intent_id", ""),
        "slots": slots,
        "active_slots": active_slots,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        plan = build_retrieval_query(
            normalized_query,
            intent_id=str(state.get("intent_id", "")),
            slots=slots,
            conversation_context=state.get("conversation_context"),
        )
        output = {
            "retrieval_query": plan.retrieval_query,
            "retrieval_queries": plan.retrieval_queries,
            "rewrite_method": plan.rewrite_method,
            "retrieval_query_changed": plan.changed,
        }
        if plan.changed:
            if len(plan.retrieval_queries) >= 2:
                summary = (
                    f"检索问句保持原样，按维度拆分为 {len(plan.retrieval_queries)} 路子 query"
                    f"（{plan.rewrite_method}）"
                )
            else:
                summary = (
                    f"检索问句已改写（{plan.rewrite_method}）："
                    f"{normalized_query} → {plan.retrieval_query}"
                )
        else:
            summary = "检索问句保持原样（passthrough）"
        return output, summary

    return await run_node_with_trace(
        state,
        node="query_rewrite",
        input_data=input_data,
        summary="完成检索问句改写",
        fn=_execute,
    )
