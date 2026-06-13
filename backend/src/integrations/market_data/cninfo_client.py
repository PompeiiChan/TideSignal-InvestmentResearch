"""Cninfo (巨潮) announcement client."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from .eastmoney_client import UA

_CNINFO_ORG_MAP: dict[str, str] = {}
_CNINFO_QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
_CNINFO_STOCK_MAP_URL = "http://www.cninfo.com.cn/new/data/szse_stock.json"


def _cninfo_ts_to_date(ts: Any) -> str:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
    return str(ts)[:10] if ts else ""


def resolve_cninfo_org_id(code: str) -> str:
    """Resolve stock orgId from official mapping table with hardcoded fallback."""
    global _CNINFO_ORG_MAP
    normalized = str(code).zfill(6)
    if not _CNINFO_ORG_MAP:
        try:
            response = requests.get(
                _CNINFO_STOCK_MAP_URL,
                headers={"User-Agent": UA},
                timeout=15,
            )
            response.raise_for_status()
            _CNINFO_ORG_MAP = {
                str(item.get("code", "")).zfill(6): str(item.get("orgId", ""))
                for item in response.json().get("stockList", [])
                if isinstance(item, dict)
            }
        except Exception:
            _CNINFO_ORG_MAP = {}

    org = _CNINFO_ORG_MAP.get(normalized)
    if org:
        return org
    if normalized.startswith("6"):
        return f"gssh0{normalized}"
    if normalized.startswith(("8", "4")):
        return f"gsbj0{normalized}"
    return f"gssz0{normalized}"


def fetch_cninfo_announcements(code: str, *, page_size: int = 20) -> list[dict[str, Any]]:
    """Fetch recent cninfo announcements for one stock."""
    normalized = str(code).zfill(6)
    org_id = resolve_cninfo_org_id(normalized)
    payload = {
        "stock": f"{normalized},{org_id}",
        "tabName": "fulltext",
        "pageSize": str(page_size),
        "pageNum": "1",
        "column": "",
        "category": "",
        "plate": "",
        "seDate": "",
        "searchkey": "",
        "secid": "",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    headers = {
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.cninfo.com.cn/new/disclosure",
        "Origin": "https://www.cninfo.com.cn",
    }
    response = requests.post(_CNINFO_QUERY_URL, data=payload, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    rows: list[dict[str, Any]] = []
    for item in data.get("announcements", []) or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "code": normalized,
                "title": str(item.get("announcementTitle", "")),
                "type": str(item.get("announcementTypeName", "")),
                "date": _cninfo_ts_to_date(item.get("announcementTime")),
                "url": (
                    "https://www.cninfo.com.cn/new/disclosure/detail"
                    f"?annoId={item.get('announcementId', '')}"
                ),
            }
        )
    return rows
