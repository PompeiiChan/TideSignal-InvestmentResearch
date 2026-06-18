"""Tests for scenario return calculator flow."""

from __future__ import annotations

from src.agents.nodes.context_preprocess import _detect_risk_hint
from src.agents.nodes.routing_decision import build_execution_plan
from src.agents.stock_tool_plan import resolve_stock_tool_names
from src.integrations.llm.rich_block_builders import (
    build_calculator_rich_payload,
    build_scenario_calculator_rich_payload,
)
from src.services.citation_catalog import CitationCatalog, CitationEntry
from src.services.earnings_forecast import extract_earnings_forecast
from src.services.scenario_return import (
    build_scenario_return_calculation,
    enrich_scenario_return_slots,
    is_scenario_return_query,
)


def test_is_scenario_return_query() -> None:
    assert is_scenario_return_query("我现在买中际旭创，预期回报率是多少")
    assert not is_scenario_return_query("泸州老窖目标价能给到多少")


def test_scenario_return_skips_prediction_boundary() -> None:
    assert _detect_risk_hint("我现在买宁德时代，预期回报率是多少") == ""


def test_enrich_scenario_return_slots_defaults_100_shares() -> None:
    slots = enrich_scenario_return_slots("买海天味业预期收益多少", {"stock_name": "海天味业"})
    assert slots["scenario_return_mode"] is True
    assert slots["share_count"] == 100


def test_build_execution_plan_stock_scenario_mode() -> None:
    plan = build_execution_plan(
        "stock_analysis_agent",
        slots={"stock_name": "中际旭创", "scenario_return_mode": True},
        query="我现在买中际旭创预期回报率是多少",
    )
    assert plan.get("scenario_return_mode") is True


def test_resolve_stock_tools_for_scenario_return() -> None:
    names = resolve_stock_tool_names(
        None,
        query="我现在买中际旭创预期回报率是多少",
        scenario_return_mode=True,
    )
    assert "valuation_profile_lookup" in names
    assert "consensus_valuation_lookup" in names


def test_extract_earnings_forecast_from_eps_and_pe() -> None:
    hits = [
        {
            "source_type": "report",
            "doc_id": "report_htwy",
            "title": "海天味业研报",
            "snippet": "对应 EPS 分别为 1.20、1.41、1.58 元。给予 25 倍 PE 估值。",
        }
    ]
    forecast = extract_earnings_forecast(hits, stock_name="海天味业")
    assert forecast["found"] is True
    assert "base" in forecast["scenarios"]
    assert forecast["scenarios"]["base"]["target_price"] > 0
    assert forecast["scenarios"]["base"]["source"]["doc_id"] == "report_htwy"
    assert forecast["scenarios"]["base"]["source"]["title"] == "海天味业研报"
    assert forecast["scenarios"]["base"]["source"]["excerpt"] == ""
    assert forecast["extraction_method"] == "eps_pe_triple"


def test_extract_earnings_forecast_formats_compact_source_title() -> None:
    hits = [
        {
            "source_type": "report",
            "doc_id": "research_603288_bocom",
            "title": "海天味业公司研报：调味品龙头海外市场成长空间",
            "publisher": "交银国际",
            "snippet": "交银国际研究 首次覆盖 对应 EPS 分别为 1.20、1.41、1.58 元。给予 25 倍 PE 估值。",
        }
    ]
    forecast = extract_earnings_forecast(hits, stock_name="海天味业")
    assert (
        forecast["scenarios"]["base"]["source"]["title"]
        == "海天味业公司研报：调味品龙头海外市场成长空间"
    )
    assert forecast["scenarios"]["base"]["source"]["excerpt"] == ""


def test_build_scenario_return_calculation() -> None:
    valuation = {
        "found": True,
        "valuation": {"stock_name": "测试股", "price": "100元"},
    }
    forecast = {
        "found": True,
        "scenarios": {
            "base": {"label": "中性", "target_price": 120, "assumption": "测试假设"},
        },
    }
    calc = build_scenario_return_calculation(
        valuation_tool=valuation,
        forecast_tool=forecast,
        rag_hits=[],
        share_count=100,
    )
    assert calc is not None
    assert calc["share_count"] == 100
    assert calc["scenario_return_mode"] is True
    assert calc["return_pct"] > 0


def test_build_calculator_payload_basic_fields() -> None:
    payload = build_calculator_rich_payload(
        {
            "buy_price": 100,
            "sell_price": 120,
            "share_count": 100,
            "fee_rate": 0.0003,
            "net_profit": 1998.8,
            "return_pct": 19.988,
            "assumption": "中性情景",
        }
    )
    assert payload["fields"][2]["value"] == 100
    assert payload.get("assumption") == "中性情景"


def test_scenario_return_uses_scenario_calculator_payload() -> None:
    catalog = CitationCatalog()
    catalog.entries.append(
        CitationEntry(index=1, title="测试股 行情", source_type="market", doc_id="000001", origin="tencent_quote_api")
    )
    catalog.doc_index["__valuation_tool__"] = 1
    catalog.entries.append(
        CitationEntry(index=2, title="测试研报", source_type="report", doc_id="report_test", origin="local_kb")
    )
    catalog.doc_index["report_test"] = 2
    payload = build_scenario_calculator_rich_payload(
        {
            "buy_price": 100,
            "share_count": 100,
            "fee_rate": 0.0003,
            "stock_name": "测试股",
            "scenario_return_mode": True,
        },
        {
            "found": True,
            "scenario_order": ["base"],
            "scenarios": {
                "base": {
                    "label": "中性",
                    "target_price": 120,
                    "assumption": "中性情景",
                    "source": {"doc_id": "report_test", "title": "测试研报", "origin": "local_kb"},
                }
            },
        },
        catalog,
    )
    assert payload["scenarios"][0]["source"]["citation_index"] == 2
