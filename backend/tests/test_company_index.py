"""Tests for company directory lookup used in slot enrichment and clarification."""

from __future__ import annotations

from pathlib import Path

from backend.src.services.rag.chunker import resolve_kb_root
from backend.src.services.rag.company_index import (
    enrich_stock_slots_from_kb,
    is_kb_resolved_stock,
    is_truly_ambiguous_stock_name,
)
from backend.src.settings import BACKEND_ROOT, AppSettings


def _kb_root() -> Path:
    settings = AppSettings()
    return resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)


def test_enrich_stock_slots_fills_haitian_code() -> None:
    kb_root = _kb_root()
    slots = enrich_stock_slots_from_kb(
        "海天味业基本面怎么样",
        {"stock_name": "海天味业", "analysis_dimension": "基本面"},
        kb_root,
    )
    assert slots["stock_name"] == "海天味业"
    assert slots["stock_code"] == "603288.SH"


def test_is_kb_resolved_stock_for_haitian() -> None:
    kb_root = _kb_root()
    assert is_kb_resolved_stock(
        "海天味业基本面怎么样",
        {"stock_name": "海天味业"},
        kb_root,
    )


def test_is_truly_ambiguous_stock_name() -> None:
    assert is_truly_ambiguous_stock_name("茅台") is True
    assert is_truly_ambiguous_stock_name("海天味业") is False
