"""Hotspot hard-fact lookup: global news + cninfo announcements."""

from __future__ import annotations

import logging
import re
from typing import Any

from ...integrations.market_data.cninfo_client import fetch_cninfo_announcements
from ...integrations.market_data.news_client import fetch_global_news, filter_news_by_keyword

logger = logging.getLogger(__name__)

_SOURCE = "东财全球资讯 + 巨潮公告（a-stock-data 适配）"
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


def _announcement_matches(announcement: dict[str, Any], keywords: list[str]) -> bool:
    if not keywords:
        return True
    haystack = str(announcement.get("title", ""))
    return any(keyword in haystack for keyword in keywords)


def lookup_hotspot_facts(
    *,
    topic: str = "",
    industry: str = "",
    event: str = "",
    stock_codes: str = "",
    news_limit: int = 30,
    announcement_limit: int = 8,
    **_extra: Any,
) -> dict[str, Any]:
    """Fetch recent news and optional stock announcements for hotspot fact-checking."""
    keywords = _split_keywords(topic, industry, event)
    primary_keyword = keywords[0] if keywords else ""
    facts: list[dict[str, Any]] = []

    try:
        news_items = fetch_global_news(page_size=max(news_limit, 20))
        matched_news = filter_news_by_keyword(news_items, primary_keyword) if primary_keyword else news_items[:8]
        for item in matched_news[:8]:
            facts.append(
                {
                    "kind": "news",
                    "title": item.get("title", ""),
                    "summary": item.get("summary", ""),
                    "time": item.get("time", ""),
                    "source": item.get("source", "东方财富全球资讯"),
                }
            )

        codes = [code.strip().zfill(6) for code in re.split(r"[,，\s]+", stock_codes) if code.strip()]
        for code in codes[:3]:
            announcements = fetch_cninfo_announcements(code, page_size=announcement_limit)
            for ann in announcements:
                if keywords and not _announcement_matches(ann, keywords):
                    continue
                facts.append(
                    {
                        "kind": "announcement",
                        "code": code,
                        "title": ann.get("title", ""),
                        "type": ann.get("type", ""),
                        "time": ann.get("date", ""),
                        "source": "巨潮资讯",
                        "url": ann.get("url", ""),
                    }
                )

        return {
            "tool": "hotspot_fact_lookup",
            "topic": primary_keyword or topic or industry or "市场热点",
            "keywords": keywords,
            "facts": facts[:15],
            "fact_count": len(facts[:15]),
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": False,
            "timeliness": "近实时快讯/公告",
            "confidence_note": "事实层证据，用于支撑或质疑题材叙事；须与 RAG 月报交叉验证",
            "notes": "未匹配到关键词时仅返回少量通用快讯；公告需提供 stock_codes",
            "attribution": _ATTRIBUTION,
        }
    except Exception as exc:
        logger.warning("hotspot_fact_lookup failed: %s", exc)
        return {
            "tool": "hotspot_fact_lookup",
            "topic": primary_keyword or topic or industry or "市场热点",
            "keywords": keywords,
            "facts": [],
            "fact_count": 0,
            "source": _SOURCE,
            "is_mock": False,
            "fallback_used": True,
            "fallback_reason": str(exc),
            "timeliness": "不可用",
            "confidence_note": "事实层暂不可用，请依赖 RAG 月报与知识库素材",
            "notes": "东财资讯或巨潮公告请求失败",
            "attribution": _ATTRIBUTION,
        }
