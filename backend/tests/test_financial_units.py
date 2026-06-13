"""Tests for deterministic financial yuan -> 亿元 conversion."""

from __future__ import annotations

from backend.src.services.rag.financial_units import convert_financial_yuan_to_yi, yuan_amount_to_yi


def test_yuan_amount_to_yi() -> None:
    assert yuan_amount_to_yi("25,731,010,647.32") == "257.31亿元"


def test_convert_revenue_line() -> None:
    line = "营业收入（元） 25,731,010,647.32 31,196,248,208.33 -17.52% 30,233,301,388.26"
    converted = convert_financial_yuan_to_yi(line)
    assert "257.31亿元" in converted
    assert "311.96亿元" in converted
    assert "-17.52%" in converted


def test_skip_margin_and_ratio_lines() -> None:
    line = "加权平均净资产收益率 22.66% 30.44% -7.78% 35.07%"
    assert convert_financial_yuan_to_yi(line) == line


def test_skip_eps_line() -> None:
    line = "基本每股收益（元/股） 7.36 9.18 -19.83% 9.02"
    assert convert_financial_yuan_to_yi(line) == line


def test_convert_balance_sheet_line() -> None:
    line = "货币资金 27,341,566,698.37 33,578,396,831.33"
    converted = convert_financial_yuan_to_yi(line)
    assert "273.42亿元" in converted
    assert "335.78亿元" in converted


def test_skip_share_capital_line() -> None:
    line = "股本 1,471,941,963.00 1,471,941,963.00"
    assert convert_financial_yuan_to_yi(line) == line


def test_skip_dividend_share_base_line() -> None:
    line = "公司经本次董事会审议通过的利润分配预案为：以 1,471,941,963 为基数"
    assert convert_financial_yuan_to_yi(line) == line


def test_convert_thousand_yuan_unit_table() -> None:
    text = "单位：千元\n营业收入 423,701,834 362,012,554 17.04% 400,917,045"
    converted = convert_financial_yuan_to_yi(text)
    assert "4237.02亿元" in converted
    assert "17.04%" in converted


def test_strip_trailing_yuan_after_conversion() -> None:
    line = "拟派发现金红利4,677,228,362.40元（含税）"
    converted = convert_financial_yuan_to_yi(line)
    assert "46.77亿元（含税）" in converted
    assert "亿元元" not in converted


def test_summary_already_in_yi_unchanged() -> None:
    text = "营业收入257.31亿元，同比-17.52%\n归母净利润108.31亿元，同比-19.61%。"
    assert convert_financial_yuan_to_yi(text) == text


def test_convert_inline_thousand_yuan_field_label() -> None:
    """Q1 主要指标表：字段名带（千元）但无独立「单位：千元」表头。"""
    line = "总资产（千元） 1,046,329,036 974,827,544 7.33%"
    converted = convert_financial_yuan_to_yi(line)
    assert "10463.29亿元" in converted
    assert "9748.28亿元" in converted
    assert "10.46亿元" not in converted


def test_convert_cashflow_inline_thousand_yuan_label() -> None:
    line = "经营活动产生的现金流量净额（千元） 33,680,852 32,868,257 2.47%"
    converted = convert_financial_yuan_to_yi(line)
    assert "336.81亿元" in converted
    assert "328.68亿元" in converted


def test_convert_balance_sheet_total_without_unit_header() -> None:
    """Q1 资产负债表切块常无「单位：千元」表头，需从整数型大额行推断。"""
    line = "资产总计     1,046,329,036    974,827,544"
    converted = convert_financial_yuan_to_yi(line)
    assert "10463.29亿元" in converted
    assert "9748.28亿元" in converted
