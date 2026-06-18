"""Tests for hotspot signal lookup (mocked THS HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.tools.hotspot_signal_lookup import lookup_hotspot_signal


def _ths_payload() -> dict:
    return {
        "errocode": 0,
        "data": [
            {
                "code": "300024",
                "name": "机器人",
                "reason": "人形机器人+减速器",
                "zhangfu": 8.5,
                "close": 12.3,
                "chengjiaoe": 1500000000,
                "huanshou": 5.2,
                "market": "深",
            },
            {
                "code": "688017",
                "name": "绿的谐波",
                "reason": "谐波减速器+机器人",
                "zhangfu": 6.1,
                "close": 88.0,
                "chengjiaoe": 900000000,
                "huanshou": 3.1,
                "market": "沪",
            },
        ],
    }


@patch("src.integrations.market_data.ths_client.requests.get")
def test_lookup_hotspot_signal_live(mock_get: MagicMock) -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = _ths_payload()
    mock_get.return_value = response

    result = lookup_hotspot_signal(topic="机器人", signal_limit=5)

    assert result["signal_mode"] == "ths_live"
    assert result["is_mock"] is False
    assert result["fallback_used"] is False
    assert result["stock_count"] >= 1
    assert any("机器人" in str(stock.get("reason", "")) for stock in result["stocks"])


@patch("src.integrations.market_data.ths_client.requests.get")
def test_lookup_hotspot_signal_topic_not_matched(mock_get: MagicMock) -> None:
    """When keyword misses THS list, do not return unrelated market leaders."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = _ths_payload()
    mock_get.return_value = response

    result = lookup_hotspot_signal(topic="宠物行业", signal_limit=5)

    assert result["signal_mode"] == "ths_live"
    assert result["topic_matched"] is False
    assert result["stock_count"] == 0
    assert "未命中" in result["notes"]


@patch("src.integrations.market_data.ths_client.requests.get")
def test_lookup_hotspot_signal_kb_fallback(mock_get: MagicMock) -> None:
    mock_get.side_effect = RuntimeError("network down")

    result = lookup_hotspot_signal(topic="机器人", signal_limit=5)

    assert result["signal_mode"] == "kb_material"
    assert result["fallback_used"] is True
    assert result["is_mock"] is False
    assert result["material_count"] >= 1
