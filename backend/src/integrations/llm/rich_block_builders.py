"""Construct frontend-compatible rich_block payloads from tool results."""

from __future__ import annotations

from typing import Any

from ...services.citation_catalog import (
    CitationCatalog,
    resolve_doc_citation_index,
    valuation_citation_index,
)


def build_calculator_rich_payload(tool_result: dict[str, Any]) -> dict[str, Any]:
    """Map local_return_calculator output to CalculatorPayload (fields + results)."""
    buy_price = float(tool_result.get("buy_price") or 0)
    sell_price = float(tool_result.get("sell_price") or tool_result.get("target_price") or 0)
    share_count = int(tool_result.get("share_count") or 100)
    return_pct = tool_result.get("return_pct")
    net_profit = tool_result.get("net_profit")
    cost = buy_price * share_count
    payload: dict[str, Any] = {
        "fields": [
            {"key": "buy_price", "label": "买入价", "value": buy_price, "unit": "元"},
            {"key": "target_price", "label": "情景价", "value": sell_price, "unit": "元"},
            {"key": "share_count", "label": "持仓数量", "value": share_count, "unit": "股"},
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
    assumption = str(tool_result.get("assumption", "")).strip()
    if assumption:
        payload["assumption"] = assumption
    return payload


def _source_ref(source: dict[str, Any], citation_index: int | None = None) -> dict[str, Any]:
    return {
        "title": str(source.get("title", "")),
        "time_period": "",
        "excerpt": "",
        "origin": str(source.get("origin", "local_kb")),
        "citation_index": citation_index,
    }


def build_scenario_calculator_rich_payload(
    calc_tool: dict[str, Any],
    forecast_tool: dict[str, Any] | None,
    catalog: CitationCatalog,
) -> dict[str, Any]:
    """Map scenario return tools to ScenarioCalculatorPayload with citation indices."""
    from ...agents.tools.return_calculator import compute_return

    buy_price = float(calc_tool.get("buy_price") or 0)
    share_count = int(calc_tool.get("share_count") or 100)
    fee_rate = float(calc_tool.get("fee_rate") or 0.0003)
    stock_name = str(calc_tool.get("stock_name", ""))

    buy_citation = valuation_citation_index(catalog)
    buy_source = _source_ref(
        {"title": "实时行情/估值", "origin": "tencent_quote_api"},
        buy_citation,
    )

    raw_scenarios: dict[str, Any] = {}
    scenario_order: list[str] = []
    if isinstance(forecast_tool, dict) and forecast_tool.get("found"):
        raw_scenarios = forecast_tool.get("scenarios") or {}
        scenario_order = list(forecast_tool.get("scenario_order") or [])
    if not raw_scenarios:
        fallback = calc_tool.get("forecast_scenarios")
        if isinstance(fallback, dict):
            raw_scenarios = fallback
    if not scenario_order:
        scenario_order = [key for key in ("bear", "base", "bull") if key in raw_scenarios]
        scenario_order.extend(key for key in raw_scenarios if key not in scenario_order)

    scenarios_out: list[dict[str, Any]] = []
    for key in scenario_order:
        scenario = raw_scenarios.get(key)
        if not isinstance(scenario, dict):
            continue
        target_price = float(scenario.get("target_price") or 0)
        if target_price <= 0:
            continue
        raw_source = scenario.get("source")
        source: dict[str, Any] = raw_source if isinstance(raw_source, dict) else {}
        doc_id = str(source.get("doc_id", ""))
        citation_index = resolve_doc_citation_index(catalog, doc_id) if doc_id else None
        ret = compute_return(
            buy_price=buy_price,
            sell_price=target_price,
            share_count=share_count,
            fee_rate=fee_rate,
        )
        item: dict[str, Any] = {
            "key": key,
            "label": str(scenario.get("label", key)),
            "target_price": target_price,
            "assumption": str(scenario.get("assumption", "")),
            "return_pct": ret.get("return_pct"),
            "net_profit": ret.get("net_profit"),
            "source": _source_ref(source, citation_index),
        }
        if scenario.get("eps") is not None:
            item["eps"] = float(scenario["eps"])
        if scenario.get("pe") is not None:
            item["pe"] = float(scenario["pe"])
        if scenario.get("forecast_year") is not None:
            item["forecast_year"] = int(scenario["forecast_year"])
        scenarios_out.append(item)

    active = "base" if any(item["key"] == "base" for item in scenarios_out) else (
        scenarios_out[0]["key"] if scenarios_out else "base"
    )
    active_item = next((item for item in scenarios_out if item["key"] == active), None)

    return {
        "stock_name": stock_name,
        "buy_price": buy_price,
        "buy_price_source": buy_source,
        "share_count": share_count,
        "fee_rate": fee_rate,
        "active_scenario": active,
        "scenarios": scenarios_out,
        "formula": str(calc_tool.get("formula") or forecast_tool.get("formula") if isinstance(forecast_tool, dict) else ""),
        "reference_year": (
            forecast_tool.get("reference_year") if isinstance(forecast_tool, dict) else None
        ),
        "low_coverage": (
            forecast_tool.get("low_coverage") if isinstance(forecast_tool, dict) else None
        ),
        "data_origin": (
            forecast_tool.get("data_origin") if isinstance(forecast_tool, dict) else ""
        ),
        "active_return_pct": active_item.get("return_pct") if active_item else calc_tool.get("return_pct"),
        "active_net_profit": active_item.get("net_profit") if active_item else calc_tool.get("net_profit"),
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
