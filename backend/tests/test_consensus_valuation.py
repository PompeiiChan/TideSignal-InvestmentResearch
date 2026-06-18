"""Tests for consensus valuation and THS worth parser."""

from __future__ import annotations

from unittest.mock import patch

from src.agents.stock_tool_plan import resolve_stock_tool_names
from src.integrations.market_data.ths_worth_client import (
    _parse_dynamic_pe_by_year,
    _parse_eps_forecast_table,
)
from src.services.consensus_valuation import build_consensus_scenarios, lookup_consensus_valuation
from src.services.scenario_return import build_scenario_return_calculation

_SAMPLE_EPS_HTML = """
<div id="forecast">
<table class="m_table">
<thead><tr><th>年度</th><th>预测机构数</th><th>最小值</th><th>均值</th><th>最大值</th></tr></thead>
<tbody>
<tr><th>2026</th><td class="tc">46</td><td>66.27</td><td>68.82</td><td>77.85</td></tr>
<tr><th>2027</th><td class="tc">46</td><td>68.73</td><td>72.60</td><td>84.02</td></tr>
<tr><th>2028</th><td class="tc">41</td><td>71.35</td><td>76.31</td><td>85.06</td></tr>
</tbody>
</table>
</div>
"""

_SAMPLE_PE_HTML = """
<th class="tl">市盈率(动态)</th>
<td>21.50</td><td>18.63</td><td>19.48</td>
<td><span>18.51</span></td></tr>
"""


def test_parse_eps_forecast_table() -> None:
    bands = _parse_eps_forecast_table(_SAMPLE_EPS_HTML)
    assert len(bands) == 3
    assert bands[0].year == 2026
    assert bands[0].mid == 68.82


def test_parse_dynamic_pe_by_year() -> None:
    pe_map = _parse_dynamic_pe_by_year(_SAMPLE_PE_HTML)
    assert pe_map[2026] == 18.63
    assert pe_map[2027] == 19.48
    assert pe_map[2028] == 18.51


def test_build_consensus_scenarios_year_mapping() -> None:
    raw = {
        "found": True,
        "data_origin": "ths_worth_consensus",
        "source": "https://basic.10jqka.com.cn/new/600519/worth.html",
        "reference_year": 2025,
        "years": {
            "2026": {
                "year": 2026,
                "analyst_count": 46,
                "eps": {"low": 66.27, "mid": 68.82, "high": 77.85},
                "pe": {"low": 18.0, "mid": 18.63, "high": 19.0},
            },
            "2027": {
                "year": 2027,
                "analyst_count": 46,
                "eps": {"low": 68.73, "mid": 72.60, "high": 84.02},
                "pe": {"low": 18.0, "mid": 19.48, "high": 20.0},
            },
            "2028": {
                "year": 2028,
                "analyst_count": 41,
                "eps": {"low": 71.35, "mid": 76.31, "high": 85.06},
                "pe": {"low": 17.5, "mid": 18.51, "high": 19.5},
            },
        },
        "notes": "test",
    }
    result = build_consensus_scenarios(raw, stock_name="贵州茅台")
    assert result["found"] is True
    assert result["scenarios"]["bear"]["forecast_year"] == 2026
    assert result["scenarios"]["base"]["forecast_year"] == 2027
    assert result["scenarios"]["bull"]["forecast_year"] == 2028
    assert result["scenarios"]["base"]["target_price"] > 0


def test_build_scenario_return_requires_forecast() -> None:
    valuation = {"found": True, "valuation": {"stock_name": "测试", "price": "100元"}}
    assert (
        build_scenario_return_calculation(
            valuation_tool=valuation,
            forecast_tool={"found": False, "scenarios": {}},
            rag_hits=[],
        )
        is None
    )


def test_resolve_stock_tools_includes_consensus_lookup() -> None:
    names = resolve_stock_tool_names(
        None,
        query="我现在买贵州茅台预期回报率是多少",
        scenario_return_mode=True,
    )
    assert names == ["valuation_profile_lookup", "consensus_valuation_lookup"]


def test_lookup_consensus_valuation_ths_path() -> None:
    ths_raw = {
        "found": True,
        "data_origin": "ths_worth_consensus",
        "source": "https://basic.10jqka.com.cn/new/600519/worth.html",
        "reference_year": 2025,
        "years": {
            "2026": {
                "year": 2026,
                "analyst_count": 10,
                "eps": {"low": 1.0, "mid": 1.1, "high": 1.2},
                "pe": {"low": 20.0, "mid": 22.0, "high": 24.0},
            },
            "2027": {
                "year": 2027,
                "analyst_count": 10,
                "eps": {"low": 1.1, "mid": 1.2, "high": 1.3},
                "pe": {"low": 19.0, "mid": 21.0, "high": 23.0},
            },
            "2028": {
                "year": 2028,
                "analyst_count": 10,
                "eps": {"low": 1.2, "mid": 1.3, "high": 1.4},
                "pe": {"low": 18.0, "mid": 20.0, "high": 22.0},
            },
        },
        "notes": "",
    }
    with patch(
        "src.services.consensus_valuation.fetch_ths_worth_consensus",
        return_value=ths_raw,
    ):
        result = lookup_consensus_valuation(stock_code="600519", stock_name="贵州茅台")
    assert result["found"] is True
    assert "base" in result["scenarios"]
