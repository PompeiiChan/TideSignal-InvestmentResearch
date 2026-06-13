"""Tests for multi-period financial profile support."""

from __future__ import annotations

from unittest.mock import patch

from backend.src.integrations.market_data.sina_finance_client import (
    PeriodSnapshot,
    build_profile_from_snapshot,
    select_multi_period_keys,
    sort_profiles_by_period,
)
from backend.src.services.rag.chunker import resolve_kb_root
from backend.src.services.rag.kb_financial_loader import (
    find_financial_kb_file,
    load_all_profiles_from_kb_file,
)
from backend.src.settings import BACKEND_ROOT, AppSettings


def test_select_multi_period_keys_prefers_latest_quarter_and_three_annuals() -> None:
    keys = {
        "20260331": {},
        "20251231": {},
        "20241231": {},
        "20231231": {},
        "20221231": {},
        "20211231": {},
    }
    selected = select_multi_period_keys(keys, max_annual=3)
    assert selected == ["20260331", "20251231", "20241231", "20231231"]


def test_select_multi_period_keys_when_latest_is_annual() -> None:
    keys = {
        "20251231": {},
        "20241231": {},
        "20231231": {},
    }
    selected = select_multi_period_keys(keys, max_annual=3)
    assert selected == ["20251231", "20241231", "20231231"]


def test_sort_profiles_by_period_descending() -> None:
    profiles = [
        {"time_period": "2024A"},
        {"time_period": "2026Q1"},
        {"time_period": "2025A"},
    ]
    sorted_profiles = sort_profiles_by_period(profiles)
    assert [item["time_period"] for item in sorted_profiles] == ["2026Q1", "2025A", "2024A"]


@patch("backend.src.integrations.market_data.sina_finance_client.fetch_report_list")
def test_fetch_multi_period_profiles_builds_multiple_snapshots(mock_fetch: object) -> None:
    from backend.src.integrations.market_data.sina_finance_client import fetch_multi_period_profiles

    def _side_effect(_code: str, report_type: str, **_kwargs: object) -> dict[str, dict]:
        if report_type == "lrb":
            return {
                "20260331": {
                    "data": [
                        {"item_title": "营业收入", "item_value": "100000000"},
                        {"item_title": "归属于母公司所有者的净利润", "item_value": "20000000"},
                        {"item_title": "营业成本", "item_value": "60000000"},
                    ]
                },
                "20251231": {
                    "data": [
                        {"item_title": "营业收入", "item_value": "400000000"},
                        {"item_title": "归属于母公司所有者的净利润", "item_value": "80000000"},
                        {"item_title": "营业成本", "item_value": "240000000"},
                    ]
                },
            }
        return {
            "20260331": {"data": [{"item_title": "归属于母公司所有者权益合计", "item_value": "500000000"}]},
            "20251231": {"data": [{"item_title": "归属于母公司所有者权益合计", "item_value": "480000000"}]},
        }

    mock_fetch.side_effect = _side_effect
    profiles = fetch_multi_period_profiles("603027", stock_name="千禾味业", max_annual=1)
    assert len(profiles) == 2
    assert profiles[0]["time_period"] == "2026Q1"
    assert profiles[1]["time_period"] == "2025A"


def test_kb_loader_reads_multiple_period_sections() -> None:
    settings = AppSettings()
    kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)
    path = find_financial_kb_file(kb_root, "300296")
    assert path is not None
    profiles = load_all_profiles_from_kb_file(path, stock_name="利亚德", stock_code="300296")
    periods = [profile["time_period"] for profile in profiles]
    assert "2026Q1" in periods
    assert "2025A" in periods
    assert profiles[0]["time_period"] == "2026Q1"


def test_build_profile_from_snapshot_includes_period_key() -> None:
    snapshot = PeriodSnapshot(
        period_key="20251231",
        lrb={
            "营业收入": "400000000",
            "营业成本": "240000000",
            "归属于母公司所有者的净利润": "80000000",
        },
        fzb={"归属于母公司所有者权益合计": "480000000"},
    )
    profile = build_profile_from_snapshot(snapshot, stock_name="测试", stock_code="603027")
    assert profile is not None
    assert profile["time_period"] == "2025A"
    assert profile["period_key"] == "20251231"
