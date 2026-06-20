"""Tests for deduplicated assembly user prompt builder."""

from __future__ import annotations

import json

from backend.src.agents.assembly.prompt_builder import build_assembly_user_prompt
from backend.src.services.citation_catalog import CitationCatalog
from backend.src.services.system_time import SystemTimeContext


def _time_ctx() -> SystemTimeContext:
    return SystemTimeContext(current_date="2026-06-20", timezone="Asia/Shanghai", source="test")


def test_user_prompt_excludes_full_evidence_pack_json() -> None:
    huge_tool = {"rows": [{"rank": i, "stock_name": f"板块{i}", "pct_change": i} for i in range(50)]}
    evidence_pack = {
        "agent_summary": "解读行业涨幅",
        "analysis_dimensions": ["涨幅", "成交额"],
        "tool_result": {"market_ranking_lookup": huge_tool},
        "retrieved_chunks": [{"snippet": "不应重复出现"}],
        "hotspot_evidence_mode": "rag_primary",
    }
    citation_context = "【1】东财排行\nrows 摘要"
    parts = build_assembly_user_prompt(
        normalized_query="今天涨幅前10的行业板块",
        evidence_pack=evidence_pack,
        citation_context=citation_context,
        catalog=CitationCatalog(),
        conversation_context={"has_context": False},
        revision_suggestions=[],
        time_ctx=_time_ctx(),
    )
    prompt = parts.user_prompt
    assert "evidence_pack" not in prompt
    assert '"rows":' not in prompt or "【结构化引用与证据】" in prompt
    assert "【分析骨架】" in prompt
    assert "解读行业涨幅" in prompt
    assert citation_context in prompt
    assert json.dumps(huge_tool, ensure_ascii=False) not in prompt
    assert len(prompt) < 4000


def test_user_prompt_includes_meta_flags() -> None:
    parts = build_assembly_user_prompt(
        normalized_query="机构怎么看宁德时代",
        evidence_pack={
            "agent_summary": "机构观点",
            "scenario_return_mode": True,
            "stock_narrative_evidence_missing": False,
        },
        citation_context="consensus json",
        catalog=CitationCatalog(),
        conversation_context={"has_context": False},
        revision_suggestions=[],
        time_ctx=_time_ctx(),
    )
    assert "【元信息 flags】" in parts.user_prompt
    assert "scenario_return_mode" in parts.user_prompt
