"""Fixed-formula return calculator — no LLM involvement in numeric results."""

from __future__ import annotations

from typing import Any


def compute_return(
    *,
    buy_price: float,
    sell_price: float,
    share_count: int,
    fee_rate: float = 0.0003,
    **_extra: Any,
) -> dict[str, Any]:
    """Compute net profit and return percentage with a deterministic formula."""
    gross = (sell_price - buy_price) * share_count
    fee = (buy_price + sell_price) * share_count * fee_rate
    net_profit = gross - fee
    return_pct = (sell_price / buy_price - 1) * 100 if buy_price else 0.0
    return {
        "buy_price": buy_price,
        "sell_price": sell_price,
        "share_count": share_count,
        "fee_rate": fee_rate,
        "gross_profit": round(gross, 2),
        "fee_total": round(fee, 2),
        "net_profit": round(net_profit, 2),
        "return_pct": round(return_pct, 4),
        "formula": "net_profit = (sell_price - buy_price) * share_count - (buy_price + sell_price) * share_count * fee_rate",
        "source": "local_return_calculator",
        "is_mock": True,
    }
