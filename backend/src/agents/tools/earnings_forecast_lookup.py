"""Earnings forecast lookup tool for scenario return calculator."""

from __future__ import annotations

from typing import Any

from ...services.earnings_forecast import extract_earnings_forecast


def lookup_earnings_forecast(
    *,
    stock_name: str = "",
    stock_code: str = "",
    rag_hits: list[dict[str, Any]] | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Extract bull/base/bear scenarios from passed RAG hits (Phase 2)."""
    _ = stock_code
    return extract_earnings_forecast(rag_hits, stock_name=stock_name)
