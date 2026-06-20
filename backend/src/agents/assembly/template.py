"""Template short-circuit for simple data-query assembly paths."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...services.citation_catalog import CitationCatalog, normalize_assembly_citations
from ...services.message_sanitizer import ensure_public_risk_notice
from ..heatmap_intent import wants_sector_heatmap


def _tool_result(state: AgentState) -> dict[str, Any]:
    evidence_pack = state.get("evidence_pack") or {}
    tool_result = evidence_pack.get("tool_result")
    return tool_result if isinstance(tool_result, dict) else {}


def _has_rag_hits(state: AgentState) -> bool:
    return bool(state.get("rag_hits"))


def _format_pct(value: Any) -> str:
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return str(value)


def _template_heatmap(query: str, tool_result: dict[str, Any]) -> str | None:
    if not wants_sector_heatmap(query):
        return None
    heatmap = tool_result.get("sector_heatmap_lookup")
    if not isinstance(heatmap, dict) or not heatmap.get("tiles"):
        return None
    other_keys = {
        key
        for key in tool_result
        if key not in {"sector_heatmap_lookup"} and tool_result.get(key)
    }
    if other_keys:
        return None
    trade_date = str(heatmap.get("trade_date") or heatmap.get("time_range") or "").strip()
    tiles = heatmap.get("tiles") or []
    if not isinstance(tiles, list) or not tiles:
        return None

    sorted_tiles = sorted(
        [tile for tile in tiles if isinstance(tile, dict)],
        key=lambda item: float(item.get("turnover_amount") or item.get("pct_change") or 0),
        reverse=True,
    )
    highlights: list[str] = []
    for tile in sorted_tiles[:2]:
        name = str(tile.get("board_name") or tile.get("stock_name") or "板块").strip()
        pct = tile.get("pct_change")
        if pct is not None:
            highlights.append(f"{name}（涨跌幅 {_format_pct(pct)}）")
        else:
            highlights.append(name)

    date_line = f"截至 {trade_date} 收盘，" if trade_date else ""
    highlight_line = "、".join(highlights) if highlights else "详见下方热力图"
    body = (
        f"{date_line}行业板块热力图已生成，成交/涨跌突出的板块包括：{highlight_line}。"
        "完整板块分布与颜色映射请查看下方交互热力图组件。"
        "\n\n以上内容仅为信息整理，不构成投资建议。"
    )
    return body


def _template_ranking(tool_result: dict[str, Any], *, has_rag: bool) -> str | None:
    if has_rag:
        return None
    ranking = tool_result.get("market_ranking_lookup")
    if not isinstance(ranking, dict) or not ranking.get("rows"):
        return None
    mode = str(ranking.get("ranking_mode", ""))
    if mode == "board_stocks":
        return None
    other_keys = {
        key
        for key in tool_result
        if key not in {"market_ranking_lookup"} and tool_result.get(key)
    }
    if other_keys:
        return None

    rows = ranking.get("rows") or []
    if not isinstance(rows, list) or not rows:
        return None
    trade_date = str(ranking.get("trade_date") or ranking.get("time_range") or "").strip()
    top = rows[0] if isinstance(rows[0], dict) else {}
    leader = str(top.get("stock_name") or top.get("board_name") or "标的").strip()
    pct = top.get("pct_change")
    pct_text = _format_pct(pct) if pct is not None else "—"
    mode_label = "行业板块" if mode == "industry_boards" else "行情"
    date_prefix = f"{trade_date} " if trade_date else ""
    body = (
        f"{date_prefix}{mode_label}涨幅居前者为 **{leader}**（涨跌幅 {pct_text}）。"
        "完整排行与涨跌幅明细见下方排行表组件。"
        "\n\n以上内容仅为信息整理，不构成投资建议。"
    )
    return body


def _template_calculator(tool_result: dict[str, Any], *, has_rag: bool) -> str | None:
    if has_rag:
        return None
    calc = tool_result.get("local_return_calculator")
    if not isinstance(calc, dict) or calc.get("scenario_return_mode"):
        return None
    ranking = tool_result.get("market_ranking_lookup")
    if isinstance(ranking, dict) and ranking.get("rows"):
        return None
    other_keys = {
        key
        for key in tool_result
        if key not in {"local_return_calculator"} and tool_result.get(key)
    }
    if other_keys:
        return None

    assumption = str(calc.get("assumption") or "基于用户输入参数与本地公式").strip()
    body = (
        f"已根据{assumption}完成收益率测算，具体买入价、持仓数量与情景价可在下方交互组件中调整，"
        "回报率与盈亏将随参数实时更新。"
        "\n\n测算结果仅供参考，不构成投资建议。"
    )
    return body


def is_template_eligible(state: AgentState) -> bool:
    """Return True when a deterministic template can replace the output LLM."""
    return try_template_assembly(state) is not None


def try_template_assembly(state: AgentState) -> str | None:
    """Return templated Markdown body for simple heatmap/ranking/calculator queries."""
    query = str(state.get("normalized_query", "")).strip()
    tool_result = _tool_result(state)
    has_rag = _has_rag_hits(state)

    for builder in (
        lambda: _template_heatmap(query, tool_result),
        lambda: _template_ranking(tool_result, has_rag=has_rag),
        lambda: _template_calculator(tool_result, has_rag=has_rag),
    ):
        body = builder()
        if body:
            return ensure_public_risk_notice(body)
    return None


def finalize_template_content(content: str, catalog: CitationCatalog) -> str:
    """Normalize citations and risk notice for template output."""
    normalized = normalize_assembly_citations(content, catalog)
    return ensure_public_risk_notice(normalized)
