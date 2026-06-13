"""Agent tool registry for LangGraph tool_call node."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .hotspot_fact_lookup import lookup_hotspot_facts
from .hotspot_signal_lookup import lookup_hotspot_signal
from .market_ranking_lookup import lookup_market_ranking as lookup_live_market_ranking
from .mock_financial_profile_lookup import lookup_financial_profile
from .mock_hotspot_material_lookup import lookup_hotspot_material
from .mock_market_ranking_lookup import lookup_market_ranking as lookup_mock_market_ranking
from .return_calculator import compute_return
from .sector_heatmap_lookup import lookup_sector_heatmap
from .valuation_profile_lookup import lookup_valuation_profile

ToolCallable = Callable[..., dict[str, Any]]

TOOL_REGISTRY: dict[str, ToolCallable] = {
    "hotspot_fact_lookup": lookup_hotspot_facts,
    "hotspot_signal_lookup": lookup_hotspot_signal,
    "market_ranking_lookup": lookup_live_market_ranking,
    "mock_market_ranking_lookup": lookup_mock_market_ranking,
    "mock_financial_profile_lookup": lookup_financial_profile,
    "valuation_profile_lookup": lookup_valuation_profile,
    "mock_hotspot_material_lookup": lookup_hotspot_material,
    "local_return_calculator": compute_return,
    "sector_heatmap_lookup": lookup_sector_heatmap,
}

__all__ = [
    "TOOL_REGISTRY",
    "ToolCallable",
    "compute_return",
    "lookup_financial_profile",
    "lookup_hotspot_material",
    "lookup_hotspot_facts",
    "lookup_hotspot_signal",
    "lookup_live_market_ranking",
    "lookup_mock_market_ranking",
    "lookup_sector_heatmap",
    "lookup_valuation_profile",
]
