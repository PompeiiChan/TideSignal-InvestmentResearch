"""Eastmoney reportapi fallback for EPS / implied PE bands."""

from __future__ import annotations

import logging
import re
from typing import Any

from .eastmoney_client import em_get

logger = logging.getLogger(__name__)

_REPORT_API = "https://reportapi.eastmoney.com/report/list"
_PE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*倍\s*(?:PE|市盈率|pe)", re.IGNORECASE)


def _stats(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {
        "low": min(values),
        "mid": sum(values) / len(values),
        "high": max(values),
    }


def fetch_em_report_consensus(
    stock_code: str,
    *,
    current_price: float | None = None,
    max_pages: int = 3,
) -> dict[str, Any]:
    """Aggregate EPS / PE hints from recent Eastmoney research reports."""
    code = stock_code.zfill(6)
    records: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        params = {
            "industryCode": "*",
            "pageSize": "50",
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": "2024-01-01",
            "endTime": "2030-12-31",
            "pageNo": str(page),
            "fields": "",
            "qType": "0",
            "orgCode": "",
            "code": code,
            "rcode": "",
            "p": str(page),
            "pageNum": str(page),
            "pageNumber": str(page),
        }
        try:
            response = em_get(
                _REPORT_API,
                params=params,
                headers={"Referer": "https://data.eastmoney.com/"},
                timeout=20,
            )
            payload = response.json()
        except Exception as exc:
            logger.warning("Eastmoney reportapi failed for %s page %s: %s", code, page, exc)
            break
        rows = payload.get("data") or []
        if not rows:
            break
        records.extend(rows)
        total_page = int(payload.get("TotalPage") or 1)
        if page >= total_page:
            break

    if not records:
        return {
            "found": False,
            "stock_code": code,
            "source": _REPORT_API,
            "data_origin": "eastmoney_reportapi",
            "notes": "东财研报列表无记录",
        }

    eps_this: list[float] = []
    eps_next: list[float] = []
    eps_two: list[float] = []
    pe_values: list[float] = []
    for row in records:
        for key, bucket in (
            ("predictThisYearEps", eps_this),
            ("predictNextYearEps", eps_next),
            ("predictNextTwoYearEps", eps_two),
        ):
            raw = row.get(key)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if value > 0:
                bucket.append(value)
        title = str(row.get("title", ""))
        for match in _PE_RE.finditer(title):
            pe_values.append(float(match.group(1)))

    years: dict[str, Any] = {}
    mapping = (
        ("2026", eps_this),
        ("2027", eps_next),
        ("2028", eps_two),
    )
    pe_band = _stats(pe_values)
    for year_label, bucket in mapping:
        eps_band = _stats(bucket)
        if not eps_band:
            continue
        pe_payload: dict[str, float]
        if pe_band:
            pe_payload = pe_band
        elif current_price and eps_band["mid"] > 0:
            pe_mid = current_price / eps_band["mid"]
            pe_payload = {
                "low": round(pe_mid * 0.95, 2),
                "mid": round(pe_mid, 2),
                "high": round(pe_mid * 1.05, 2),
            }
        else:
            continue
        years[year_label] = {
            "year": int(year_label),
            "analyst_count": len(bucket),
            "eps": {k: round(v, 4) for k, v in eps_band.items()},
            "pe": {k: round(v, 2) for k, v in pe_payload.items()},
        }

    return {
        "found": bool(years),
        "stock_code": code,
        "reference_year": 2025,
        "years": years,
        "source": _REPORT_API,
        "data_origin": "eastmoney_reportapi",
        "notes": "东财研报 EPS 聚合 + 隐含/正文 PE",
        "report_count": len(records),
    }
