"""document_qa_agent node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.prompts.agents.document_qa import document_qa_agent_prompt
from ...integrations.llm.service import LLMService
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ._helpers import (
    call_intent_json,
    response_kind_for_intent,
    run_node_with_trace,
)


async def document_qa_agent(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Plan document QA via LLM sub-agent."""
    _ = rag
    normalized_query = str(state.get("normalized_query", "")).strip()
    slots = state.get("slots") or {}
    context_pack = state.get("context_pack") or {}
    intent_id = str(state.get("intent_id", "document_qa"))

    input_data = {
        "normalized_query": normalized_query,
        "slots": slots,
        "context_pack": context_pack,
        "intent_id": intent_id,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        time_ctx = resolve_system_time(settings)
        parsed = await call_intent_json(
            llm,
            system_prompt=document_qa_agent_prompt(time_ctx),
            user_payload=input_data,
        )
        agent_result = str(parsed.get("agent_result", "")).strip()
        document_id = str(
            parsed.get("document_id")
            or slots.get("document_id")
            or context_pack.get("active_document_id")
            or ""
        ).strip()
        quoted_chunks = parsed.get("quoted_chunks")
        if not isinstance(quoted_chunks, list):
            quoted_chunks = []
        doc_citations = parsed.get("doc_citations")
        if not isinstance(doc_citations, list):
            doc_citations = []
        output = {
            "agent_result": agent_result,
            "document_id": document_id,
            "quoted_chunks": quoted_chunks,
            "doc_citations": doc_citations,
            "response_kind": response_kind_for_intent(intent_id),
        }
        return output, "完成文档问答规划"

    return await run_node_with_trace(
        state,
        node="document_qa_agent",
        input_data=input_data,
        summary="完成文档问答规划",
        fn=_execute,
    )
