"""Industry sector heatmap snapshot for rich_block rendering."""

from __future__ import annotations

import logging
from typing import Any

from ...integrations.market_data.eastmoney_client import industry_heatmap_boards
from ...services.trading_calendar import resolve_trade_date_label

logger = logging.getLogger(__name__)

_SOURCE = "东方财富 push2（a-stock-data 适配）"
_ATTRIBUTION = "third_party/a-stock-data (Apache-2.0)"

def _normalize_tiles(boards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tiles: list[dict[str, Any]] = []
    for board in boards:
        name = str(board.get("board_name", "")).strip()
        if not name:
            continue
        tiles.append(
            {
                "board_name": name,
                "board_code": str(board.get("board_code", "")),
                "pct_change": float(board.get("change_pct") or board.get("pct_change") or 0.0),
                "turnover_amount": float(board.get("turnover_amount") or 0.0),
                "leader": str(board.get("leader", "")),
                "leader_change": board.get("leader_change"),
                "up_count": int(board.get("up_count") or 0),
                "down_count": int(board.get("down_count") or 0),
            }
        )
    return tiles


def lookup_sector_heatmap(
    *,
    board_kind: str = "industry",
    board_limit: int = 30,
    trade_date: str = "",
    time_range: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Return industry-board heatmap tiles sized by turnover from Eastmoney push2."""
    limit = max(min(int(board_limit or 30), 50), 5)
    resolved_trade_date = resolve_trade_date_label(trade_date=trade_date, time_range=time_range)
    if board_kind.strip() and board_kind.strip() != "industry":
        return {
            "tool": "sector_heatmap_lookup",
            "board_kind": board_kind,
            "board_limit": limit,
            "trade_date": resolved_trade_date,
            "tiles": [],
            "tile_count": 0,
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": False,
            "notes": "当前仅支持行业板块热力图（board_kind=industry）",
            "attribution": _ATTRIBUTION,
        }

    try:
        boards = industry_heatmap_boards(limit=limit)
        tiles = _normalize_tiles(boards)
        if not tiles:
            raise ValueError("东财行业板块列表为空")
        return {
            "tool": "sector_heatmap_lookup",
            "board_kind": "industry",
            "board_limit": limit,
            "trade_date": resolved_trade_date,
            "tiles": tiles,
            "tile_count": len(tiles),
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": False,
            "notes": "行业板块热力图：方块面积按成交额缩放，颜色按涨跌幅着色",
            "attribution": _ATTRIBUTION,
        }
    except Exception as exc:
        logger.warning("sector_heatmap_lookup failed: %s", exc)
        return {
            "tool": "sector_heatmap_lookup",
            "board_kind": "industry",
            "board_limit": limit,
            "trade_date": resolved_trade_date,
            "tiles": [],
            "tile_count": 0,
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": False,
            "error": str(exc),
            "notes": f"东财行业板块接口调用失败：{exc}",
            "attribution": _ATTRIBUTION,
        }
