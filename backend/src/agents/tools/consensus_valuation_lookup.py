"""Consensus valuation lookup for scenario return (EPS × PE bands)."""

from __future__ import annotations

from typing import Any

from ...integrations.market_data.stock_code_resolver import resolve_stock_code
from ...services.consensus_valuation import lookup_consensus_valuation


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    cleaned = str(value).replace("元", "").replace(",", "").strip()
    try:
        parsed = float(cleaned)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def lookup_consensus_valuation_tool(
    *,
    stock_name: str = "",
    stock_code: str = "",
    rag_hits: list[dict[str, Any]] | None = None,
    valuation_tool: dict[str, Any] | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Fetch bear/base/bull scenarios from THS / Eastmoney APIs, KB as fallback."""
    resolved_code, resolved_name = resolve_stock_code(stock_name, stock_code)
    current_price = None
    if isinstance(valuation_tool, dict):
        valuation = valuation_tool.get("valuation")
        if isinstance(valuation, dict):
            current_price = _parse_price(valuation.get("price"))
            stock_name = stock_name or str(valuation.get("stock_name", ""))
    return lookup_consensus_valuation(
        stock_name=resolved_name or stock_name,
        stock_code=resolved_code or stock_code,
        current_price=current_price,
        rag_hits=rag_hits,
    )
