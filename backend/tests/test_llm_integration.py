"""Unit tests for SiliconFlow LLM integration."""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.integrations.llm.client import LLMClientError, SiliconFlowLLMClient
from backend.src.integrations.llm.service import LLMNotConfiguredError, LLMService
from backend.src.settings import AppSettings


def _chat_body(content: str) -> dict:
    return {
        "id": "chatcmpl-test",
        "model": "deepseek-ai/DeepSeek-V3",
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


@pytest.mark.asyncio
async def test_llm_service_recognize_intent_parses_json() -> None:
    payload = {
        "response_kind": "hotspot",
        "intent_level_1": "热点归因",
        "intent_level_2": "产业催化",
        "subject_type": "sector",
        "subject_name": "机器人板块",
        "action_type": "归因",
        "risk_level": "medium",
        "route_reason": "热点问题",
        "sub_agent": "hotspot_agent",
        "agent_label": "热点助手",
    }
    settings = AppSettings(
        llm_api_key="output-key",
        llm_base_url="https://api.siliconflow.cn/v1",
        llm_model="Qwen/Qwen3.5-27B",
        llm_intent_api_key="intent-key",
        llm_intent_base_url="https://api.siliconflow.cn/v1",
        llm_intent_model="deepseek-ai/DeepSeek-V3",
    )
    service = LLMService(settings)
    with patch.object(
        SiliconFlowLLMClient,
        "chat_completion",
        new=AsyncMock(return_value=_chat_body(json.dumps(payload, ensure_ascii=False))),
    ):
        result = await service.recognize_intent("机器人板块为什么涨")

    assert result.response_kind == "hotspot"
    assert result.agent_label == "热点助手"
    assert result.meta.model


@pytest.mark.asyncio
async def test_llm_service_requires_configuration() -> None:
    service = LLMService(AppSettings())
    with pytest.raises(LLMNotConfiguredError):
        await service.recognize_intent("测试")


def test_siliconflow_client_extract_message_content() -> None:
    content = SiliconFlowLLMClient.extract_message_content(_chat_body('{"response_kind":"data"}'))
    assert "response_kind" in content


def test_siliconflow_client_rejects_empty_content() -> None:
    with pytest.raises(LLMClientError):
        SiliconFlowLLMClient.extract_message_content({"choices": [{"message": {"content": ""}}]})


def test_llm_service_routes_intent_and_output_models() -> None:
    settings = AppSettings(
        llm_api_key="output-key",
        llm_base_url="https://api.siliconflow.cn/v1",
        llm_model="Qwen/Qwen3.5-27B",
        llm_intent_api_key="intent-key",
        llm_intent_base_url="https://api.siliconflow.cn/v1",
        llm_intent_model="deepseek-ai/DeepSeek-V3",
    )
    service = LLMService(settings)
    intent_client = service._intent_client()
    output_client = service._output_client()
    assert intent_client.model == "deepseek-ai/DeepSeek-V3"
    assert intent_client.api_key == "intent-key"
    assert output_client.model == "Qwen/Qwen3.5-27B"
    assert output_client.api_key == "output-key"


def test_llm_service_enrich_rich_blocks_keeps_only_interactive_blocks() -> None:
    content = "第一段分析。\n\n第二段展开催化因素，包含政策与订单预期。"
    blocks = [
        {
            "type": "text",
            "title": "机器人板块近期核心催化因素",
            "payload": {"paragraphs": ["应写入正文"]},
            "sources": [],
            "risk_notice": "",
        },
        {
            "type": "ranking_table",
            "title": "涨幅排行",
            "payload": {"columns": ["rank", "name"], "rows": [{"rank": 1, "name": "寒武纪"}]},
            "sources": [],
            "risk_notice": "",
        },
        {
            "type": "citation_list",
            "title": "引用来源",
            "payload": {"items": [{"type": "report", "label": "模型整理"}]},
            "sources": [],
            "risk_notice": "",
        },
    ]
    enriched = LLMService.enrich_rich_blocks(content, blocks, "hotspot")
    assert [item["type"] for item in enriched] == ["ranking_table"]


def test_llm_service_parse_json_from_mixed_thinking_text() -> None:
    mixed = (
        "Thinking Process:\n\n1. Analyze the request.\n\n"
        '{"response_kind":"data","intent_level_1":"行情查询"}'
    )
    parsed = LLMService._parse_json_payload(mixed)
    assert parsed["response_kind"] == "data"


def test_siliconflow_client_falls_back_to_reasoning_content() -> None:
    body = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "reasoning_content": '{"response_kind":"data"}',
                },
                "finish_reason": "length",
            }
        ]
    }
    content = SiliconFlowLLMClient.extract_message_content(body)
    assert "response_kind" in content


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("REAL_API_TEST"), reason="REAL_API_TEST not set")
async def test_real_siliconflow_llm_call() -> None:
    """Optional real upstream call for manual verification."""
    from backend.src.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    service = LLMService(settings)
    if not service.is_configured():
        pytest.skip("LLM is not configured in backend/.env")

    intent = await service.recognize_intent("半导体板块今天涨幅靠前有哪些")
    assert intent.response_kind in {"data", "hotspot", "stock", "calculator"}
    assert intent.meta.total_tokens >= 0
