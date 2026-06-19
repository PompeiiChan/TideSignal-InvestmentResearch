"""Tests for Eastmoney valuation history client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.integrations.market_data.em_valuation_history_client import fetch_valuation_history


def _history_row(trade_date: str, pe: float, pb: float) -> dict:
    return {
        "SECUCODE": "000661.SZ",
        "SECURITY_NAME_ABBR": "长春高新",
        "PE_TTM": pe,
        "PB_MRQ": pb,
        "TRADE_DATE": f"{trade_date} 00:00:00",
    }


@patch("src.integrations.market_data.em_valuation_history_client.em_get")
def test_fetch_valuation_history_computes_percentiles(mock_em_get: MagicMock) -> None:
    rows = []
    for month in range(1, 13):
        trade_date = f"2025-{month:02d}-15"
        rows.append(_history_row(trade_date, 10.0 + month * 0.5, 1.5 + month * 0.05))
    rows.append(_history_row("2026-06-18", 18.2, 3.1))

    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"success": True, "result": {"data": list(reversed(rows))}}
    mock_em_get.return_value = response

    result = fetch_valuation_history("000661.SZ", years=3)

    assert result["found"] is True
    assert result["secu_code"] == "000661.SZ"
    assert result["trading_day_count"] >= 12
    assert result["pe_ttm"]["current"] == 18.2
    assert result["pe_ttm"]["sample_count"] >= 12
    assert result["pe_ttm"]["percentile"] is not None
    assert result["pb"]["current"] == 3.1
    assert len(result["quarterly_series"]) >= 4


@patch("src.integrations.market_data.em_valuation_history_client.em_get")
def test_fetch_valuation_history_empty_on_api_failure(mock_em_get: MagicMock) -> None:
    mock_em_get.side_effect = RuntimeError("network down")

    result = fetch_valuation_history("000661")

    assert result["found"] is False
    assert "失败" in result["notes"]
