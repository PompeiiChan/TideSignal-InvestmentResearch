"""Hotspot signal lookup: THS live attribution with KB material fallback."""

from __future__ import annotations

import logging
from typing import Any

from ...integrations.market_data.ths_client import fetch_ths_hot_stocks
from .mock_hotspot_material_lookup import lookup_hotspot_material

logger = logging.getLogger(__name__)

_SOURCE_LIVE = "同花顺热点归因（zx.10jqka.com.cn）"
_SOURCE_KB = "知识库热点月报整理摘要"
_ATTRIBUTION = "third_party/a-stock-data (Apache-2.0)"


def lookup_hotspot_signal(
    *,
    topic: str = "",
    industry: str = "",
    event: str = "",
    time_range: str = "",
    trade_date: str = "",
    signal_limit: int = 10,
    **_extra: Any,
) -> dict[str, Any]:
    """Return live hotspot signals; fall back to curated KB materials on failure."""
    keyword = topic or industry or event
    limit = max(int(signal_limit or 10), 1)

    try:
        live = fetch_ths_hot_stocks(
            trade_date=trade_date or None,
            keyword=keyword,
            limit=limit,
        )
        stocks = live.get("stocks") or []
        return {
            "tool": "hotspot_signal_lookup",
            "signal_mode": "ths_live",
            "topic": keyword or "市场热点",
            "time_range": time_range or live.get("trade_date", ""),
            "trade_date": live.get("trade_date"),
            "stocks": stocks,
            "stock_count": len(stocks),
            "themes": live.get("themes") or [],
            "total_available": live.get("total_available", 0),
            "matched_count": live.get("matched_count", 0),
            "source": _SOURCE_LIVE,
            "is_mock": False,
            "fallback_used": False,
            "timeliness": "当日盘面信号（同花顺人工题材标签）",
            "confidence_note": "题材标签为现象层归因，须与 RAG 月报交叉验证",
            "notes": "强势股 + reason 标签；深度归因仍以知识库 RAG 为主",
            "attribution": _ATTRIBUTION,
        }
    except Exception as exc:
        logger.warning("hotspot_signal_lookup failed, using KB material fallback: %s", exc)
        kb = lookup_hotspot_material(
            topic=topic,
            industry=industry,
            event=event,
            time_range=time_range or "2026-06",
        )
        return {
            "tool": "hotspot_signal_lookup",
            "signal_mode": "kb_material",
            "topic": kb.get("topic", keyword or "市场热点"),
            "time_range": kb.get("time_range", time_range),
            "trade_date": None,
            "stocks": [],
            "stock_count": 0,
            "themes": [item.get("topic", "") for item in kb.get("materials", []) if item.get("topic")],
            "materials": kb.get("materials", []),
            "material_count": kb.get("material_count", 0),
            "source": _SOURCE_KB,
            "is_mock": False,
            "fallback_used": True,
            "fallback_reason": str(exc),
            "timeliness": "月报/复盘口径，时效滞后于当日盘面",
            "confidence_note": "知识库整理素材，置信度高，须写明 time_period",
            "notes": kb.get("notes", ""),
            "attribution": _ATTRIBUTION,
        }
