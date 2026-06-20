"""Eastmoney push2 client HTTP layer tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from backend.src.integrations.market_data.eastmoney_client import (
    CLIST_FALLBACK_URL,
    CLIST_URL,
    em_get,
    fetch_board_list,
)


def test_em_get_uses_httpx_without_proxy_env() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    with patch("backend.src.integrations.market_data.eastmoney_client._EM_CLIENT") as client:
        client.headers = {"User-Agent": "test"}
        client.get.return_value = mock_response
        result = em_get(CLIST_URL, params={"pn": "1"})
    assert result is mock_response
    client.get.assert_called_once()
    assert client.get.call_args.args[0] == CLIST_URL


def test_em_get_falls_back_to_82_host_on_primary_failure() -> None:
    fallback = MagicMock()
    fallback.raise_for_status = MagicMock()
    with patch("backend.src.integrations.market_data.eastmoney_client._EM_CLIENT") as client:
        client.headers = {"User-Agent": "test"}
        client.get.side_effect = [
            httpx.ConnectError("primary down"),
            fallback,
        ]
        result = em_get(CLIST_URL, params={"pn": "1"})
    assert result is fallback
    assert client.get.call_args_list[1].args[0] == CLIST_FALLBACK_URL


def test_fetch_board_list_parses_diff() -> None:
    payload = {
        "data": {
            "diff": [
                {"f12": "BK0001", "f14": "半导体", "f3": 1.5, "f6": 1000.0, "f104": 10, "f105": 5},
            ]
        }
    }
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    with patch(
        "backend.src.integrations.market_data.eastmoney_client.em_get",
        return_value=mock_response,
    ):
        rows = fetch_board_list("industry", page_size=10)
    assert len(rows) == 1
    assert rows[0]["board_name"] == "半导体"
