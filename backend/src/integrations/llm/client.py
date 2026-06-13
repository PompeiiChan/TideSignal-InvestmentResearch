"""HTTP client for SiliconFlow OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx

from pycore.core import get_logger

logger = get_logger()


class LLMClientError(RuntimeError):
    """Raised when the upstream LLM HTTP call fails."""


class SiliconFlowLLMClient:
    """Thin httpx wrapper for /v1/chat/completions."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.strip().rstrip("/")
        self.model = model.strip()
        self.timeout = timeout

    @property
    def chat_completions_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        enable_thinking: bool = False,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        """Call chat completions and return parsed JSON body with latency metadata."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # Qwen3 / Qwen3.5: must disable thinking at top-level AND template kwargs,
        # otherwise output lands in reasoning_content without JSON.
        if not enable_thinking:
            payload["enable_thinking"] = False
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=self.timeout) as client:
                response = await client.post(
                    self.chat_completions_url,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            logger.error("LLM request timed out", model=self.model)
            raise LLMClientError("LLM 请求超时") from exc
        except httpx.HTTPError as exc:
            logger.error("LLM transport error", detail=str(exc))
            raise LLMClientError("LLM 网络请求失败") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            body_preview = response.text[:300]
            logger.error(
                "LLM upstream error",
                status_code=response.status_code,
                detail=body_preview,
            )
            raise LLMClientError(f"LLM 上游返回 {response.status_code}")

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            logger.error("LLM response is not JSON", detail=response.text[:300])
            raise LLMClientError("LLM 响应不是合法 JSON") from exc

        body["_latency_ms"] = latency_ms
        return cast(dict[str, Any], body)

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int = 2048,
        enable_thinking: bool = False,
    ) -> AsyncIterator[str]:
        """Stream chat completion deltas (SiliconFlow OpenAI-compatible SSE)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if not enable_thinking:
            payload["enable_thinking"] = False
            payload["chat_template_kwargs"] = {"enable_thinking": False}

        try:
            async with (
                httpx.AsyncClient(trust_env=False, timeout=self.timeout) as client,
                client.stream(
                    "POST",
                    self.chat_completions_url,
                    headers=headers,
                    json=payload,
                ) as response,
            ):
                    if response.status_code >= 400:
                        body_preview = (await response.aread())[:300].decode("utf-8", errors="replace")
                        logger.error(
                            "LLM stream upstream error",
                            status_code=response.status_code,
                            detail=body_preview,
                        )
                        raise LLMClientError(f"LLM 上游返回 {response.status_code}")

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line.removeprefix("data:").strip()
                        if not data or data == "[DONE]":
                            if data == "[DONE]":
                                break
                            continue
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices")
                        if not isinstance(choices, list) or not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        if not isinstance(delta, dict):
                            continue
                        content = delta.get("content")
                        if isinstance(content, str) and content:
                            yield content
        except httpx.TimeoutException as exc:
            logger.error("LLM stream timed out", model=self.model)
            raise LLMClientError("LLM 请求超时") from exc
        except httpx.HTTPError as exc:
            logger.error("LLM stream transport error", detail=str(exc))
            raise LLMClientError("LLM 网络请求失败") from exc

    @staticmethod
    def extract_message_content(body: dict[str, Any]) -> str:
        """Extract assistant message content from OpenAI-style response."""
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMClientError("LLM 响应缺少 choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        reasoning = message.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()
        raise LLMClientError("LLM 响应 content 为空")

    @staticmethod
    def build_call_meta(body: dict[str, Any]) -> dict[str, Any]:
        """Build observability metadata without secrets."""
        usage = body.get("usage") or {}
        choice = (body.get("choices") or [{}])[0]
        return {
            "model": str(body.get("model", "")),
            "latency_ms": int(body.get("_latency_ms", 0)),
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
            "finish_reason": str(choice.get("finish_reason", "stop")),
            "provider": "siliconflow",
        }
