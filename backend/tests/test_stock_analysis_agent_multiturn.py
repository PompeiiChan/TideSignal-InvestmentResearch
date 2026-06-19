"""Tests for stock_analysis_agent multi-turn context payload."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.agents.nodes.stock_analysis_agent import stock_analysis_agent
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


@pytest.mark.asyncio
async def test_stock_analysis_agent_passes_conversation_context() -> None:
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
            "agent_result": "宁德时代 2026Q1 一季报解读规划",
            "analysis_dimensions": ["一季报业绩", "盈利质量"],
            "tool_names": ["mock_financial_profile_lookup"],
            "tool_params": {
                "stock_name": "宁德时代",
                "stock_code": "300750.SZ",
                "analysis_dimension": "一季报",
            },
        }

    state = {
        "normalized_query": "一季报呢",
        "intent_id": "stock_analysis",
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
        "trace_steps": [],
    }
    llm, rag, settings = LLMService(AppSettings()), RagService(), AppSettings()

    with patch(
        "backend.src.agents.nodes.stock_analysis_agent.call_intent_json",
        new=AsyncMock(side_effect=fake_call_intent_json),
    ):
        result = await stock_analysis_agent(state, llm=llm, rag=rag, settings=settings)

    assert captured_payload["active_slots"]["stock_name"] == "宁德时代"
    assert captured_payload["history_summary"].startswith("user: 宁德时代")
    assert captured_payload["conversation_context"]["has_context"] is True
    trace_input = result["trace_steps"][-1]["raw_json"]["input"]
    assert trace_input["conversation_context"]["has_context"] is True
    assert trace_input["active_slots"]["stock_name"] == "宁德时代"
