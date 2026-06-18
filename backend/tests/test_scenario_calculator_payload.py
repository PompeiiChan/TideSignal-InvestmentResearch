"""Tests for scenario_calculator rich block payload."""

from __future__ import annotations

from src.integrations.llm.rich_block_builders import build_scenario_calculator_rich_payload
from src.services.citation_catalog import CitationCatalog, CitationEntry


def _catalog_with_valuation_and_report() -> CitationCatalog:
    catalog = CitationCatalog()
    catalog.entries.append(
        CitationEntry(index=1, title="海天味业 行情", source_type="market", doc_id="603288", origin="tencent_quote_api")
    )
    catalog.doc_index["__valuation_tool__"] = 1
    catalog.entries.append(
        CitationEntry(index=2, title="海天味业研报", source_type="report", doc_id="report_htwy_2025", origin="local_kb")
    )
    catalog.doc_index["report_htwy_2025"] = 2
    return catalog


def test_build_scenario_calculator_payload_with_citations() -> None:
    catalog = _catalog_with_valuation_and_report()
    calc_tool = {
        "buy_price": 38.5,
        "share_count": 100,
        "fee_rate": 0.0003,
        "stock_name": "海天味业",
        "return_pct": 12.5,
        "net_profit": 481.0,
        "formula": "收益率 = (卖出价 - 买入价) * 股数 - 费用",
        "scenario_return_mode": True,
    }
    forecast_tool = {
        "found": True,
        "scenario_order": ["bear", "base", "bull"],
        "scenarios": {
            "bear": {
                "label": "保守",
                "target_price": 34.0,
                "assumption": "保守情景",
                "source": {
                    "doc_id": "report_htwy_2025",
                    "title": "海天味业研报",
                    "excerpt": "EPS 分别为 1.20、1.41、1.58",
                    "origin": "local_kb",
                },
            },
            "base": {
                "label": "中性",
                "target_price": 35.25,
                "eps": 1.41,
                "pe": 25,
                "assumption": "中性情景",
                "source": {
                    "doc_id": "report_htwy_2025",
                    "title": "海天味业研报",
                    "excerpt": "给予 25 倍 PE",
                    "origin": "local_kb",
                },
            },
            "bull": {
                "label": "乐观",
                "target_price": 38.7,
                "assumption": "乐观情景",
                "source": {
                    "doc_id": "report_htwy_2025",
                    "title": "海天味业研报",
                    "excerpt": "乐观 EPS",
                    "origin": "local_kb",
                },
            },
        },
    }

    payload = build_scenario_calculator_rich_payload(calc_tool, forecast_tool, catalog)

    assert payload["stock_name"] == "海天味业"
    assert payload["buy_price_source"]["citation_index"] == 1
    assert len(payload["scenarios"]) == 3
    assert payload["scenarios"][1]["key"] == "base"
    assert payload["scenarios"][1]["source"]["citation_index"] == 2
    assert payload["scenarios"][1]["return_pct"] is not None
