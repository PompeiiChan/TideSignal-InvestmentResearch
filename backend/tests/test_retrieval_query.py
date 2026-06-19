"""Tests for rule-based retrieval query builder (T-014 / T-014-P2)."""

from __future__ import annotations

from backend.src.services.retrieval_query import build_retrieval_query


def test_multiturn_followup_with_stock_name() -> None:
    plan = build_retrieval_query(
        "它一季报怎么样",
        intent_id="stock_analysis",
        slots={"stock_name": "宁德时代"},
    )
    assert "宁德时代" in plan.retrieval_query
    assert "一季报" in plan.retrieval_query
    assert plan.changed is True
    assert plan.rewrite_method in {"rule_slots", "rule_multiturn"}
    assert plan.retrieval_queries == []


def test_explicit_query_passthrough() -> None:
    query = "罗莱生活 2026 年一季报"
    plan = build_retrieval_query(
        query,
        intent_id="stock_analysis",
        slots={"stock_name": "罗莱生活", "time_range": "2026Q1"},
    )
    assert plan.retrieval_query == query
    assert plan.rewrite_method == "passthrough"
    assert plan.changed is False
    assert plan.retrieval_queries == []


def test_short_query_without_stock_passthrough() -> None:
    query = "一季报呢"
    plan = build_retrieval_query(
        query,
        intent_id="stock_analysis",
        slots={},
    )
    assert plan.retrieval_query == query
    assert plan.rewrite_method == "passthrough"
    assert plan.changed is False


def test_time_range_2026q1_in_rewrite() -> None:
    plan = build_retrieval_query(
        "它怎么样",
        intent_id="stock_analysis",
        slots={"stock_name": "宁德时代", "time_range": "2026Q1"},
    )
    assert "2026" in plan.retrieval_query
    assert "一季报" in plan.retrieval_query
    assert plan.changed is True
    assert plan.rewrite_method in {"rule_slots", "rule_multiturn"}


def test_hotspot_slot_concatenation() -> None:
    plan = build_retrieval_query(
        "最近怎么样",
        intent_id="hotspot_analysis",
        slots={"topic": "机器人", "industry": "智能制造", "time_range": "2026Q1"},
    )
    assert "机器人" in plan.retrieval_query
    assert "智能制造" in plan.retrieval_query
    assert "2026" in plan.retrieval_query
    assert "一季报" in plan.retrieval_query
    assert plan.changed is True
    assert plan.rewrite_method == "rule_slots"


def test_haitian_fundamentals_passthrough() -> None:
    query = "海天味业基本面"
    plan = build_retrieval_query(
        query,
        intent_id="stock_analysis",
        slots={"stock_name": "海天味业", "analysis_dimension": "基本面"},
    )
    assert plan.retrieval_query == query
    assert "财报" not in plan.retrieval_query
    assert plan.rewrite_method == "rule_dimension_split"


def test_haitian_dimension_split() -> None:
    plan = build_retrieval_query(
        "海天味业基本面",
        intent_id="stock_analysis",
        slots={"stock_name": "海天味业", "analysis_dimension": "基本面"},
    )
    assert len(plan.retrieval_queries) >= 2
    joined = " ".join(plan.retrieval_queries)
    assert "财务" in joined or "营收" in joined
    assert "研报" in joined or "竞争力" in joined


def test_follow_up_still_rewrites() -> None:
    plan = build_retrieval_query(
        "它一季报怎么样",
        intent_id="stock_analysis",
        slots={"stock_name": "宁德时代"},
    )
    assert "宁德时代" in plan.retrieval_query
    assert "一季报" in plan.retrieval_query
    assert plan.changed is True


def test_luolai_explicit_passthrough() -> None:
    query = "罗莱生活 2026 年一季报"
    plan = build_retrieval_query(
        query,
        intent_id="stock_analysis",
        slots={"stock_name": "罗莱生活", "time_range": "2026Q1"},
    )
    assert plan.retrieval_query == query
    assert plan.rewrite_method == "passthrough"
    assert plan.changed is False
