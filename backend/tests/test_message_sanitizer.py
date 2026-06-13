"""Tests for assistant message sanitization."""

from __future__ import annotations

from backend.src.services.message_sanitizer import sanitize_assistant_content, sanitize_rich_blocks


def test_real_stock_answer_content_is_preserved() -> None:
    content = "泸州老窖 2025A 营收 312.5 亿元，毛利率 88.2%，ROE 28.6%。"
    assert sanitize_assistant_content("assistant", content) == content


def test_legacy_stock_boilerplate_is_stripped_not_replaced_with_fixed_stock() -> None:
    legacy = "已根据本地模拟数据生成个股基本面信息卡，并附上引用来源和风险提示。"
    assert sanitize_assistant_content("assistant", legacy) == ""


def test_internal_engineering_lines_are_removed_but_answer_kept() -> None:
    content = (
        "泸州老窖盈利能力仍处修复通道。\n"
        "当前回答由演示级 Agent fallback 链路生成，用于验证路由。\n"
        "毛利率与 ROE 仍需继续跟踪。"
    )
    cleaned = sanitize_assistant_content("assistant", content)
    assert "fallback" not in cleaned
    assert "泸州老窖盈利能力仍处修复通道" in cleaned
    assert "毛利率与 ROE 仍需继续跟踪" in cleaned


def test_deprecated_rich_blocks_are_filtered() -> None:
    blocks = [
        {
            "id": "stock_1",
            "type": "stock_card",
            "title": "个股基本面信息卡",
            "payload": {
                "name": "泸州老窖",
                "code": "000568.SZ",
                "metrics": {
                    "rows": [{"metric": "营业收入", "value": "312.5亿元", "period": "2025A", "note": ""}],
                },
            },
            "sources": [{"type": "financial", "label": "本地 mock 财务画像", "time": "2025A"}],
            "risk_notice": "",
        },
        {
            "id": "rank_1",
            "type": "ranking_table",
            "title": "涨幅排行",
            "payload": {
                "columns": ["rank", "name"],
                "rows": [{"rank": 1, "name": "寒武纪"}],
            },
            "sources": [],
            "risk_notice": "以上内容仅为信息整理，不构成投资建议。",
        },
    ]
    sanitized = sanitize_rich_blocks("assistant", blocks)
    assert [block["type"] for block in sanitized] == ["ranking_table"]
