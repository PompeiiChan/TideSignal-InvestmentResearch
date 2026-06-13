"""Sanitize persisted assistant messages before returning them to UI clients."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

PUBLIC_RISK_NOTICE = "以上内容仅为信息整理，不构成投资建议。"

_INTERNAL_SUMMARY_TITLES = {"Agent fallback 回答摘要", "fallback 回答摘要"}
_INTERNAL_PHRASES = (
    "当前回答由演示级 Agent fallback 链路生成",
    "Agent fallback",
    "fallback 链路",
    "fallback 规则",
    "真实 LLM",
    "LangGraph",
    "用于验证路由",
)
_LEGACY_STOCK_BOILERPLATE = "已根据本地模拟数据生成个股基本面信息卡，并附上引用来源和风险提示"
_LEGACY_CONTENT_REPLACEMENTS = {
    _LEGACY_STOCK_BOILERPLATE: "",
    f"{_LEGACY_STOCK_BOILERPLATE}。": "",
    "已路由到热点助手，基于本地模拟研报与公告生成热点归因摘要。": "下面整理热点归因摘要。",
    "已路由到问数助手，基于本地模拟行情生成结构化排行回答。": "下面是相关行情数据整理。",
}

ALLOWED_RICH_BLOCK_TYPES = frozenset({"ranking_table", "calculator", "sector_heatmap"})
DEPRECATED_RICH_BLOCK_TYPES = frozenset(
    {
        "text",
        "stock_card",
        "metric_table",
        "trace_summary",
        "citation_list",
        "risk_notice",
        "hotspot",
    }
)


def _strip_internal_lines(content: str) -> str:
    """Remove engineering-only lines while preserving user-visible answer text."""
    lines = [line.strip() for line in content.splitlines()]
    public_lines = [
        line
        for line in lines
        if line and not line.startswith("问题：") and not any(phrase in line for phrase in _INTERNAL_PHRASES)
    ]
    return "\n".join(public_lines).strip()


def sanitize_assistant_content(role: str, content: str) -> str:
    """Remove internal orchestration wording from assistant-visible content."""
    if role != "assistant":
        return content

    normalized = content.strip()
    if not normalized:
        return content

    if _LEGACY_STOCK_BOILERPLATE in normalized:
        return _strip_internal_lines(normalized.replace(_LEGACY_STOCK_BOILERPLATE, "").replace("。", ""))

    if normalized in _LEGACY_CONTENT_REPLACEMENTS:
        return _LEGACY_CONTENT_REPLACEMENTS[normalized]

    if not any(phrase in normalized for phrase in _INTERNAL_PHRASES):
        return content

    cleaned = _strip_internal_lines(normalized)
    return cleaned if cleaned else content


def sanitize_rich_blocks(role: str, rich_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return UI-safe rich blocks; only interactive ranking_table / calculator are kept."""
    if role != "assistant":
        return rich_blocks

    sanitized: list[dict[str, Any]] = []
    for block in rich_blocks:
        if _is_internal_summary_block(block):
            continue
        block_type = str(block.get("type", ""))
        if block_type in DEPRECATED_RICH_BLOCK_TYPES:
            continue
        if block_type not in ALLOWED_RICH_BLOCK_TYPES:
            continue
        next_block = _sanitize_block(block)
        if next_block.get("payload"):
            sanitized.append(next_block)
    return sanitized


def _is_internal_summary_block(block: dict[str, Any]) -> bool:
    title = str(block.get("title", ""))
    if title in _INTERNAL_SUMMARY_TITLES:
        return True
    payload = block.get("payload")
    paragraphs = payload.get("paragraphs", []) if isinstance(payload, dict) else []
    return any(any(phrase in str(paragraph) for phrase in _INTERNAL_PHRASES) for paragraph in paragraphs)


def _sanitize_block(block: dict[str, Any]) -> dict[str, Any]:
    next_block = deepcopy(block)
    raw_risk = str(next_block.get("risk_notice", ""))
    if raw_risk and not any(phrase in raw_risk for phrase in _INTERNAL_PHRASES):
        next_block["risk_notice"] = raw_risk
    else:
        next_block["risk_notice"] = PUBLIC_RISK_NOTICE
    return next_block
