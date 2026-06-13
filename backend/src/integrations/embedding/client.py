"""HTTP client for SiliconFlow OpenAI-compatible embeddings."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from pycore.core import get_logger

logger = get_logger()


class EmbeddingClientError(RuntimeError):
    """Raised when the upstream embedding HTTP call fails."""


class SiliconFlowEmbeddingClient:
    """Thin httpx wrapper for /v1/embeddings."""

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
    def embeddings_url(self) -> str:
        if self.base_url.endswith("/embeddings"):
            return self.base_url
        return f"{self.base_url}/embeddings"

    async def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        """Embed one or more texts and return vectors with latency metadata."""
        if not texts:
            return [], {"latency_ms": 0, "model": self.model, "provider": "siliconflow"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=self.timeout) as client:
                response = await client.post(
                    self.embeddings_url,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            logger.error("Embedding request timed out", model=self.model)
            raise EmbeddingClientError("Embedding 请求超时") from exc
        except httpx.HTTPError as exc:
            logger.error("Embedding transport error", detail=str(exc))
            raise EmbeddingClientError("Embedding 网络请求失败") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            body_preview = response.text[:300]
            logger.error(
                "Embedding upstream error",
                status_code=response.status_code,
                detail=body_preview,
            )
            raise EmbeddingClientError(f"Embedding 上游返回 {response.status_code}")

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            logger.error("Embedding response is not JSON", detail=response.text[:300])
            raise EmbeddingClientError("Embedding 响应不是合法 JSON") from exc

        vectors = self.extract_embeddings(body)
        meta = {
            "latency_ms": latency_ms,
            "model": str(body.get("model", self.model)),
            "provider": "siliconflow",
            "usage": body.get("usage", {}),
        }
        return vectors, meta

    @staticmethod
    def extract_embeddings(body: dict[str, Any]) -> list[list[float]]:
        """Extract embedding vectors from OpenAI-style response."""
        data = body.get("data")
        if not isinstance(data, list) or not data:
            raise EmbeddingClientError("Embedding 响应缺少 data")

        ordered: list[tuple[int, list[float]]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                continue
            index = int(item.get("index", len(ordered)))
            ordered.append((index, [float(value) for value in embedding]))

        if not ordered:
            raise EmbeddingClientError("Embedding 响应向量为空")

        ordered.sort(key=lambda pair: pair[0])
        return [vector for _, vector in ordered]
