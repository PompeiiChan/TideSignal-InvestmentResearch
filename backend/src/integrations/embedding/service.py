"""High-level embedding service."""

from __future__ import annotations

import asyncio

from pycore.core import get_logger

from ...settings import AppSettings, get_settings
from .client import EmbeddingClientError, SiliconFlowEmbeddingClient

logger = get_logger()

_MAX_RETRIES = 3


class EmbeddingNotConfiguredError(RuntimeError):
    """Raised when embedding configuration is incomplete."""


class EmbeddingService:
    """Orchestrates SiliconFlow embedding calls."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        return bool(
            self.settings.embedding_api_key.strip()
            and self.settings.embedding_base_url.strip()
            and self.settings.embedding_model.strip()
            and self.settings.embedding_dim.strip()
        )

    def configured_dim(self) -> int:
        try:
            return int(self.settings.embedding_dim.strip())
        except ValueError:
            return 0

    def configured_timeout(self) -> float:
        try:
            return float(self.settings.embedding_timeout.strip())
        except ValueError:
            return 180.0

    def _client(self) -> SiliconFlowEmbeddingClient:
        if not self.is_configured():
            raise EmbeddingNotConfiguredError("Embedding 配置不完整，请检查 EMBEDDING_* 环境变量")
        return SiliconFlowEmbeddingClient(
            api_key=self.settings.embedding_api_key,
            base_url=self.settings.embedding_base_url,
            model=self.settings.embedding_model,
            timeout=self.configured_timeout(),
        )

    async def embed_text(self, text: str) -> tuple[list[float], dict[str, object]]:
        vectors, meta = await self.embed_texts([text])
        return vectors[0], meta

    async def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], dict[str, object]]:
        last_error: EmbeddingClientError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                client = self._client()
                vectors, meta = await client.embed_texts(texts)
                expected_dim = self.configured_dim()
                if expected_dim > 0:
                    for vector in vectors:
                        if len(vector) != expected_dim:
                            raise EmbeddingClientError(
                                f"Embedding 维度不匹配：期望 {expected_dim}，实际 {len(vector)}"
                            )
                return vectors, meta
            except EmbeddingNotConfiguredError:
                raise
            except EmbeddingClientError as exc:
                last_error = exc
                if attempt >= _MAX_RETRIES - 1:
                    break
                delay = 2**attempt
                logger.warning(
                    "Embedding request failed, retrying",
                    attempt=attempt + 1,
                    delay_s=delay,
                    detail=str(exc),
                )
                await asyncio.sleep(delay)
        if last_error is None:
            raise EmbeddingClientError("Embedding 请求失败")
        raise last_error
