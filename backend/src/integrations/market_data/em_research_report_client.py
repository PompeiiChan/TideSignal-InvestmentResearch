"""Eastmoney reportapi — research report list metadata (titles, ratings, EPS)."""

from __future__ import annotations

import logging
from typing import Any

from .eastmoney_client import em_get

logger = logging.getLogger(__name__)

REPORT_API = "https://reportapi.eastmoney.com/report/list"
PDF_URL_TEMPLATE = "https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"
ATTRIBUTION = "third_party/a-stock-data (Apache-2.0)"


def _parse_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _normalize_report_row(row: dict[str, Any]) -> dict[str, Any]:
    info_code = str(row.get("infoCode") or "").strip()
    pdf_url = PDF_URL_TEMPLATE.format(info_code=info_code) if info_code else ""
    rating_change = str(row.get("ratingChange") or row.get("emRatingChangeName") or "").strip()
    return {
        "title": str(row.get("title") or "").strip(),
        "org_name": str(row.get("orgSName") or row.get("orgName") or "").strip(),
        "publish_date": str(row.get("publishDate") or "")[:10],
        "rating": str(row.get("emRatingName") or row.get("rating") or "").strip(),
        "rating_change": rating_change,
        "predict_this_year_eps": _parse_optional_float(row.get("predictThisYearEps")),
        "predict_next_year_eps": _parse_optional_float(row.get("predictNextYearEps")),
        "pdf_url": pdf_url,
    }


def fetch_em_research_report_rows(
    stock_code: str,
    *,
    page_size: int = 50,
    max_pages: int = 2,
) -> list[dict[str, Any]]:
    """Fetch raw reportapi rows for a stock (shared by consensus aggregation and metadata tools)."""
    code = stock_code.zfill(6)
    records: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        params = {
            "industryCode": "*",
            "pageSize": str(page_size),
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
                REPORT_API,
                params=params,
                headers={"Referer": "https://data.eastmoney.com/"},
                timeout=20,
            )
            payload = response.json()
        except Exception as exc:
            logger.warning("Eastmoney reportapi list failed for %s page %s: %s", code, page, exc)
            break
        rows = payload.get("data") or []
        if not rows:
            break
        records.extend(rows)
        total_page = int(payload.get("TotalPage") or 1)
        if page >= total_page:
            break
    return records


def _build_rating_summary(reports: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for report in reports:
        rating = str(report.get("rating") or "").strip()
        if not rating:
            continue
        summary[rating] = summary.get(rating, 0) + 1
    return summary


def fetch_em_research_reports(
    stock_code: str,
    *,
    page_size: int = 20,
    max_pages: int = 2,
) -> dict[str, Any]:
    """Return normalized research-report metadata for agent tools."""
    code = stock_code.zfill(6)
    rows = fetch_em_research_report_rows(code, page_size=max(page_size, 50), max_pages=max_pages)
    reports = [_normalize_report_row(row) for row in rows]
    reports = [item for item in reports if item.get("title")]
    reports.sort(key=lambda item: str(item.get("publish_date", "")), reverse=True)
    reports = reports[:page_size]

    if not reports:
        return {
            "found": False,
            "stock_code": code,
            "reports": [],
            "report_count": 0,
            "rating_summary": {},
            "source": REPORT_API,
            "data_origin": "eastmoney_reportapi",
            "notes": "东财研报列表无记录",
        }

    return {
        "found": True,
        "stock_code": code,
        "reports": reports,
        "report_count": len(reports),
        "rating_summary": _build_rating_summary(reports),
        "source": REPORT_API,
        "data_origin": "eastmoney_reportapi",
        "notes": f"东财研报元数据 {len(reports)} 条",
    }
