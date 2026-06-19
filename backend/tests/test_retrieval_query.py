"""Tests for rule-based retrieval query builder (T-014)."""

from __future__ import annotations

from backend.src.services.retrieval_query import build_retrieval_query


def test_multiturn_followup_with_stock_name() -> None:
    retrieval_query, method, changed = build_retrieval_query(
        "它一季报怎么样",
        intent_id="stock_analysis",
        slots={"stock_name": "宁德时代"},
    )
    assert "宁德时代" in retrieval_query
    assert "一季报" in retrieval_query
    assert changed is True
    assert method in {"rule_slots", "rule_multiturn"}


def test_explicit_query_passthrough() -> None:
    query = "罗莱生活 2026 年一季报"
    retrieval_query, method, changed = build_retrieval_query(
        query,
        intent_id="stock_analysis",
        slots={"stock_name": "罗莱生活", "time_range": "2026Q1"},
    )
    assert retrieval_query == query
    assert method == "passthrough"
    assert changed is False


def test_short_query_without_stock_passthrough() -> None:
    query = "一季报呢"
    retrieval_query, method, changed = build_retrieval_query(
        query,
        intent_id="stock_analysis",
        slots={},
    )
    assert retrieval_query == query
    assert method == "passthrough"
    assert changed is False


def test_time_range_2026q1_in_rewrite() -> None:
    retrieval_query, method, changed = build_retrieval_query(
        "它怎么样",
        intent_id="stock_analysis",
        slots={"stock_name": "宁德时代", "time_range": "2026Q1"},
    )
    assert "2026" in retrieval_query
    assert "一季报" in retrieval_query
    assert changed is True
    assert method in {"rule_slots", "rule_multiturn"}


def test_hotspot_slot_concatenation() -> None:
    retrieval_query, method, changed = build_retrieval_query(
        "最近怎么样",
        intent_id="hotspot_analysis",
        slots={"topic": "机器人", "industry": "智能制造", "time_range": "2026Q1"},
    )
    assert "机器人" in retrieval_query
    assert "智能制造" in retrieval_query
    assert "2026" in retrieval_query
    assert "一季报" in retrieval_query
    assert changed is True
    assert method == "rule_slots"
