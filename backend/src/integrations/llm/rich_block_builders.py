"""Construct frontend-compatible rich_block payloads from tool results."""

from __future__ import annotations

from typing import Any


def build_calculator_rich_payload(tool_result: dict[str, Any]) -> dict[str, Any]:
    """Map local_return_calculator output to CalculatorPayload (fields + results)."""
    buy_price = float(tool_result.get("buy_price") or 0)
    sell_price = float(tool_result.get("sell_price") or tool_result.get("target_price") or 0)
    share_count = int(tool_result.get("share_count") or 1000)
    fee_rate = float(tool_result.get("fee_rate") or 0.03)
    return_pct = tool_result.get("return_pct")
    net_profit = tool_result.get("net_profit")
    cost = buy_price * share_count
    return {
        "fields": [
            {"key": "buy_price", "label": "买入价", "value": buy_price, "unit": "元"},
            {"key": "target_price", "label": "情景价", "value": sell_price, "unit": "元"},
            {"key": "share_count", "label": "持仓数量", "value": share_count, "unit": "股"},
            {"key": "fee_rate", "label": "估算费率", "value": fee_rate, "unit": "%"},
        ],
        "results": [
            {
                "key": "return_rate",
                "label": "收益率",
                "value": f"{float(return_pct):.2f}%" if return_pct is not None else "—",
            },
            {
                "key": "profit_amount",
                "label": "预估盈亏",
                "value": f"{float(net_profit):.2f} 元" if net_profit is not None else "—",
            },
            {
                "key": "cost_amount",
                "label": "测算成本",
                "value": f"{cost:.2f} 元",
            },
        ],
        "formula": str(tool_result.get("formula", "")),
    }


def build_sector_heatmap_payload(tool_result: dict[str, Any]) -> dict[str, Any]:
    """Map sector_heatmap_lookup output to frontend SectorHeatmapPayload."""
    tiles = tool_result.get("tiles")
    if not isinstance(tiles, list):
        tiles = []
    normalized: list[dict[str, Any]] = []
    for item in tiles:
        if not isinstance(item, dict):
            continue
        name = str(item.get("board_name", "")).strip()
        if not name:
            continue
        normalized.append(
            {
                "board_name": name,
                "board_code": str(item.get("board_code", "")),
                "pct_change": float(item.get("pct_change") or 0.0),
                "turnover_amount": float(item.get("turnover_amount") or 0.0),
                "leader": str(item.get("leader", "")),
                "leader_change": item.get("leader_change"),
                "up_count": int(item.get("up_count") or 0),
                "down_count": int(item.get("down_count") or 0),
            }
        )
    return {
        "board_kind": str(tool_result.get("board_kind", "industry")),
        "trade_date": str(tool_result.get("trade_date", "")),
        "tiles": normalized,
        "size_by": "turnover_amount",
    }
