"""Sina Finance HTTP client for runtime financial profile lookup."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

SINA_URL = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

LRB_KEYS = [
    "营业总收入",
    "营业收入",
    "营业成本",
    "营业利润",
    "利润总额",
    "净利润",
    "归属于母公司所有者的净利润",
]
FZB_KEYS = [
    "归属于母公司所有者权益合计",
    "所有者权益(或股东权益)合计",
]

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.headers.update({"User-Agent": UA})
_last_call = 0.0
_MIN_INTERVAL = 1.0
_DEFAULT_MAX_ANNUAL = 3


@dataclass(frozen=True)
class PeriodSnapshot:
    period_key: str
    lrb: dict[str, str]
    fzb: dict[str, str]


def paper_code_for(stock_code: str) -> str:
    code = stock_code.zfill(6)
    prefix = "sh" if code.startswith("6") else "sz"
    return f"{prefix}{code}"


def _throttled_get(url: str, params: dict[str, Any]) -> requests.Response:
    global _last_call
    wait = _MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    try:
        response = _SESSION.get(url, params=params, timeout=20)
        _last_call = time.time()
        response.raise_for_status()
        return response
    except requests.RequestException:
        _last_call = time.time()
        raise


def _extract_items(report_obj: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in report_obj.get("data", []) or []:
        title = str(item.get("item_title") or "").strip()
        value = item.get("item_value")
        if title and value not in (None, ""):
            out[title] = str(value)
    return out


def fetch_report_list(stock_code: str, report_type: str, *, num: int = 8) -> dict[str, dict[str, Any]]:
    params = {
        "paperCode": paper_code_for(stock_code),
        "source": report_type,
        "type": "0",
        "page": "1",
        "num": str(num),
    }
    response = _throttled_get(SINA_URL, params)
    return response.json().get("result", {}).get("data", {}).get("report_list", {}) or {}


def _pick_latest_period(report_lists: dict[str, dict[str, Any]]) -> str | None:
    keys = sorted(report_lists.keys(), reverse=True)
    return keys[0] if keys else None


def select_multi_period_keys(
    report_lists: dict[str, dict[str, Any]],
    *,
    max_annual: int = _DEFAULT_MAX_ANNUAL,
) -> list[str]:
    """Pick latest interim/quarter plus up to N most recent annual reports."""
    keys = sorted(report_lists.keys(), reverse=True)
    if not keys:
        return []

    latest = keys[0]
    annuals = [key for key in keys if key.endswith("1231")][:max_annual]
    selected: list[str] = []
    if not latest.endswith("1231"):
        selected.append(latest)
    for annual in annuals:
        if annual not in selected:
            selected.append(annual)
    if not selected:
        selected.append(latest)
    return selected


def fetch_latest_period_snapshot(stock_code: str) -> PeriodSnapshot | None:
    snapshots = fetch_multi_period_snapshots(stock_code, max_annual=1)
    return snapshots[0] if snapshots else None


def fetch_multi_period_snapshots(
    stock_code: str,
    *,
    max_annual: int = _DEFAULT_MAX_ANNUAL,
) -> list[PeriodSnapshot]:
    lrb_list = fetch_report_list(stock_code, "lrb")
    fzb_list = fetch_report_list(stock_code, "fzb")
    all_keys = set(lrb_list) | set(fzb_list)
    period_keys = select_multi_period_keys({key: {} for key in all_keys}, max_annual=max_annual)
    snapshots: list[PeriodSnapshot] = []
    for period_key in period_keys:
        lrb = _extract_items(lrb_list.get(period_key, {}))
        fzb = _extract_items(fzb_list.get(period_key, {}))
        if not lrb and not fzb:
            continue
        snapshots.append(PeriodSnapshot(period_key=period_key, lrb=lrb, fzb=fzb))
    return snapshots


def _first_value(data: dict[str, str], keys: list[str]) -> str | None:
    for key in keys:
        if key in data and data[key]:
            return data[key]
    return None


def _fmt_amount(raw: str | None) -> str:
    if raw is None:
        return "N/A"
    try:
        value = float(raw)
    except ValueError:
        return raw
    if abs(value) >= 1e8:
        return f"{value / 1e8:.2f}亿元"
    if abs(value) >= 1e4:
        return f"{value / 1e4:.2f}万元"
    return f"{value:.2f}元"


def _compute_gross_margin(lrb: dict[str, str]) -> str | None:
    revenue = _first_value(lrb, ["营业收入", "营业总收入"])
    cost = lrb.get("营业成本")
    if not revenue or not cost:
        return None
    try:
        rev, c = float(revenue), float(cost)
        if rev == 0:
            return None
        return f"{(rev - c) / rev * 100:.2f}%"
    except ValueError:
        return None


def _compute_roe(lrb: dict[str, str], fzb: dict[str, str]) -> str | None:
    profit = _first_value(lrb, ["归属于母公司所有者的净利润", "净利润"])
    equity = _first_value(fzb, FZB_KEYS)
    if not profit or not equity:
        return None
    try:
        p, e = float(profit), float(equity)
        if e == 0:
            return None
        return f"{p / e * 100:.2f}%"
    except ValueError:
        return None


def _time_period_label(period_key: str) -> str:
    if period_key.endswith("1231"):
        return f"{period_key[:4]}A"
    if period_key.endswith("0331"):
        return f"{period_key[:4]}Q1"
    month = int(period_key[4:6])
    quarter = max(1, (month - 1) // 3 + 1)
    return f"{period_key[:4]}Q{quarter}"


def period_sort_key(time_period: str) -> str:
    """Sort key for labels like 2026Q1 / 2025A (descending-friendly)."""
    if time_period.endswith("A") and len(time_period) >= 5:
        return f"{time_period[:4]}99"
    if "Q" in time_period:
        year, quarter = time_period.split("Q", maxsplit=1)
        return f"{year}{int(quarter):02d}"
    return time_period


def sort_profiles_by_period(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        profiles,
        key=lambda item: period_sort_key(str(item.get("time_period", ""))),
        reverse=True,
    )


def build_profile_from_snapshot(
    snapshot: PeriodSnapshot,
    *,
    stock_name: str,
    stock_code: str,
) -> dict[str, Any] | None:
    revenue_raw = _first_value(snapshot.lrb, ["营业收入", "营业总收入"])
    profit_raw = _first_value(snapshot.lrb, ["归属于母公司所有者的净利润", "净利润"])
    if not revenue_raw and not profit_raw:
        return None

    gross_margin = _compute_gross_margin(snapshot.lrb) or "N/A"
    roe = _compute_roe(snapshot.lrb, snapshot.fzb) or "N/A"
    time_period = _time_period_label(snapshot.period_key)
    from .stock_code_resolver import format_ticker

    highlights = [
        f"{time_period} 营收 {_fmt_amount(revenue_raw)}",
        f"归母净利润 {_fmt_amount(profit_raw)}",
        "数据来源：新浪财经公开 API",
    ]
    return {
        "company_id": f"company_{stock_code}",
        "ticker": format_ticker(stock_code),
        "stock_name": stock_name or stock_code,
        "industry": "未知",
        "time_period": time_period,
        "period_key": snapshot.period_key,
        "revenue": _fmt_amount(revenue_raw),
        "net_profit": _fmt_amount(profit_raw),
        "gross_margin": gross_margin,
        "roe": roe,
        "pe_ttm": "N/A",
        "highlights": highlights,
    }


def fetch_multi_period_profiles(
    stock_code: str,
    *,
    stock_name: str = "",
    max_annual: int = _DEFAULT_MAX_ANNUAL,
) -> list[dict[str, Any]]:
    snapshots = fetch_multi_period_snapshots(stock_code, max_annual=max_annual)
    profiles: list[dict[str, Any]] = []
    for snapshot in snapshots:
        profile = build_profile_from_snapshot(snapshot, stock_name=stock_name, stock_code=stock_code)
        if profile is not None:
            profiles.append(profile)
    return sort_profiles_by_period(profiles)


def fetch_financial_profile(stock_code: str, *, stock_name: str = "") -> dict[str, Any] | None:
    profiles = fetch_multi_period_profiles(stock_code, stock_name=stock_name)
    return profiles[0] if profiles else None
