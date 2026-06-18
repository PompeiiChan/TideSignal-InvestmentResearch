"""Tests for live market ranking tool (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from src.agents.tools.market_ranking_lookup import lookup_market_ranking


def _clist_response(items: list[dict]) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"data": {"diff": items}}
    return response


@patch("src.integrations.market_data.eastmoney_client.em_get")
def test_lookup_sector_stock_ranking(mock_em_get: MagicMock) -> None:
    mock_em_get.side_effect = [
        _clist_response(
            [
                {
                    "f12": "BK0917",
                    "f14": "半导体",
                    "f3": 2.5,
                    "f104": 30,
                    "f105": 10,
                    "f140": "寒武纪",
                    "f136": 5.1,
                }
            ]
        ),
        _clist_response(
            [
                {
                    "f12": "688256",
                    "f14": "寒武纪",
                    "f2": 948.5,
                    "f3": 5.1,
                    "f6": 11190000000,
                    "f13": 1,
                },
                {
                    "f12": "688981",
                    "f14": "中芯国际",
                    "f2": 85.2,
                    "f3": 3.2,
                    "f6": 5200000000,
                    "f13": 1,
                },
            ]
        ),
    ]

    result = lookup_market_ranking(industry="半导体", metric="涨幅排行", rank_limit=2)

    assert result["tool"] == "market_ranking_lookup"
    assert result["is_mock"] is False
    assert result["fallback_used"] is False
    assert result["row_count"] == 2
    assert result["rows"][0]["stock_name"] == "寒武纪"
    assert result["rows"][0]["ticker"] == "688256.SH"
    assert result["rows"][0]["pct_change"] == pytest.approx(5.1)


@patch("src.integrations.market_data.eastmoney_client.em_get")
def test_lookup_returns_empty_on_api_error(mock_em_get: MagicMock) -> None:
    mock_em_get.side_effect = RuntimeError("network down")

    result = lookup_market_ranking(industry="半导体", rank_limit=3)

    assert result["tool"] == "market_ranking_lookup"
    assert result["row_count"] == 0
    assert result["rows"] == []
    assert result["is_mock"] is False
    assert result.get("error")
