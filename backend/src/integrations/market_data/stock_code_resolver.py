"""Resolve A-share 6-digit codes from ticker strings or company names."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests

from ...services.rag.company_index import enrich_stock_slots_from_kb, load_company_directory
from ...services.rag.chunker import resolve_kb_root
from ...settings import BACKEND_ROOT, AppSettings, get_settings

_EM_SUGGEST_URL = "https://searchapi.eastmoney.com/api/suggest/get"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def normalize_stock_code(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) < 6:
        return ""
    return digits[-6:].zfill(6)


def _ticker_suffix(code: str) -> str:
    if code.startswith(("6", "5")):
        return "SH"
    if code.startswith(("4", "8")):
        return "BJ"
    return "SZ"


def format_ticker(code: str) -> str:
    normalized = normalize_stock_code(code)
    if not normalized:
        return ""
    return f"{normalized}.{_ticker_suffix(normalized)}"


def _resolve_from_kb(stock_name: str, stock_code: str, kb_root: Path) -> str:
    slots = enrich_stock_slots_from_kb(
        stock_name,
        {"stock_name": stock_name, "stock_code": stock_code},
        kb_root,
    )
    return normalize_stock_code(str(slots.get("stock_code", "")))


def _resolve_from_eastmoney_suggest(stock_name: str) -> str:
    name = stock_name.strip()
    if not name:
        return ""
    try:
        response = requests.get(
            _EM_SUGGEST_URL,
            params={"input": name, "type": "14", "token": "794521197859", "count": "5"},
            headers={"User-Agent": _UA},
            timeout=10,
        )
        response.raise_for_status()
        rows = response.json().get("QuotationCodeTable", {}).get("Data") or []
    except requests.RequestException:
        return ""
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("Classify", "")).lower() not in {"astock", ""}:
            continue
        code = normalize_stock_code(str(row.get("Code", "")))
        if code:
            return code
    return ""


def resolve_stock_code(
    stock_name: str = "",
    stock_code: str = "",
    *,
    settings: AppSettings | None = None,
) -> tuple[str, str]:
    """Return (six_digit_code, resolved_stock_name)."""
    settings = settings or get_settings()
    kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)

    code = normalize_stock_code(stock_code)
    resolved_name = stock_name.strip()

    if not code and kb_root.exists():
        code = _resolve_from_kb(resolved_name, stock_code, kb_root)

    if not code and resolved_name:
        code = _resolve_from_eastmoney_suggest(resolved_name)

    if code and not resolved_name:
        directory = load_company_directory(kb_root)
        for record in directory.values():
            ticker = normalize_stock_code(str(record.get("ticker", "")))
            if ticker == code:
                resolved_name = str(record.get("company_name", "")).strip()
                break

    return code, resolved_name or stock_name.strip()
