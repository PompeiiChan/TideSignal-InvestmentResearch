"""Stock evidence API lookup: cninfo announcements + Eastmoney news for supplement fetch."""

from __future__ import annotations

import logging
import re
from typing import Any

from ...integrations.market_data.cninfo_client import fetch_cninfo_announcements
from ...integrations.market_data.news_client import fetch_global_news, filter_news_by_keyword
from ...integrations.market_data.stock_code_resolver import resolve_stock_code

logger = logging.getLogger(__name__)

_SOURCE = "巨潮公告 + 东财全球资讯（a-stock-data 适配）"
_ATTRIBUTION = "third_party/a-stock-data (Apache-2.0)"


def _split_keywords(*parts: str) -> list[str]:
    keywords: list[str] = []
    for part in parts:
        text = part.strip()
        if not text:
            continue
        for token in re.split(r"[,，、/|+\s]+", text):
            token = token.strip()
            if len(token) >= 2 and token not in keywords:
                keywords.append(token)
    return keywords[:5]


def lookup_stock_evidence_api(
    *,
    stock_name: str = "",
    stock_code: str = "",
    keywords: str = "",
    news_limit: int = 30,
    announcement_limit: int = 10,
    **_extra: Any,
) -> dict[str, Any]:
    """Fetch recent announcements and news for a single stock (evidence gap supplement)."""
    resolved_code, resolved_name = resolve_stock_code(stock_name, stock_code)
    display_name = resolved_name or stock_name.strip() or resolved_code
    keyword_list = _split_keywords(keywords, display_name)
    primary_keyword = display_name or (keyword_list[0] if keyword_list else "")
    facts: list[dict[str, Any]] = []

    try:
        if resolved_code:
            announcements = fetch_cninfo_announcements(resolved_code, page_size=announcement_limit)
            for ann in announcements[:announcement_limit]:
                facts.append(
                    {
                        "kind": "announcement",
                        "code": resolved_code,
                        "title": ann.get("title", ""),
                        "type": ann.get("type", ""),
                        "time": ann.get("date", ""),
                        "source": "巨潮资讯",
                        "url": ann.get("url", ""),
                    }
                )

        if primary_keyword:
            news_items = fetch_global_news(page_size=max(news_limit, 20))
            matched_news = filter_news_by_keyword(news_items, primary_keyword)
            for item in matched_news[:6]:
                facts.append(
                    {
                        "kind": "news",
                        "title": item.get("title", ""),
                        "summary": item.get("summary", ""),
                        "time": item.get("time", ""),
                        "source": item.get("source", "东方财富全球资讯"),
                    }
                )

        return {
            "tool": "stock_evidence_api_lookup",
            "found": bool(facts),
            "stock_name": display_name,
            "stock_code": resolved_code,
            "keywords": keyword_list,
            "facts": facts[:12],
            "fact_count": len(facts[:12]),
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": False,
            "timeliness": "近实时公告/快讯",
            "confidence_note": "API 事实层证据，用于补充本地知识库未收录标的；须与结构化财报交叉验证",
            "notes": "公告依赖股票代码解析；资讯按公司名关键词过滤",
            "attribution": _ATTRIBUTION,
        }
    except Exception as exc:
        logger.warning("stock_evidence_api_lookup failed: %s", exc)
        return {
            "tool": "stock_evidence_api_lookup",
            "found": False,
            "stock_name": display_name,
            "stock_code": resolved_code,
            "keywords": keyword_list,
            "facts": [],
            "fact_count": 0,
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": True,
            "fallback_reason": str(exc),
            "timeliness": "不可用",
            "confidence_note": "API 证据暂不可用，请依赖结构化财报与本地知识库",
            "notes": "巨潮公告或东财资讯请求失败",
            "attribution": _ATTRIBUTION,
        }
