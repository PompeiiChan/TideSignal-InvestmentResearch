"""HTTP client for SiliconFlow /v1/rerank."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from pycore.core import get_logger

logger = get_logger()


class RerankClientError(RuntimeError):
    """Raised when the upstream rerank HTTP call fails."""


class SiliconFlowRerankClient:
    """Thin httpx wrapper for /v1/rerank."""

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
    def rerank_url(self) -> str:
        if self.base_url.endswith("/rerank"):
            return self.base_url
        return f"{self.base_url}/rerank"

    async def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        top_n: int,
    ) -> tuple[list[tuple[int, float]], dict[str, Any]]:
        if not documents:
            return [], {"latency_ms": 0, "model": self.model, "provider": "siliconflow"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": top_n,
            "return_documents": False,
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=self.timeout) as client:
                response = await client.post(self.rerank_url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            logger.error("Rerank request timed out", model=self.model)
            raise RerankClientError("Rerank 请求超时") from exc
        except httpx.HTTPError as exc:
            logger.error("Rerank transport error", detail=str(exc))
            raise RerankClientError("Rerank 网络请求失败") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            logger.error("Rerank upstream error", status_code=response.status_code, detail=response.text[:300])
            raise RerankClientError(f"Rerank 上游返回 {response.status_code}")

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise RerankClientError("Rerank 响应不是合法 JSON") from exc

        results = body.get("results")
        if not isinstance(results, list):
            raise RerankClientError("Rerank 响应缺少 results")

        ranked: list[tuple[int, float]] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            index = int(item.get("index", -1))
            raw_score = item.get("relevance_score", item.get("score", 0.0))
            score = float(raw_score) if raw_score is not None else 0.0
            if index >= 0:
                ranked.append((index, score))

        meta = {
            "latency_ms": latency_ms,
            "model": str(body.get("model", self.model)),
            "provider": "siliconflow",
        }
        return ranked, meta
