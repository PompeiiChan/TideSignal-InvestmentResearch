"""Mock market ranking lookup from embedded demo quotes."""

from __future__ import annotations

from typing import Any

_DEMO_QUOTES: list[dict[str, Any]] = [
    {
        "trade_date": "2026-04-30",
        "company_id": "company_688256",
        "ticker": "688256.SH",
        "stock_name": "寒武纪",
        "close_price": 948.5,
        "pct_change": 1.36,
        "turnover_amount": 11190000000,
        "is_mock": True,
    },
    {
        "trade_date": "2026-04-30",
        "company_id": "company_300750",
        "ticker": "300750.SZ",
        "stock_name": "宁德时代",
        "close_price": 331.4,
        "pct_change": -1.89,
        "turnover_amount": 13620000000,
        "is_mock": True,
    },
    {
        "trade_date": "2026-04-30",
        "company_id": "company_000568",
        "ticker": "000568.SZ",
        "stock_name": "泸州老窖",
        "close_price": 140.85,
        "pct_change": -0.18,
        "turnover_amount": 2270000000,
        "is_mock": True,
    },
    {
        "trade_date": "2026-04-30",
        "company_id": "company_603288",
        "ticker": "603288.SH",
        "stock_name": "海天味业",
        "close_price": 43.05,
        "pct_change": -0.58,
        "turnover_amount": 943000000,
        "is_mock": True,
    },
    {
        "trade_date": "2026-04-30",
        "company_id": "company_002293",
        "ticker": "002293.SZ",
        "stock_name": "罗莱生活",
        "close_price": 9.75,
        "pct_change": -0.41,
        "turnover_amount": 118000000,
        "is_mock": True,
    },
]


def lookup_market_ranking(
    *,
    industry: str = "",
    metric: str = "涨幅排行",
    time_range: str = "近一交易日",
    rank_limit: int = 5,
    **_extra: Any,
) -> dict[str, Any]:
    """Return a sorted mock ranking table for demo data queries."""
    rows = sorted(_DEMO_QUOTES, key=lambda item: item["pct_change"], reverse=True)
    if rank_limit > 0:
        rows = rows[:rank_limit]
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return {
        "tool": "mock_market_ranking_lookup",
        "industry": industry or "全市场",
        "metric": metric,
        "time_range": time_range,
        "rows": rows,
        "row_count": len(rows),
        "source": "backend/data/knowledge-base/structured-data/stock_daily_quotes_mock.md",
        "is_mock": True,
        "notes": "演示用 mock 行情，不代表真实价格",
    }
