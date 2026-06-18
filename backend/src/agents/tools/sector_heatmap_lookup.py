"""Industry sector heatmap snapshot for rich_block rendering."""

from __future__ import annotations

import logging
from typing import Any

from ...integrations.market_data.eastmoney_client import industry_heatmap_boards
from ...services.trading_calendar import resolve_default_trade_date

logger = logging.getLogger(__name__)

_SOURCE = "东方财富 push2（a-stock-data 适配）"
_ATTRIBUTION = "third_party/a-stock-data (Apache-2.0)"

_MOCK_TILES: list[dict[str, Any]] = [
    {"board_name": "半导体", "pct_change": 3.42, "turnover_amount": 84200000000, "leader": "寒武纪", "leader_change": 8.76},
    {"board_name": "白酒", "pct_change": -0.85, "turnover_amount": 62100000000, "leader": "贵州茅台", "leader_change": -0.42},
    {"board_name": "电池", "pct_change": 1.28, "turnover_amount": 59800000000, "leader": "宁德时代", "leader_change": 2.18},
    {"board_name": "光学光电子", "pct_change": 2.91, "turnover_amount": 45600000000, "leader": "京东方A", "leader_change": 3.55},
    {"board_name": "证券", "pct_change": 0.64, "turnover_amount": 43200000000, "leader": "中信证券", "leader_change": 0.88},
    {"board_name": "医疗器械", "pct_change": -1.12, "turnover_amount": 38900000000, "leader": "迈瑞医疗", "leader_change": -0.95},
    {"board_name": "汽车零部件", "pct_change": 1.76, "turnover_amount": 36500000000, "leader": "比亚迪", "leader_change": 1.44},
    {"board_name": "通信设备", "pct_change": 2.35, "turnover_amount": 34100000000, "leader": "中兴通讯", "leader_change": 2.02},
    {"board_name": "电力", "pct_change": 0.22, "turnover_amount": 31800000000, "leader": "长江电力", "leader_change": 0.15},
    {"board_name": "银行", "pct_change": -0.31, "turnover_amount": 30500000000, "leader": "招商银行", "leader_change": -0.28},
]


def _trade_date_label() -> str:
    return resolve_default_trade_date()


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
    **_extra: Any,
) -> dict[str, Any]:
    """Return industry-board heatmap tiles sized by turnover (demo fallback on failure)."""
    limit = max(min(int(board_limit or 30), 50), 5)
    if board_kind.strip() and board_kind.strip() != "industry":
        return {
            "tool": "sector_heatmap_lookup",
            "board_kind": board_kind,
            "board_limit": limit,
            "trade_date": _trade_date_label(),
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
            "trade_date": _trade_date_label(),
            "tiles": tiles,
            "tile_count": len(tiles),
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": False,
            "notes": "行业板块热力图：方块面积按成交额缩放，颜色按涨跌幅着色",
            "attribution": _ATTRIBUTION,
        }
    except Exception as exc:
        logger.warning("sector_heatmap_lookup failed, using mock fallback: %s", exc)
        mock_tiles = _normalize_tiles(
            [
                {
                    "board_name": item["board_name"],
                    "change_pct": item["pct_change"],
                    "turnover_amount": item["turnover_amount"],
                    "leader": item["leader"],
                    "leader_change": item["leader_change"],
                }
                for item in _MOCK_TILES[:limit]
            ]
        )
        return {
            "tool": "sector_heatmap_lookup",
            "board_kind": "industry",
            "board_limit": limit,
            "trade_date": _trade_date_label(),
            "tiles": mock_tiles,
            "tile_count": len(mock_tiles),
            "source": "本地 demo 行业板块截面",
            "is_mock": True,
            "fallback_used": True,
            "fallback_reason": str(exc),
            "notes": "行业板块热力图（降级 demo）；方块面积按成交额缩放",
            "attribution": _ATTRIBUTION,
        }
