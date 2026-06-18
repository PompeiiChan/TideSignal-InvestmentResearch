"""Tencent Finance realtime quote client for valuation metrics."""

from __future__ import annotations

import time
import urllib.request
from typing import Any

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_last_call = 0.0
_MIN_INTERVAL = 0.5


def paper_code_for(stock_code: str) -> str:
    code = stock_code.zfill(6)
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return f"sz{code}"


def _throttled_fetch(url: str) -> str:
    global _last_call
    wait = _MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    request = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = str(response.read().decode("gbk", errors="replace"))
        _last_call = time.time()
        return payload
    except Exception:
        _last_call = time.time()
        raise


def _parse_float(raw: str) -> float | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fetch_quote_snapshot(stock_code: str, *, stock_name: str = "") -> dict[str, Any] | None:
    """Return latest price and valuation fields from Tencent qt.gtimg.cn."""
    code = stock_code.zfill(6)
    if len(code) != 6:
        return None
    url = f"https://qt.gtimg.cn/q={paper_code_for(code)}"
    payload = _throttled_fetch(url)
    quoted = payload.split('"')
    if len(quoted) < 2:
        return None
    vals = quoted[1].split("~")
    if len(vals) < 47:
        return None

    price = _parse_float(vals[3])
    if price is None or price <= 0:
        return None

    from .stock_code_resolver import format_ticker

    name = (stock_name or vals[1] or code).strip()
    pe_ttm = _parse_float(vals[39])
    pb = _parse_float(vals[46])
    mcap_raw = _parse_float(vals[44])

    return {
        "stock_name": name,
        "ticker": format_ticker(code),
        "price": round(price, 2),
        "pe_ttm": round(pe_ttm, 2) if pe_ttm is not None else None,
        "pb": round(pb, 2) if pb is not None else None,
        "market_cap_yi": round(mcap_raw, 2) if mcap_raw is not None else None,
        "change_pct": _parse_float(vals[32]),
        "source": "https://qt.gtimg.cn/",
    }
