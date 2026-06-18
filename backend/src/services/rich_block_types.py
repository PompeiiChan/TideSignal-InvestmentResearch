"""Helpers for exposing rich block types on session list items."""

from __future__ import annotations

from typing import Any

from .message_sanitizer import ALLOWED_RICH_BLOCK_TYPES, sanitize_rich_blocks

_RICH_BLOCK_ORDER = (
    "ranking_table",
    "sector_heatmap",
    "calculator",
    "scenario_calculator",
)


def extract_rich_block_types(rich_blocks: list[Any], *, role: str = "assistant") -> list[str]:
    """Return ordered unique UI rich block types from a message payload."""
    sanitized = sanitize_rich_blocks(role, rich_blocks if isinstance(rich_blocks, list) else [])
    seen: set[str] = set()
    ordered: list[str] = []
    for block_type in _RICH_BLOCK_ORDER:
        if block_type in seen:
            continue
        if any(str(block.get("type", "")) == block_type for block in sanitized):
            ordered.append(block_type)
            seen.add(block_type)
    for block in sanitized:
        block_type = str(block.get("type", ""))
        if block_type in ALLOWED_RICH_BLOCK_TYPES and block_type not in seen:
            ordered.append(block_type)
            seen.add(block_type)
    return ordered
