"""Tests for evidence_merge conversation_context carryover."""

from __future__ import annotations

import pytest

from backend.src.agents.nodes.evidence_merge import evidence_merge
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


@pytest.mark.asyncio
async def test_evidence_merge_writes_conversation_context() -> None:
    state = {
        "normalized_query": "一季报呢",
        "history_summary": "user: 宁德时代基本面怎么样\nassistant: 营收稳健…",
        "slots": {
            "stock_name": "宁德时代",
            "stock_code": "300750.SZ",
            "time_range": "2026Q1",
        },
        "active_slots": {
            "stock_name": "宁德时代",
            "stock_code": "300750.SZ",
            "time_range": "2026Q1",
        },
        "inherited_slot_keys": ["stock_name", "stock_code"],
        "agent_result": "规划要点",
        "tool_result": {},
        "rag_hits": [],
        "retrieved_chunks": [],
        "citations": [],
        "trace_steps": [],
    }
    llm, rag, settings = LLMService(AppSettings()), RagService(), AppSettings()

    result = await evidence_merge(state, llm=llm, rag=rag, settings=settings)

    evidence_pack = result["evidence_pack"]
    assert evidence_pack["conversation_context"]["has_context"] is True
    assert evidence_pack["active_slots"]["stock_name"] == "宁德时代"
    trace_input = result["trace_steps"][-1]["raw_json"]["input"]
    assert trace_input["has_conversation_context"] is True
