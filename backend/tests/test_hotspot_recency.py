"""Tests for hotspot time-aware evidence routing."""

from __future__ import annotations

from datetime import date

from src.agents.nodes.routing_decision import build_execution_plan
from src.services.hotspot_recency import (
    build_hotspot_execution_plan,
    classify_hotspot_evidence_mode,
)


def test_recent_query_uses_api_primary() -> None:
    mode, reason = classify_hotspot_evidence_mode(
        "机器人板块本周为什么突然这么火？",
        {"topic": "机器人"},
        current_date=date(2026, 6, 13),
    )
    assert mode == "api_primary"
    assert "近期" in reason or "接口" in reason


def test_may_retrospective_uses_rag_primary() -> None:
    mode, _reason = classify_hotspot_evidence_mode(
        "5月A股市场热点月度复盘，主线是什么？",
        {"time_range": "2026-05"},
        current_date=date(2026, 6, 13),
    )
    assert mode == "rag_primary"


def test_current_month_when_kb_stale_uses_api_primary() -> None:
    mode, reason = classify_hotspot_evidence_mode(
        "6月有什么概念在炒？",
        {"time_range": "2026-06"},
        current_date=date(2026, 6, 13),
    )
    assert mode == "api_primary"
    assert "2026-06-11" in reason or "滞后" in reason


def test_build_hotspot_plan_api_primary_skips_monthly_rag() -> None:
    plan = build_hotspot_execution_plan(
        "最近半导体为什么涨",
        {"topic": "半导体"},
        current_date=date(2026, 6, 13),
    )
    assert plan["hotspot_evidence_mode"] == "api_primary"
    assert plan["retrieval_config"]["strategy"] == "hotspot_industry_only"
    assert plan["tool_params_defaults"]["news_limit"] >= 40


def test_build_hotspot_plan_rag_primary_uses_dual() -> None:
    plan = build_hotspot_execution_plan(
        "5月热点收官复盘",
        {"time_range": "2026-05"},
        current_date=date(2026, 6, 13),
    )
    assert plan["hotspot_evidence_mode"] == "rag_primary"
    assert plan["retrieval_config"]["strategy"] == "hotspot_dual"


def test_routing_decision_hotspot_recent_query() -> None:
    plan = build_execution_plan(
        "hotspot_agent",
        slots={"topic": "机器人"},
        query="今天盘面机器人在炒什么？",
    )
    assert plan["hotspot_evidence_mode"] == "api_primary"
    assert plan["retrieval_config"]["strategy"] == "hotspot_industry_only"
