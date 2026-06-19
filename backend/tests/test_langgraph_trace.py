"""Tests for LangGraph trace persistence."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.agents.nodes.intent_recognition import intent_recognition
from backend.src.db.models import Base
from backend.src.integrations.langgraph.trace_recorder import TraceRecorder
from backend.src.integrations.llm.prompts.intent import INTENT_SYSTEM_PROMPT_BASE
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.services.trace_service import TraceService
from backend.src.settings import AppSettings


def test_langgraph_intent_prompt_removes_calculator() -> None:
    """LangGraph intent prompt excludes calculator and documents prediction_request."""
    lowered = INTENT_SYSTEM_PROMPT_BASE.lower()
    assert "response_kind: calculator" not in lowered
    assert "prediction_request" in INTENT_SYSTEM_PROMPT_BASE
    assert "不得由模型自由" in INTENT_SYSTEM_PROMPT_BASE


def test_intent_prompt_mentions_history_summary() -> None:
    """Intent prompt documents follow-up handling with history_summary."""
    assert "history_summary" in INTENT_SYSTEM_PROMPT_BASE
    assert "多轮续问" in INTENT_SYSTEM_PROMPT_BASE
    assert "一季报呢" in INTENT_SYSTEM_PROMPT_BASE


@pytest.mark.asyncio
async def test_intent_follow_up_with_mock_llm() -> None:
    """Follow-up intent recognition passes history_summary in the LLM payload."""
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
            "intent_id": "stock_analysis",
            "intent_name": "个股分析",
            "intent_confidence": 0.91,
            "candidate_intents": [{"intent_id": "stock_analysis", "confidence": 0.91}],
            "missing_slots": [],
        }

    state = {
        "normalized_query": "一季报呢",
        "history_summary": "user: 宁德时代基本面怎么样\nassistant: 宁德时代营收稳健…",
        "context_pack": {"history_count": 2},
        "trace_steps": [],
    }
    llm, rag, settings = LLMService(AppSettings()), RagService(), AppSettings()

    with patch(
        "backend.src.agents.nodes.intent_recognition.call_intent_json",
        new=AsyncMock(side_effect=fake_call_intent_json),
    ):
        result = await intent_recognition(state, llm=llm, rag=rag, settings=settings)

    assert captured_payload["history_summary"].startswith("user: 宁德时代")
    assert captured_payload["normalized_query"] == "一季报呢"
    assert result["intent_id"] == "stock_analysis"
    assert result["trace_steps"][-1]["raw_json"]["input"]["history_summary"]


@pytest.mark.asyncio
async def test_create_langgraph_trace_writes_context_preprocess_step(tmp_path: Path) -> None:
    """create_langgraph_trace persists recorder-produced context_preprocess step."""
    db_path = tmp_path / "langgraph_trace.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    step = TraceRecorder.record(
        node="context_preprocess",
        step_index=1,
        status="success",
        latency_ms=12,
        input_data={"user_query": "白酒龙头热度排第几？"},
        output_data={"normalized_query": "查询白酒板块龙头热度排名"},
        summary="完成上下文预处理",
    )

    async with session_maker() as session:
        service = TraceService(session)
        trace = await service.create_langgraph_trace(
            trace_id="trace_langgraph_p1",
            session_id="session_test",
            message_id="msg_test",
            user_query="白酒龙头热度排第几？",
            steps=[step],
        )
        loaded = await service.get_trace(trace.id)

    await engine.dispose()

    assert trace.steps[0]["node"] == "context_preprocess"
    assert loaded.steps[0].node == "context_preprocess"
    assert loaded.metadata.total_latency_ms == 12
