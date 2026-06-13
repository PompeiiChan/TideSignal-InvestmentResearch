"""Tests for rich block payload builders."""

from backend.src.integrations.llm.rich_block_builders import build_calculator_rich_payload


def test_build_calculator_rich_payload_fields_results() -> None:
    payload = build_calculator_rich_payload(
        {
            "buy_price": 15,
            "sell_price": 20,
            "share_count": 1000,
            "fee_rate": 0.03,
            "net_profit": 4991.5,
            "return_pct": 33.27,
        }
    )
    assert len(payload["fields"]) == 4
    assert payload["fields"][0]["key"] == "buy_price"
    assert payload["results"][0]["key"] == "return_rate"
    assert "33.27%" in payload["results"][0]["value"]
