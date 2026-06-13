"""High-level rerank service."""

from __future__ import annotations

import asyncio

from pycore.core import get_logger

from ...settings import AppSettings, get_settings
from .client import RerankClientError, SiliconFlowRerankClient

logger = get_logger()

_MAX_RETRIES = 2


class RerankNotConfiguredError(RuntimeError):
    """Raised when rerank configuration is incomplete."""


class RerankService:
    """Orchestrates SiliconFlow rerank calls."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        return bool(
            self.settings.rerank_api_key.strip()
            and self.settings.rerank_base_url.strip()
            and self.settings.rerank_model.strip()
        )

    def _client(self) -> SiliconFlowRerankClient:
        if not self.is_configured():
            raise RerankNotConfiguredError("Rerank 配置不完整，请检查 RERANK_* 环境变量")
        return SiliconFlowRerankClient(
            api_key=self.settings.rerank_api_key,
            base_url=self.settings.rerank_base_url,
            model=self.settings.rerank_model,
        )

    async def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[tuple[int, float]]:
        last_error: RerankClientError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                client = self._client()
                ranked, _meta = await client.rerank(query, documents, top_n=top_n)
                return ranked
            except RerankNotConfiguredError:
                raise
            except RerankClientError as exc:
                last_error = exc
                if attempt >= _MAX_RETRIES - 1:
                    break
                await asyncio.sleep(2**attempt)
        if last_error is None:
            raise RerankClientError("Rerank 请求失败")
        raise last_error
