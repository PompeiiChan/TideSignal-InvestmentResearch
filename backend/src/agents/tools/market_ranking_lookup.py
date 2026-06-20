"""Live market ranking via Eastmoney push2."""

from __future__ import annotations

import logging
from typing import Any

from ...integrations.market_data.eastmoney_client import (
    fetch_board_stock_ranking,
    find_board_by_keyword,
    industry_board_ranking,
)
from ...services.trading_calendar import resolve_trade_date_label

logger = logging.getLogger(__name__)

_SOURCE = "东方财富 push2（a-stock-data 适配）"
_ATTRIBUTION = "third_party/a-stock-data (Apache-2.0)"


def _board_ticker(board_code: str) -> str:
    code = board_code.strip().upper()
    if code.startswith("BK"):
        return code
    return f"BK{code}"


def _board_rows_to_ranking_rows(
    boards: list[dict[str, Any]],
    *,
    limit: int,
    trade_date: str,
) -> list[dict[str, Any]]:
    """Map industry-board ranking to ranking_table row shape."""
    rows: list[dict[str, Any]] = []
    for board in boards[:limit]:
        rows.append(
            {
                "rank": board.get("rank"),
                "trade_date": trade_date,
                "ticker": _board_ticker(str(board.get("board_code", ""))),
                "stock_name": board.get("board_name", ""),
                "close_price": None,
                "pct_change": board.get("change_pct", 0.0),
                "turnover_amount": None,
                "leader": board.get("leader", ""),
                "leader_change": board.get("leader_change"),
                "is_mock": False,
            }
        )
    return rows


def _industry_search_terms(industry: str) -> list[str]:
    needle = industry.strip()
    if not needle:
        return []
    terms = [needle]
    for suffix in ("行业", "概念", "板块"):
        if needle.endswith(suffix) and len(needle) > len(suffix):
            core = needle[: -len(suffix)].strip()
            if core and core not in terms:
                terms.append(core)
    return terms


def lookup_market_ranking(
    *,
    industry: str = "",
    metric: str = "涨幅排行",
    time_range: str = "近一交易日",
    trade_date: str = "",
    rank_limit: int = 5,
    **_extra: Any,
) -> dict[str, Any]:
    """Query live board/stock rankings from Eastmoney push2."""
    limit = max(int(rank_limit or 5), 1)
    descending = "跌" not in metric
    resolved_trade_date = resolve_trade_date_label(trade_date=trade_date, time_range=time_range)
    time_label = time_range or f"{resolved_trade_date} 盘中/收盘"

    try:
        if industry.strip():
            board = None
            matched_term = industry.strip()
            for term in _industry_search_terms(industry):
                board = find_board_by_keyword(term)
                if board is not None:
                    matched_term = term
                    break
            if board is None:
                return {
                    "tool": "market_ranking_lookup",
                    "industry": industry,
                    "metric": metric,
                    "time_range": time_label,
                    "trade_date": resolved_trade_date,
                    "rows": [],
                    "row_count": 0,
                    "source": _SOURCE,
                    "is_mock": False,
                    "fallback_used": False,
                    "notes": f"未在东财板块列表中匹配到「{industry}」",
                    "attribution": _ATTRIBUTION,
                }
            rows = fetch_board_stock_ranking(
                str(board["board_code"]),
                limit=limit,
                descending=descending,
                trade_date=resolved_trade_date,
            )
            return {
                "tool": "market_ranking_lookup",
                "ranking_mode": "board_stocks",
                "industry": board.get("board_name", matched_term),
                "board_code": board.get("board_code"),
                "board_kind": board.get("board_kind"),
                "metric": metric,
                "time_range": time_label,
                "trade_date": resolved_trade_date,
                "rows": rows,
                "row_count": len(rows),
                "source": _SOURCE,
                "is_mock": False,
                "fallback_used": False,
                "notes": "板块成分股涨跌幅排行，数据来自东财 push2",
                "attribution": _ATTRIBUTION,
            }

        ranking = industry_board_ranking(top_n=limit)
        source_rows = ranking["top"] if descending else ranking["bottom"]
        rows = _board_rows_to_ranking_rows(
            source_rows,
            limit=limit,
            trade_date=resolved_trade_date,
        )
        return {
            "tool": "market_ranking_lookup",
            "ranking_mode": "industry_boards",
            "industry": "全行业",
            "metric": metric,
            "time_range": time_label,
            "trade_date": resolved_trade_date,
            "rows": rows,
            "row_count": len(rows),
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": False,
            "notes": "全行业板块涨跌幅排行（东财行业板块）；rows 中 stock_name 为板块名，非个股",
            "attribution": _ATTRIBUTION,
        }
    except Exception as exc:
        logger.warning("market_ranking_lookup failed: %s", exc)
        return {
            "tool": "market_ranking_lookup",
            "industry": industry or "全行业",
            "metric": metric,
            "time_range": time_label,
            "trade_date": resolved_trade_date,
            "rows": [],
            "row_count": 0,
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": False,
            "error": str(exc),
            "notes": f"东财行情接口调用失败：{exc}",
            "attribution": _ATTRIBUTION,
        }
