"""Hotspot assistant acceptance helpers (structural gates for user QA)."""

from __future__ import annotations

import re

import pytest
from src.agents.nodes.routing_decision import build_execution_plan
from src.integrations.llm.prompts.agents.hotspot import HOTSPOT_AGENT_PROMPT_BASE
from src.integrations.llm.prompts.assembly import ASSEMBLY_HOTSPOT_PROMPT_BASE

REQUIRED_ASSEMBLY_SECTIONS = ("事实支撑", "预期博弈", "纯叙事风险")


def test_hotspot_execution_plan_has_dual_tools_and_rag_strategy() -> None:
    plan = build_execution_plan(
        "hotspot_agent",
        slots={"topic": "机器人"},
        query="5月机器人板块月度复盘",
    )
    assert plan["needs_rag"] is True
    assert plan["needs_tool"] is True
    assert "hotspot_fact_lookup" in plan["tool_names"]
    assert "hotspot_signal_lookup" not in plan["tool_names"]
    assert plan["hotspot_evidence_mode"] == "rag_primary"
    assert plan["retrieval_config"].get("strategy") == "hotspot_dual"


def test_hotspot_prompts_require_credibility_sections() -> None:
    for section in REQUIRED_ASSEMBLY_SECTIONS:
        assert section in ASSEMBLY_HOTSPOT_PROMPT_BASE
    assert "hotspot_fact_lookup" in HOTSPOT_AGENT_PROMPT_BASE
    assert "industry-reports" in HOTSPOT_AGENT_PROMPT_BASE


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            "### 事实支撑\n- 政策已发布\n### 预期博弈\n- 订单预期\n### 纯叙事风险\n- 拥挤度高",
            True,
        ),
        ("只有热点描述，没有成色三段", False),
    ],
)
def test_hotspot_response_contains_credibility_sections(content: str, expected: bool) -> None:
    """Gate for manual/LLM output review: all three sections must appear."""
    ok = all(re.search(rf"###\s*{section}", content) for section in REQUIRED_ASSEMBLY_SECTIONS)
    assert ok is expected
