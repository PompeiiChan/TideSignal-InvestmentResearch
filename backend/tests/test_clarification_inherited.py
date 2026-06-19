"""Tests for clarification_check with inherited slots."""

from __future__ import annotations

import pytest

from backend.src.agents.nodes.clarification_check import clarification_check
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


def _llm_deps() -> tuple[LLMService, RagService, AppSettings]:
    return LLMService(AppSettings()), RagService(), AppSettings()


@pytest.mark.asyncio
async def test_inherited_stock_name_skips_clarification() -> None:
    state = {
        "intent_id": "stock_analysis",
        "intent_confidence": 0.92,
        "normalized_query": "一季报呢",
        "slots": {
            "stock_name": "宁德时代",
            "stock_code": "300750.SZ",
            "time_range": "2026Q1",
        },
        "missing_slots": ["stock_name"],
        "ambiguous_slots": [],
        "inherited_slot_keys": ["stock_name", "stock_code"],
        "context_pack": {},
        "trace_steps": [],
    }
    llm, rag, settings = _llm_deps()
    result = await clarification_check(state, llm=llm, rag=rag, settings=settings)

    assert result["need_clarification"] is False
    assert "stock_name" not in result["clarification_reason"]
    trace_output = result["trace_steps"][-1]["raw_json"]["output"]
    assert trace_output["inherited_slot_keys"] == ["stock_name", "stock_code"]


@pytest.mark.asyncio
async def test_missing_stock_name_still_clarifies() -> None:
    state = {
        "intent_id": "stock_analysis",
        "intent_confidence": 0.92,
        "normalized_query": "一季报怎么样",
        "slots": {"time_range": "2026Q1"},
        "missing_slots": ["stock_name"],
        "ambiguous_slots": [],
        "inherited_slot_keys": [],
        "context_pack": {},
        "trace_steps": [],
    }
    llm, rag, settings = _llm_deps()
    result = await clarification_check(state, llm=llm, rag=rag, settings=settings)

    assert result["need_clarification"] is True
    assert "stock_name" in result["clarification_reason"]
