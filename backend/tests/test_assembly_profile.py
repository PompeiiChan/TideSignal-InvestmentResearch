"""Tests for resolve_assembly_profile."""

from __future__ import annotations

from backend.src.agents.assembly.profile import AssemblyProfile, resolve_assembly_profile
from backend.src.integrations.langgraph.state import AgentState


def _state(**overrides: object) -> AgentState:
    base: AgentState = {
        "normalized_query": "测试",
        "response_kind": "data",
        "evidence_pack": {"tool_result": {}},
        "rag_hits": [],
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


def test_profile_template_skip_for_pure_ranking() -> None:
    state = _state(
        normalized_query="今天涨幅前10的行业板块",
        response_kind="data",
        evidence_pack={
            "tool_result": {
                "market_ranking_lookup": {
                    "tool": "market_ranking_lookup",
                    "ranking_mode": "industry_boards",
                    "rows": [{"rank": 1, "stock_name": "半导体", "pct_change": 2.1}],
                }
            }
        },
    )
    assert resolve_assembly_profile(state) == AssemblyProfile.TEMPLATE_SKIP


def test_profile_heatmap_primary_when_not_template_only() -> None:
    state = _state(
        normalized_query="行业板块热力图",
        response_kind="data",
        evidence_pack={
            "tool_result": {
                "sector_heatmap_lookup": {
                    "tool": "sector_heatmap_lookup",
                    "tiles": [{"board_name": "半导体", "pct_change": 1.2}],
                },
                "market_ranking_lookup": {
                    "tool": "market_ranking_lookup",
                    "rows": [{"rank": 1, "stock_name": "半导体"}],
                },
            }
        },
    )
    assert resolve_assembly_profile(state) == AssemblyProfile.HEATMAP_PRIMARY


def test_profile_data_ranking_only() -> None:
    state = _state(
        normalized_query="半导体成分股涨幅",
        response_kind="data",
        evidence_pack={
            "tool_result": {
                "market_ranking_lookup": {
                    "tool": "market_ranking_lookup",
                    "ranking_mode": "board_stocks",
                    "rows": [{"rank": 1, "stock_name": "某股", "pct_change": 2.1}],
                }
            }
        },
    )
    assert resolve_assembly_profile(state) == AssemblyProfile.DATA_RANKING_ONLY


def test_profile_hotspot_api_primary() -> None:
    state = _state(
        response_kind="hotspot",
        evidence_pack={"hotspot_evidence_mode": "api_primary", "tool_result": {}},
    )
    assert resolve_assembly_profile(state) == AssemblyProfile.HOTSPOT_API_PRIMARY


def test_profile_stock_narrative_without_financial_tool() -> None:
    state = _state(
        response_kind="stock",
        evidence_pack={"stock_narrative_mode": True, "tool_result": {}},
    )
    assert resolve_assembly_profile(state) == AssemblyProfile.STOCK_NARRATIVE


def test_profile_stock_full_with_financial_tool() -> None:
    state = _state(
        response_kind="stock",
        evidence_pack={
            "stock_narrative_mode": True,
            "tool_result": {
                "mock_financial_profile_lookup": {
                    "found": True,
                    "profile": {
                        "company_id": "c1",
                        "stock_name": "宁德时代",
                        "revenue": "100",
                        "net_profit": "10",
                    },
                }
            },
        },
    )
    assert resolve_assembly_profile(state) == AssemblyProfile.STOCK_FULL


def test_profile_compound() -> None:
    state = _state(response_kind="compound_stock_data")
    assert resolve_assembly_profile(state) == AssemblyProfile.COMPOUND
