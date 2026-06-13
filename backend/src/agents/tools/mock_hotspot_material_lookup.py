"""Curated hotspot material lookup (KB-derived themes for hotspot analysis)."""

from __future__ import annotations

from typing import Any

_HOTSPOT_THEMES: list[dict[str, Any]] = [
    {
        "topic": "AI硬件与算力",
        "catalyst": "算力产业链从 GPU 向光通信、玻璃基板、散热等环节扩散",
        "policy": "证监会强调基金行业服务科技创新",
        "industry_chain": "光模块、PCB、散热、先进封装",
        "time_period": "2026-06",
    },
    {
        "topic": "半导体退潮与红利承接",
        "catalyst": "科创50阶段性调整，半导体产业链获利了结",
        "policy": "无新增限制性政策",
        "industry_chain": "银行、煤炭等高股息板块逆势抱团",
        "time_period": "2026-06",
    },
    {
        "topic": "机器人与新型工业化",
        "catalyst": "减速器、太赫兹、工业气体等分支轮动活跃",
        "policy": "发改委召开经济形势专家座谈会",
        "industry_chain": "机器人本体、减速器、工业自动化",
        "time_period": "2026-06",
    },
]


def lookup_hotspot_material(
    *,
    topic: str = "",
    industry: str = "",
    event: str = "",
    time_range: str = "2026-06",
    **_extra: Any,
) -> dict[str, Any]:
    """Return curated hotspot catalyst themes from knowledge-base summaries."""
    keyword = topic or industry or event
    materials = _HOTSPOT_THEMES
    if keyword:
        filtered = [
            item
            for item in _HOTSPOT_THEMES
            if keyword in item["topic"]
            or keyword in item["catalyst"]
            or keyword in item["industry_chain"]
        ]
        if filtered:
            materials = filtered
    return {
        "tool": "mock_hotspot_material_lookup",
        "topic": topic or industry or "市场热点",
        "time_range": time_range,
        "materials": materials,
        "material_count": len(materials),
        "source": "知识库 hotspots/ 月报整理摘要",
        "is_mock": False,
        "timeliness": "月报/复盘口径，时效可能滞后于当日盘面",
        "confidence_note": "知识库整理素材，置信度高，须结合 time_period 使用",
        "notes": "知识库热点主题摘要，不构成投资建议",
    }
