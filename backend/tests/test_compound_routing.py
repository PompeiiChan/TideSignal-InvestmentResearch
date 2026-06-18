"""Tests for compound stock + data query routing."""

from __future__ import annotations

from backend.src.integrations.langgraph.routing import route_after_evidence_merge
from backend.src.services.compound_routing import (
    enrich_slots_for_compound,
    extract_industry_label,
    resolve_compound_route_targets,
)

PET_QUERY = (
    "宠物行业是否值得看好？整体的逻辑是什么？有哪些分类值得重点关注？"
    "哪些公司是可以关注的？然后最近市场的热度怎么样？"
)


def test_resolve_compound_route_targets_pet_industry() -> None:
    targets = resolve_compound_route_targets(PET_QUERY, intent_id="stock_analysis")
    assert targets == ["stock_analysis_agent", "data_query_agent"]


def test_resolve_compound_route_targets_with_candidate_intents() -> None:
    targets = resolve_compound_route_targets(
        "白酒行业逻辑如何？最近成交活跃吗？",
        intent_id="stock_analysis",
        candidate_intents=[
            {"intent_id": "stock_analysis", "confidence": 0.9},
            {"intent_id": "data_query", "confidence": 0.8},
        ],
    )
    assert targets == ["stock_analysis_agent", "data_query_agent"]


def test_resolve_compound_route_targets_skips_prediction() -> None:
    assert resolve_compound_route_targets("预测明天涨跌", intent_id="prediction_request") is None


def test_extract_industry_label() -> None:
    assert extract_industry_label(PET_QUERY, {}) == "宠物行业"


def test_enrich_slots_for_compound() -> None:
    slots = enrich_slots_for_compound(PET_QUERY, {})
    assert slots["industry"] == "宠物行业"
    assert slots["metric"] == "涨幅排行"
    assert slots["time_range"] == "近一交易日"


def test_route_after_evidence_merge_compound_skips_gap_loop() -> None:
    state = {
        "multi_agent_mode": True,
        "route_target": "stock_analysis_agent",
        "multi_agent_stock_phase_done": False,
    }
    assert route_after_evidence_merge(state) == "multi_agent_handoff"


def test_route_after_evidence_merge_data_phase_goes_quality() -> None:
    state = {
        "multi_agent_mode": True,
        "route_target": "data_query_agent",
        "multi_agent_stock_phase_done": True,
    }
    assert route_after_evidence_merge(state) == "quality_check"
