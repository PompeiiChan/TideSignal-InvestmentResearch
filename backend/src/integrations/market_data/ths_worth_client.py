"""Tonghuashun (10jqka) worth.html consensus EPS / dynamic PE parser."""

from __future__ import annotations

import logging
import re
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_REFERER = "https://basic.10jqka.com.cn/"
_MIN_INTERVAL = 0.8
_last_fetch = 0.0

_YEAR_ROW_RE = re.compile(
    r"<th[^>]*>\s*(20\d{2})\s*</th>\s*"
    r"<td[^>]*>\s*(\d+)\s*</td>\s*"
    r"<td[^>]*>\s*([0-9]+(?:\.[0-9]+)?)\s*</td>\s*"
    r"<td[^>]*>\s*([0-9]+(?:\.[0-9]+)?)\s*</td>\s*"
    r"<td[^>]*>\s*([0-9]+(?:\.[0-9]+)?)\s*</td>",
    re.IGNORECASE,
)
_PE_DYNAMIC_RE = re.compile(
    r"市盈率\s*\(\s*动态\s*\)\s*</th>\s*"
    r"(?P<cells>(?:\s*<td[^>]*>\s*[0-9]+(?:\.[0-9]+)?\s*</td>)+)"
    r"(?P<after>.*?)(?:</tr>|</tbody>)",
    re.IGNORECASE | re.DOTALL,
)
_PE_CELL_RE = re.compile(r"<td[^>]*>\s*([0-9]+(?:\.[0-9]+)?)\s*</td>")
_PE_SPAN_RE = re.compile(r"<span>\s*([0-9]+(?:\.[0-9]+)?)\s*</span>")


@dataclass(frozen=True)
class YearBand:
    year: int
    analyst_count: int
    low: float
    mid: float
    high: float


def _throttled_fetch(url: str) -> str:
    global _last_fetch
    wait = _MIN_INTERVAL - (time.time() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Referer": _REFERER},
    )
    with urllib.request.urlopen(request, timeout=18) as response:
        payload = response.read()
    _last_fetch = time.time()
    return str(payload.decode("gbk", errors="replace"))


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def _parse_eps_forecast_table(html: str) -> list[YearBand]:
    """Parse the first EPS consensus table (yuan per share, not net profit in billions)."""
    forecast_idx = html.find('id="forecast"')
    if forecast_idx < 0:
        forecast_idx = 0
    section = html[forecast_idx : forecast_idx + 120_000]
    bands: list[YearBand] = []
    seen_years: set[int] = set()
    for match in _YEAR_ROW_RE.finditer(section):
        year = int(match.group(1))
        if year in seen_years:
            continue
        low = float(match.group(3))
        mid = float(match.group(4))
        high = float(match.group(5))
        # Net-profit rows use values in hundreds+; EPS for large caps is typically < 500.
        if mid > 500:
            continue
        seen_years.add(year)
        bands.append(
            YearBand(
                year=year,
                analyst_count=int(match.group(2)),
                low=low,
                mid=mid,
                high=high,
            )
        )
    bands.sort(key=lambda item: item.year)
    return bands


def _parse_dynamic_pe_by_year(html: str) -> dict[int, float]:
    match = _PE_DYNAMIC_RE.search(html)
    if not match:
        return {}
    td_values = [float(item) for item in _PE_CELL_RE.findall(match.group("cells"))]
    span_values = [float(item) for item in _PE_SPAN_RE.findall(match.group("after")[:400])]
    if len(td_values) >= 4:
        pe_triplet = td_values[1:4]
    elif len(td_values) == 3 and span_values:
        # First column is usually prior-year PE; last span is the furthest forecast year.
        pe_triplet = [td_values[1], td_values[2], span_values[0]]
    elif len(td_values) >= 3:
        pe_triplet = td_values[-3:]
    else:
        return {}
    base_year = 2026
    return {base_year + offset: pe_triplet[offset] for offset in range(len(pe_triplet))}


def _pe_band(pe_mid: float) -> dict[str, float]:
    return {
        "low": round(pe_mid * 0.95, 2),
        "mid": round(pe_mid, 2),
        "high": round(pe_mid * 1.05, 2),
    }


def _parse_reference_year(html: str) -> int | None:
    match = re.search(r"预测20(\d{2})年每股收益", html)
    if match:
        return 2000 + int(match.group(1))
    match = re.search(r"20(\d{2})（实际值）", html)
    if match:
        return 2000 + int(match.group(1)) - 1
    return None


def fetch_ths_worth_consensus(stock_code: str) -> dict[str, Any]:
    """Fetch EPS / PE consensus bands from Tonghuashun worth.html."""
    code = stock_code.zfill(6)
    url = f"https://basic.10jqka.com.cn/new/{code}/worth.html"
    try:
        html = _throttled_fetch(url)
    except Exception as exc:
        logger.warning("THS worth fetch failed for %s: %s", code, exc)
        return {
            "found": False,
            "stock_code": code,
            "source": url,
            "data_origin": "ths_worth_consensus",
            "notes": f"同花顺 worth 页请求失败: {exc}",
        }

    eps_bands = _parse_eps_forecast_table(html)
    pe_by_year = _parse_dynamic_pe_by_year(html)
    reference_year = _parse_reference_year(html)

    if not eps_bands:
        return {
            "found": False,
            "stock_code": code,
            "source": url,
            "data_origin": "ths_worth_consensus",
            "notes": "同花顺页面未解析到 EPS 一致预期表",
        }

    years_payload: dict[str, Any] = {}
    for band in eps_bands:
        year_key = str(band.year)
        pe_mid = pe_by_year.get(band.year)
        if pe_mid is None:
            continue
        pe_payload = _pe_band(pe_mid)
        years_payload[year_key] = {
            "year": band.year,
            "analyst_count": band.analyst_count,
            "eps": {"low": band.low, "mid": band.mid, "high": band.high},
            "pe": pe_payload,
        }

    return {
        "found": bool(years_payload),
        "stock_code": code,
        "reference_year": reference_year,
        "years": years_payload,
        "source": url,
        "data_origin": "ths_worth_consensus",
        "notes": "同花顺机构一致预期 EPS + 动态 PE",
    }
