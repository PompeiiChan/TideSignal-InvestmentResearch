"""Deterministic yuan -> 亿元 conversion for financial knowledge-base text."""

from __future__ import annotations

import re

_YI_DIVISOR = 100_000_000
_MIN_YUAN_TO_CONVERT = 1_000_000

_COMMA_YUAN_AMOUNT = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?)(元)?")

_LINE_SKIP_PATTERNS = (
    re.compile(r"毛利率|净利率|净资产收益率|加权平均净资产收益率"),
    re.compile(r"每股收益|基本每股收益|稀释每股收益|元/股"),
    re.compile(r"市盈率|市净率|P/E|P/B|PE\(|PB\("),
    re.compile(r"^股本\s|^\s*股本\s|股份总数|持股数量|万股|亿股"),
    re.compile(r"股票代码|证券代码|股票简称"),
    re.compile(r"分配预案|为基数|为基$|总股本|回购专用.*股|股数"),
)

_UNIT_YUAN_HINT = re.compile(r"单位[：:]\s*元|（元）|\(元\)")
_UNIT_HEADER_RE = re.compile(r"单位[：:]\s*(千元|万元|元)")
_INLINE_UNIT_IN_LINE_RE = re.compile(r"（(千元|万元|元)）|\((千元|万元|元)\)")


def yuan_amount_to_yi(amount: str, *, unit_multiplier: int = 1) -> str:
    """Convert a numeric yuan string to a 亿元 label."""
    value = float(amount.replace(",", "")) * unit_multiplier
    return f"{value / _YI_DIVISOR:.2f}亿元"


def format_yi(amount: str) -> str:
    """Alias used by financial summary builders."""
    return yuan_amount_to_yi(amount)


def _line_should_skip(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    return any(pattern.search(stripped) for pattern in _LINE_SKIP_PATTERNS)


def _should_convert_amount(amount: str, *, line: str, match: re.Match[str]) -> bool:
    tail = line[match.end() :].lstrip()
    if tail.startswith("%"):
        return False
    if tail.startswith("股"):
        return False

    normalized = amount.replace(",", "")
    if not normalized:
        return False

    try:
        value = float(normalized)
    except ValueError:
        return False

    if value < _MIN_YUAN_TO_CONVERT:
        return False

    if "," in amount:
        return True

    if _UNIT_YUAN_HINT.search(line):
        return True

    account_hints = (
        "收入",
        "成本",
        "费用",
        "利润",
        "资产",
        "负债",
        "现金",
        "存款",
        "贷款",
        "借款",
        "资金",
        "存货",
        "商誉",
        "净值",
        "净额",
        "合计",
        "总额",
        "余额",
        "准备",
        "公积",
        "收益",
        "损失",
        "支付",
        "收到",
        "分配",
        "回购",
        "投资",
        "筹资",
        "经营",
        "红利",
        "未分配",
    )
    return any(hint in line for hint in account_hints)


def _unit_multiplier(unit_label: str) -> int:
    if unit_label == "千元":
        return 1_000
    if unit_label == "万元":
        return 10_000
    return 1


def _line_has_decimal_yuan_amount(line: str) -> bool:
    """Detect 元-denominated statement lines (e.g. 27,341,566,698.37)."""
    for match in _COMMA_YUAN_AMOUNT.finditer(line):
        amount = match.group(1)
        if "." in amount and _should_convert_amount(amount, line=line, match=match):
            return True
    return False


def _line_looks_like_thousand_yuan_statement(line: str) -> bool:
    """Infer 千元 when PDF omits unit header but amounts are integer-style (typical Q1 tables)."""
    if _line_has_decimal_yuan_amount(line):
        return False
    if _UNIT_YUAN_HINT.search(line):
        return False
    amounts: list[str] = []
    for match in _COMMA_YUAN_AMOUNT.finditer(line):
        amount = match.group(1)
        if _should_convert_amount(amount, line=line, match=match):
            amounts.append(amount)
    if not amounts:
        return False
    try:
        values = [float(item.replace(",", "")) for item in amounts]
    except ValueError:
        return False
    return all(value >= _MIN_YUAN_TO_CONVERT for value in values)


def _line_unit_multiplier(line: str, table_multiplier: int) -> int:
    """Resolve per-line unit: table header > inline field label > 千元推断 > carry-over."""
    header_match = _UNIT_HEADER_RE.search(line)
    if header_match:
        return _unit_multiplier(header_match.group(1))
    inline_match = _INLINE_UNIT_IN_LINE_RE.search(line)
    if inline_match:
        label = inline_match.group(1) or inline_match.group(2) or ""
        return _unit_multiplier(label)
    if table_multiplier == 1 and _line_looks_like_thousand_yuan_statement(line):
        return 1_000
    return table_multiplier


def _convert_line(line: str, *, unit_multiplier: int = 1) -> str:
    if _line_should_skip(line):
        return line

    def replacer(match: re.Match[str]) -> str:
        amount = match.group(1)
        if not _should_convert_amount(amount, line=line, match=match):
            return match.group(0)
        return yuan_amount_to_yi(amount, unit_multiplier=unit_multiplier)

    return _COMMA_YUAN_AMOUNT.sub(replacer, line)


def convert_financial_yuan_to_yi(text: str) -> str:
    """Convert comma-separated yuan amounts in financial text to 亿元 labels."""
    if not text.strip():
        return text

    table_unit_multiplier = 1
    converted_lines: list[str] = []
    for line in text.splitlines():
        header_match = _UNIT_HEADER_RE.search(line)
        if header_match:
            table_unit_multiplier = _unit_multiplier(header_match.group(1))
        line_multiplier = _line_unit_multiplier(line, table_unit_multiplier)
        converted_lines.append(_convert_line(line, unit_multiplier=line_multiplier))
    return "\n".join(converted_lines)


def count_converted_amounts(before: str, after: str) -> int:
    """Count how many 亿元 labels were introduced (for batch scripts)."""
    return after.count("亿元") - before.count("亿元")
