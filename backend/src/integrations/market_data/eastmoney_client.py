"""Eastmoney push2 client — throttled HTTP helpers for board and stock rankings.

Adapted from simonlin1212/a-stock-data (SKILL.md §3.7, Apache-2.0).
Reference: Projects_Repo/smart-investment-research/third_party/a-stock-data/SKILL.md
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"

# Industry boards (m:90+t:2) and concept boards (m:90+t:3)
BOARD_FS_FILTERS = {
    "industry": "m:90+t:2",
    "concept": "m:90+t:3",
}

_EM_SESSION = requests.Session()
_EM_SESSION.headers.update({"User-Agent": UA})
_EM_MIN_INTERVAL = 1.0
_em_last_call = [0.0]


def em_get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    *,
    timeout: int = 15,
    **kwargs: Any,
) -> requests.Response:
    """Throttled Eastmoney HTTP GET (serial ≥1s + jitter)."""
    wait = _EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        return _EM_SESSION.get(url, params=params, headers=headers, timeout=timeout, **kwargs)
    finally:
        _em_last_call[0] = time.time()


def _shanghai_now() -> datetime:
    return datetime.now(tz=ZoneInfo("Asia/Shanghai"))


def _ticker_from_em(code: str, market: int | str | None) -> str:
    normalized = str(code).zfill(6)
    market_id = int(market) if market is not None else 0
    if market_id == 1:
        return f"{normalized}.SH"
    if market_id in {105, 116}:
        return f"{normalized}.BJ"
    return f"{normalized}.SZ"


def _parse_clist_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    diff = payload.get("data", {}).get("diff")
    if not diff:
        return []
    if isinstance(diff, dict):
        return [item for item in diff.values() if isinstance(item, dict)]
    if isinstance(diff, list):
        return [item for item in diff if isinstance(item, dict)]
    return []


def fetch_board_list(board_kind: str = "concept", *, page_size: int = 100) -> list[dict[str, Any]]:
    """Fetch all industry or concept boards sorted by change % descending."""
    fs = BOARD_FS_FILTERS.get(board_kind, BOARD_FS_FILTERS["concept"])
    params = {
        "pn": "1",
        "pz": str(page_size),
        "po": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fs": fs,
        "fields": "f2,f3,f4,f6,f12,f13,f14,f104,f105,f128,f136,f140,f141,f207",
    }
    response = em_get(CLIST_URL, params=params, headers={"User-Agent": UA}, timeout=15)
    response.raise_for_status()
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(_parse_clist_items(response.json()), start=1):
        rows.append(
            {
                "rank": index,
                "board_code": str(item.get("f12", "")),
                "board_name": str(item.get("f14", "")),
                "change_pct": _safe_float(item.get("f3")),
                "turnover_amount": _safe_float(item.get("f6")),
                "up_count": int(item.get("f104") or 0),
                "down_count": int(item.get("f105") or 0),
                "leader": str(item.get("f140", "")),
                "leader_change": _safe_float(item.get("f136")),
            }
        )
    return rows


def find_board_by_keyword(keyword: str) -> dict[str, Any] | None:
    """Match a board by name across concept then industry lists."""
    needle = keyword.strip()
    if not needle:
        return None
    for kind in ("concept", "industry"):
        for board in fetch_board_list(kind):
            name = board.get("board_name", "")
            if needle in name or name in needle:
                return {**board, "board_kind": kind}
    return None


def fetch_board_stock_ranking(
    board_code: str,
    *,
    limit: int = 10,
    descending: bool = True,
) -> list[dict[str, Any]]:
    """Return constituent stocks of a board sorted by intraday change %."""
    params = {
        "pn": "1",
        "pz": str(max(limit, 20)),
        "po": "1" if descending else "0",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": f"b:{board_code}",
        "fields": "f2,f3,f6,f12,f13,f14",
    }
    response = em_get(CLIST_URL, params=params, headers={"User-Agent": UA}, timeout=15)
    response.raise_for_status()
    trade_date = _shanghai_now().strftime("%Y-%m-%d")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(_parse_clist_items(response.json())[:limit], start=1):
        code = str(item.get("f12", "")).zfill(6)
        rows.append(
            {
                "rank": index,
                "trade_date": trade_date,
                "ticker": _ticker_from_em(code, item.get("f13")),
                "stock_name": str(item.get("f14", "")),
                "close_price": _safe_float(item.get("f2")),
                "pct_change": _safe_float(item.get("f3")),
                "turnover_amount": _safe_float(item.get("f6")),
                "is_mock": False,
            }
        )
    return rows


def industry_board_ranking(*, top_n: int = 20) -> dict[str, Any]:
    """Full industry board ranking (Eastmoney m:90+t:2)."""
    boards = fetch_board_list("industry", page_size=100)
    top = boards[:top_n]
    bottom = list(reversed(boards[-top_n:])) if boards else []
    return {"top": top, "bottom": bottom, "total": len(boards)}


def industry_heatmap_boards(*, limit: int = 30) -> list[dict[str, Any]]:
    """Industry boards for heatmap: top `limit` by turnover (成交额)."""
    boards = fetch_board_list("industry", page_size=100)
    ranked = sorted(boards, key=lambda item: float(item.get("turnover_amount") or 0.0), reverse=True)
    return ranked[: max(int(limit), 1)]


def _safe_float(value: Any) -> float:
    try:
        if value in (None, "", "-"):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
