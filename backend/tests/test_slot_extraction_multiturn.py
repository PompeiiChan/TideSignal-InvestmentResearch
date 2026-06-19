"""Tests for multi-turn slot extraction with pending_slots."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.agents.nodes.slot_extraction import slot_extraction
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


@pytest.mark.asyncio
async def test_slot_extraction_merges_pending_stock_name() -> None:
    captured_payload: dict[str, Any] = {}

    async def fake_call_intent_json(
        _llm: LLMService,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        _ = (system_prompt, temperature)
        captured_payload.update(user_payload)
        return {
            "slots": {"time_range": "2026Q1", "analysis_dimension": "一季报"},
            "slot_confidence": {"time_range": 0.9},
            "missing_slots": ["stock_name"],
            "ambiguous_slots": [],
        }

    state = {
        "normalized_query": "一季报呢",
        "intent_id": "stock_analysis",
        "history_summary": "user: 宁德时代基本面怎么样\nassistant: 营收稳健…",
        "pending_slots": {"stock_name": "宁德时代", "stock_code": "300750.SZ"},
        "pending_intent_id": "stock_analysis",
        "context_pack": {"pending_slots": {"stock_name": "宁德时代"}},
        "trace_steps": [],
    }
    llm, rag, settings = LLMService(AppSettings()), RagService(), AppSettings()

    with patch(
        "backend.src.agents.nodes.slot_extraction.call_intent_json",
        new=AsyncMock(side_effect=fake_call_intent_json),
    ):
        result = await slot_extraction(state, llm=llm, rag=rag, settings=settings)

    assert captured_payload["pending_slots"]["stock_name"] == "宁德时代"
    assert captured_payload["history_summary"].startswith("user: 宁德时代")
    assert result["slots"]["stock_name"] == "宁德时代"
    assert result["slots"]["time_range"] == "2026Q1"
    assert "stock_name" in result["inherited_slot_keys"]
    assert "stock_name" not in result["missing_slots"]
    trace_output = result["trace_steps"][-1]["raw_json"]["output"]
    assert trace_output["extracted_slots"]["time_range"] == "2026Q1"
    assert trace_output["pending_slots"]["stock_name"] == "宁德时代"
    assert trace_output["inherited_slot_keys"]


@pytest.mark.asyncio
async def test_slot_extraction_overrides_pending_stock_name() -> None:
    async def fake_call_intent_json(
        _llm: LLMService,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        _ = (system_prompt, temperature, user_payload)
        return {
            "slots": {"stock_name": "泸州老窖"},
            "slot_confidence": {"stock_name": 0.95},
            "missing_slots": [],
            "ambiguous_slots": [],
        }

    state = {
        "normalized_query": "泸州老窖呢",
        "intent_id": "stock_analysis",
        "pending_slots": {"stock_name": "宁德时代"},
        "pending_intent_id": "stock_analysis",
        "context_pack": {},
        "trace_steps": [],
    }
    llm, rag, settings = LLMService(AppSettings()), RagService(), AppSettings()

    with patch(
        "backend.src.agents.nodes.slot_extraction.call_intent_json",
        new=AsyncMock(side_effect=fake_call_intent_json),
    ):
        result = await slot_extraction(state, llm=llm, rag=rag, settings=settings)

    assert result["slots"]["stock_name"] == "泸州老窖"
    assert "stock_name" in result["overridden_slot_keys"]
