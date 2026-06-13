"""Eastmoney global news client (7x24)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from .eastmoney_client import UA, em_get

FAST_NEWS_URL = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"


def fetch_global_news(*, page_size: int = 50) -> list[dict[str, Any]]:
    """Fetch Eastmoney 7x24 global finance headlines."""
    params = {
        "client": "web",
        "biz": "web_724",
        "fastColumn": "102",
        "sortEnd": "",
        "pageSize": str(page_size),
        "req_trace": str(uuid.uuid4()),
    }
    response = em_get(
        FAST_NEWS_URL,
        params=params,
        headers={"User-Agent": UA, "Referer": "https://kuaixun.eastmoney.com/"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    rows: list[dict[str, Any]] = []
    for item in payload.get("data", {}).get("fastNewsList", []) or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "title": str(item.get("title", "")),
                "summary": str(item.get("summary", ""))[:300],
                "time": str(item.get("showTime", "")),
                "source": "东方财富全球资讯",
            }
        )
    return rows


def filter_news_by_keyword(news: list[dict[str, Any]], keyword: str) -> list[dict[str, Any]]:
    """Keep news items whose title/summary contains keyword."""
    needle = keyword.strip()
    if not needle:
        return news[:10]
    matched: list[dict[str, Any]] = []
    for item in news:
        haystack = f"{item.get('title', '')} {item.get('summary', '')}"
        if needle in haystack:
            matched.append(item)
    return matched


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()
