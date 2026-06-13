"""Detect explicit user requests for sector heatmap rich component."""

from __future__ import annotations

_HEATMAP_KEYWORDS: tuple[str, ...] = (
    "热力图",
    "热图",
    "板块地图",
    "板块全景",
    "行业全景",
    "行业热力",
    "板块热度图",
    "板块热度",
    "板块一览",
    "行业涨跌一览",
    "板块涨跌图",
    "行业板块图",
    "板块分布图",
)


def wants_sector_heatmap(query: str) -> bool:
    """Return True when the user explicitly asks for a sector/board heatmap view."""
    normalized = query.strip()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in _HEATMAP_KEYWORDS)
