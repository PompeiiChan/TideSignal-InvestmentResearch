"""Tests for sector heatmap intent and tool."""

from backend.src.agents.heatmap_intent import wants_sector_heatmap
from backend.src.agents.tools.sector_heatmap_lookup import lookup_sector_heatmap
from backend.src.integrations.llm.rich_block_builders import build_sector_heatmap_payload


def test_wants_sector_heatmap_keywords() -> None:
    assert wants_sector_heatmap("给我今天的行业板块热力图")
    assert wants_sector_heatmap("看一下板块全景")
    assert not wants_sector_heatmap("半导体涨幅前五")


def test_lookup_sector_heatmap_mock_shape() -> None:
    result = lookup_sector_heatmap(board_limit=5)
    assert result["tile_count"] == 5
    assert len(result["tiles"]) == 5
    payload = build_sector_heatmap_payload(result)
    assert payload["size_by"] == "turnover_amount"
    assert payload["tiles"][0]["board_name"]
