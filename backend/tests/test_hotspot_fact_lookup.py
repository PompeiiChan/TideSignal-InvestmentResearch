"""Tests for hotspot fact lookup tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.tools.hotspot_fact_lookup import lookup_hotspot_facts


@patch("src.agents.tools.hotspot_fact_lookup.fetch_cninfo_announcements")
@patch("src.agents.tools.hotspot_fact_lookup.fetch_global_news")
def test_lookup_hotspot_facts_merges_news_and_announcements(
    mock_news: MagicMock,
    mock_ann: MagicMock,
) -> None:
    mock_news.return_value = [
        {"title": "发改委部署机器人产业", "summary": "政策推动智能制造", "time": "2026-06-12", "source": "东财"},
        {"title": "无关新闻", "summary": "其他", "time": "2026-06-12", "source": "东财"},
    ]
    mock_ann.return_value = [
        {
            "code": "300024",
            "title": "关于机器人业务进展的公告",
            "type": "临时公告",
            "date": "2026-06-10",
            "url": "https://example.com",
        }
    ]

    result = lookup_hotspot_facts(topic="机器人", stock_codes="300024")

    assert result["is_mock"] is False
    assert result["fallback_used"] is False
    assert result["fact_count"] >= 2
    kinds = {item["kind"] for item in result["facts"]}
    assert "news" in kinds
    assert "announcement" in kinds


@patch("src.agents.tools.hotspot_fact_lookup.fetch_global_news")
def test_lookup_hotspot_facts_empty_on_failure(mock_news: MagicMock) -> None:
    mock_news.side_effect = RuntimeError("blocked")

    result = lookup_hotspot_facts(topic="半导体")

    assert result["fallback_used"] is True
    assert result["fact_count"] == 0
