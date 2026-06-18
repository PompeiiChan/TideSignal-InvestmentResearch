"""Tests for sector heatmap intent and tool."""

from unittest.mock import MagicMock, patch

from backend.src.agents.heatmap_intent import wants_sector_heatmap
from backend.src.agents.tools.sector_heatmap_lookup import lookup_sector_heatmap
from backend.src.integrations.llm.rich_block_builders import build_sector_heatmap_payload


def test_wants_sector_heatmap_keywords() -> None:
    assert wants_sector_heatmap("给我今天的行业板块热力图")
    assert wants_sector_heatmap("看一下板块全景")
    assert not wants_sector_heatmap("半导体涨幅前五")


@patch("backend.src.agents.tools.sector_heatmap_lookup.industry_heatmap_boards")
def test_lookup_sector_heatmap_shape(mock_boards: MagicMock) -> None:
    mock_boards.return_value = [
        {
            "board_name": "半导体",
            "board_code": "BK0917",
            "change_pct": 3.42,
            "turnover_amount": 84200000000,
            "leader": "寒武纪",
            "leader_change": 8.76,
            "up_count": 30,
            "down_count": 10,
        },
        {
            "board_name": "白酒",
            "board_code": "BK0896",
            "change_pct": -0.85,
            "turnover_amount": 62100000000,
            "leader": "贵州茅台",
            "leader_change": -0.42,
            "up_count": 5,
            "down_count": 20,
        },
    ]

    result = lookup_sector_heatmap(board_limit=2)
    assert result["tile_count"] == 2
    assert len(result["tiles"]) == 2
    assert result["is_mock"] is False
    payload = build_sector_heatmap_payload(result)
    assert payload["size_by"] == "turnover_amount"
    assert payload["tiles"][0]["board_name"] == "半导体"
