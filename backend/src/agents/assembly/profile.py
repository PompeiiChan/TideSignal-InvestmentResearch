"""Assembly profile resolution for response_assembly performance tiers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from ...integrations.langgraph.state import AgentState
from ...services.citation_catalog import financial_tool_is_usable
from ...services.rag.models import RagHit
from ..heatmap_intent import wants_sector_heatmap
from .template import is_template_eligible


class AssemblyProfile(StrEnum):
    TEMPLATE_SKIP = "template_skip"
    HEATMAP_PRIMARY = "heatmap_primary"
    DATA_RANKING_ONLY = "data_ranking_only"
    DATA_CALCULATOR = "data_calculator"
    HOTSPOT_API_PRIMARY = "hotspot_api_primary"
    STOCK_NARRATIVE = "stock_narrative"
    COMPOUND = "compound"
    STOCK_FULL = "stock_full"
    DATA_DEFAULT = "data_default"
    HOTSPOT_DEFAULT = "hotspot_default"


PROFILE_MAX_TOKENS: dict[AssemblyProfile, int] = {
    AssemblyProfile.TEMPLATE_SKIP: 0,
    AssemblyProfile.HEATMAP_PRIMARY: 512,
    AssemblyProfile.DATA_RANKING_ONLY: 768,
    AssemblyProfile.DATA_CALCULATOR: 1024,
    AssemblyProfile.HOTSPOT_API_PRIMARY: 1536,
    AssemblyProfile.STOCK_NARRATIVE: 1536,
    AssemblyProfile.COMPOUND: 2048,
    AssemblyProfile.STOCK_FULL: 2048,
    AssemblyProfile.DATA_DEFAULT: 1536,
    AssemblyProfile.HOTSPOT_DEFAULT: 1536,
}


def _tool_result(state: AgentState) -> dict[str, Any]:
    evidence_pack = state.get("evidence_pack") or {}
    tool_result = evidence_pack.get("tool_result")
    return tool_result if isinstance(tool_result, dict) else {}


def _has_rag_hits(state: AgentState) -> bool:
    return bool(state.get("rag_hits"))


def _heatmap_has_tiles(tool_result: dict[str, Any]) -> bool:
    heatmap = tool_result.get("sector_heatmap_lookup")
    return isinstance(heatmap, dict) and bool(heatmap.get("tiles"))


def _ranking_only(tool_result: dict[str, Any], *, has_rag: bool) -> bool:
    if has_rag:
        return False
    ranking = tool_result.get("market_ranking_lookup")
    if not isinstance(ranking, dict) or not ranking.get("rows"):
        return False
    other_keys = {
        key
        for key in tool_result
        if key not in {"market_ranking_lookup"} and tool_result.get(key)
    }
    return not other_keys


def _calculator_only(tool_result: dict[str, Any], *, has_rag: bool) -> bool:
    if has_rag:
        return False
    calc = tool_result.get("local_return_calculator")
    if not isinstance(calc, dict):
        return False
    if calc.get("scenario_return_mode"):
        return False
    ranking = tool_result.get("market_ranking_lookup")
    if isinstance(ranking, dict) and ranking.get("rows"):
        return False
    other_keys = {
        key
        for key in tool_result
        if key not in {"local_return_calculator"} and tool_result.get(key)
    }
    return not other_keys


def resolve_assembly_profile(state: AgentState) -> AssemblyProfile:
    """Pick assembly tier from routing context and evidence shape."""
    if is_template_eligible(state):
        return AssemblyProfile.TEMPLATE_SKIP

    evidence_pack = state.get("evidence_pack") or {}
    response_kind = str(state.get("response_kind", "data"))
    query = str(state.get("normalized_query", "")).strip()
    tool_result = _tool_result(state)
    has_rag = _has_rag_hits(state)

    if response_kind == "compound_stock_data":
        return AssemblyProfile.COMPOUND

    if wants_sector_heatmap(query) and _heatmap_has_tiles(tool_result):
        return AssemblyProfile.HEATMAP_PRIMARY

    if response_kind in {"data", "calculator"}:
        if _ranking_only(tool_result, has_rag=has_rag):
            return AssemblyProfile.DATA_RANKING_ONLY
        if _calculator_only(tool_result, has_rag=has_rag):
            return AssemblyProfile.DATA_CALCULATOR
        return AssemblyProfile.DATA_DEFAULT

    if response_kind == "hotspot":
        if str(evidence_pack.get("hotspot_evidence_mode", "")) == "api_primary":
            return AssemblyProfile.HOTSPOT_API_PRIMARY
        return AssemblyProfile.HOTSPOT_DEFAULT

    if response_kind == "stock":
        narrative_mode = bool(evidence_pack.get("stock_narrative_mode"))
        if narrative_mode and not financial_tool_is_usable(tool_result):
            return AssemblyProfile.STOCK_NARRATIVE
        return AssemblyProfile.STOCK_FULL

    return AssemblyProfile.DATA_DEFAULT


COMPACT_CITATION_PROFILES = frozenset(
    {
        AssemblyProfile.STOCK_FULL,
        AssemblyProfile.STOCK_NARRATIVE,
        AssemblyProfile.COMPOUND,
    }
)


def use_compact_citation_context(profile: AssemblyProfile) -> bool:
    """Whether assembly should emit slim citation context (T-027)."""
    return profile in COMPACT_CITATION_PROFILES


def rag_hits_from_state(state: AgentState) -> list[RagHit]:
    hits: list[RagHit] = []
    for item in state.get("rag_hits") or []:
        if isinstance(item, dict):
            try:
                hits.append(RagHit.model_validate(item))
            except Exception:
                continue
    return hits
