"""Company name / ticker lookup for query-side metadata filtering."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)

# Short names that may refer to a stock, sector, or concept — keep clarification path.
_AMBIGUOUS_STOCK_NAMES = frozenset(
    {
        "茅台",
        "贵州茅台",
        "苹果",
        "平安",
        "招行",
        "中行",
        "建行",
        "工行",
    }
)


def load_company_aliases(kb_root: Path) -> dict[str, str]:
    """Map company names and tickers to company_id."""
    directory = load_company_directory(kb_root)
    aliases: dict[str, str] = {}
    for company_id, record in directory.items():
        name = str(record.get("company_name", "")).strip()
        ticker = str(record.get("ticker", "")).strip()
        if name:
            aliases[name] = company_id
        ticker_code = ticker.split(".")[0]
        if ticker_code:
            aliases[ticker_code] = company_id
    return aliases


def load_company_directory(kb_root: Path) -> dict[str, dict[str, str]]:
    """Map company_id to canonical name and ticker."""
    path = kb_root / "structured-data" / "companies.md"
    if not path.exists():
        return {}

    records: dict[str, dict[str, str]] = {}
    in_data = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "## 数据":
            in_data = True
            continue
        if not in_data or not line.strip().startswith("|"):
            continue
        if "company_id" in line or set(line.strip()) <= {"|", "-", " "}:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        company_id, company_name, ticker = cells[0], cells[1], cells[2]
        if not company_id.startswith("company_"):
            continue
        records[company_id] = {
            "company_id": company_id,
            "company_name": company_name,
            "ticker": ticker,
        }
    return records


def resolve_query_filters(query: str, aliases: dict[str, str]) -> dict[str, str]:
    """Infer hard-filter hints from a natural-language query."""
    company_id = ""
    for name, cid in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if name and name in query:
            company_id = cid
            break

    doc_type = ""
    if any(term in query for term in ("一季报", "第一季度", "季报", "Q1")):
        doc_type = "quarterly_report"
    elif "年报" in query:
        doc_type = "annual_report"
    elif any(term in query for term in ("研报", "深度研究", "投资要点")):
        doc_type = "company_research"

    return {"company_id": company_id, "doc_type": doc_type}


def _match_company_id(
    query: str,
    slots: dict[str, Any],
    aliases: dict[str, str],
) -> str:
    stock_name = str(slots.get("stock_name", "")).strip()
    if stock_name and stock_name in aliases:
        return aliases[stock_name]

    for name, company_id in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if not name or len(name) < 2:
            continue
        if stock_name and name in stock_name:
            return company_id
        if stock_name and stock_name in name:
            return company_id

    return resolve_query_filters(query, aliases).get("company_id", "")


def is_truly_ambiguous_stock_name(stock_name: str) -> bool:
    """Return True when a short alias may refer to multiple investable subjects."""
    normalized = stock_name.strip()
    if not normalized:
        return False
    if normalized in _AMBIGUOUS_STOCK_NAMES:
        return True
    return any(normalized == item or normalized.startswith(f"{item}") for item in _AMBIGUOUS_STOCK_NAMES)


def enrich_stock_slots_from_kb(
    query: str,
    slots: dict[str, Any],
    kb_root: Path,
) -> dict[str, Any]:
    """Fill stock_name / stock_code from the local company directory when uniquely matched."""
    directory = load_company_directory(kb_root)
    if not directory:
        return dict(slots)

    aliases = load_company_aliases(kb_root)
    company_id = _match_company_id(query, slots, aliases)
    if not company_id:
        return dict(slots)

    record = directory.get(company_id, {})
    enriched = dict(slots)
    canonical_name = str(record.get("company_name", "")).strip()
    ticker = str(record.get("ticker", "")).strip()

    if canonical_name and not str(enriched.get("stock_name", "")).strip():
        enriched["stock_name"] = canonical_name
    if ticker:
        enriched["stock_code"] = ticker
    return enriched


def is_kb_resolved_stock(query: str, slots: dict[str, Any], kb_root: Path) -> bool:
    """Whether query/slots uniquely map to a company in the local KB directory."""
    aliases = load_company_aliases(kb_root)
    company_id = _match_company_id(query, slots, aliases)
    return bool(company_id)
