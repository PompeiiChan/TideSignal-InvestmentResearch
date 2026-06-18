"""Tests for authoritative system time injection."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.integrations.llm.models import AnswerResult, LLMCallMeta
from backend.src.integrations.llm.prompts import quality_system_prompt
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.models import RagHit
from backend.src.services.rag.service import (
    format_rag_context,
    format_source_time,
    hits_to_source_refs,
)
from backend.src.services.system_time import SystemTimeContext, resolve_system_time
from backend.src.settings import AppSettings


def test_resolve_system_time_from_reference_date() -> None:
    settings = AppSettings(reference_date="2026-06-12", timezone="Asia/Shanghai")
    ctx = resolve_system_time(settings)
    assert ctx.current_date == "2026-06-12"
    assert ctx.last_trading_day == "2026-06-12"
    assert ctx.is_trading_day is True
    assert ctx.source == "REFERENCE_DATE"
    assert "2026-06-12" in ctx.prompt_block()


def test_hits_to_source_refs_uses_time_period() -> None:
    ctx = SystemTimeContext(current_date="2026-06-12", timezone="Asia/Shanghai", source="test")
    hit = RagHit(
        doc_id="doc1",
        title="泸州老窖 2025 年年报",
        source_type="financial",
        path="financials/luzhou.md",
        score=0.9,
        snippet="营收",
        relevance_reason="test",
        time_period="2025A",
    )
    refs = hits_to_source_refs([hit], ctx=ctx)
    assert refs[0]["time"] == "2025A，本地知识库"


def test_format_rag_context_includes_system_time_and_period() -> None:
    ctx = SystemTimeContext(current_date="2026-06-12", timezone="Asia/Shanghai", source="test")
    hit = RagHit(
        doc_id="doc1",
        title="测试文档",
        source_type="financial",
        path="financials/x.md",
        score=0.8,
        snippet="片段",
        relevance_reason="test",
        time_period="2025A",
    )
    text = format_rag_context([hit], ctx=ctx)
    assert "current_date: 2026-06-12" in text
    assert "time_period=2025A" in text


def test_quality_system_prompt_forbids_calendar_hallucination_fail() -> None:
    ctx = SystemTimeContext(current_date="2026-06-12", timezone="Asia/Shanghai", source="test")
    prompt = quality_system_prompt(ctx)
    assert "system_context.current_date" in prompt
    assert "2025A" in prompt
    assert "不得仅因" in prompt


@pytest.mark.asyncio
async def test_quality_check_payload_includes_system_context_and_rag_citations() -> None:
    service = LLMService(
        AppSettings(
            llm_intent_api_key="k",
            llm_intent_base_url="https://example.com/v1",
            llm_intent_model="intent-model",
            llm_api_key="k",
            llm_base_url="https://example.com/v1",
            llm_model="output-model",
            reference_date="2026-06-12",
        )
    )
    captured: dict[str, object] = {}

    async def fake_chat(messages: list[dict[str, str]], **kwargs: object) -> dict[str, object]:
        captured["messages"] = messages
        return {
            "choices": [{"message": {"content": json.dumps({"overall_result": "PASS"})}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    with patch.object(service, "_intent_client") as mock_client_factory:
        client = mock_client_factory.return_value
        client.chat_completion = AsyncMock(side_effect=fake_chat)
        client.extract_message_content = lambda body: body["choices"][0]["message"]["content"]
        client.model = "intent-model"

        answer = AnswerResult(
            content="测试回答",
            response_kind="stock",
            rich_blocks=[],
            meta=LLMCallMeta(
                model="m",
                latency_ms=1,
                prompt_tokens=1,
                completion_tokens=1,
                total_tokens=2,
                finish_reason="stop",
                raw_json={},
            ),
        )
        hits = [
            RagHit(
                doc_id="d1",
                title="年报",
                source_type="financial",
                path="f.md",
                score=0.9,
                snippet="x",
                relevance_reason="r",
                time_period="2025A",
            )
        ]
        await service.quality_check("泸州老窖营收", answer, rag_hits=hits)

    messages = captured["messages"]
    assert isinstance(messages, list)
    user_payload = json.loads(messages[1]["content"])
    assert user_payload["system_context"]["current_date"] == "2026-06-12"
    assert user_payload["system_context"]["last_trading_day"] == "2026-06-12"
    assert user_payload["rag_citations"][0]["time_period"] == "2025A"
    assert "2026-06-12" in messages[0]["content"]


def test_format_source_time_fallback_without_period() -> None:
    ctx = SystemTimeContext(current_date="2026-06-12", timezone="Asia/Shanghai", source="test")
    hit = RagHit(
        doc_id="d",
        title="t",
        source_type="knowledge",
        path="p",
        score=0.1,
        snippet="s",
        relevance_reason="r",
    )
    assert format_source_time(hit, ctx) == "截至 2026-06-12，本地知识库"
