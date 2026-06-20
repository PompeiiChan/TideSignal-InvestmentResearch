"""Tests for template short-circuit assembly."""

from __future__ import annotations

from backend.src.agents.assembly.template import try_template_assembly
from backend.src.integrations.langgraph.state import AgentState
from backend.src.services.message_sanitizer import ensure_public_risk_notice


def test_template_heatmap_includes_risk_notice() -> None:
    state: AgentState = {
        "normalized_query": "行业板块热力图",
        "evidence_pack": {
            "tool_result": {
                "sector_heatmap_lookup": {
                    "trade_date": "2026-06-18",
                    "tiles": [
                        {"board_name": "半导体", "pct_change": 2.5, "turnover_amount": 100},
                        {"board_name": "白酒", "pct_change": -1.2, "turnover_amount": 80},
                    ],
                }
            }
        },
        "rag_hits": [],
    }
    body = try_template_assembly(state)
    assert body
    assert "热力图" in body
    assert "不构成投资建议" in body
    assert body == ensure_public_risk_notice(body)


def test_template_ranking_simple_query() -> None:
    state: AgentState = {
        "normalized_query": "今天涨幅前10的行业板块",
        "evidence_pack": {
            "tool_result": {
                "market_ranking_lookup": {
                    "tool": "market_ranking_lookup",
                    "ranking_mode": "industry_boards",
                    "trade_date": "2026-06-18",
                    "rows": [{"rank": 1, "stock_name": "半导体", "pct_change": 3.2}],
                }
            }
        },
        "rag_hits": [],
    }
    body = try_template_assembly(state)
    assert body
    assert "半导体" in body
    assert "排行表" in body


def test_template_skips_board_stocks_complex_ranking() -> None:
    state: AgentState = {
        "normalized_query": "半导体成分股涨幅",
        "evidence_pack": {
            "tool_result": {
                "market_ranking_lookup": {
                    "tool": "market_ranking_lookup",
                    "ranking_mode": "board_stocks",
                    "rows": [{"rank": 1, "stock_name": "某股", "pct_change": 3.2}],
                }
            }
        },
        "rag_hits": [],
    }
    assert try_template_assembly(state) is None
