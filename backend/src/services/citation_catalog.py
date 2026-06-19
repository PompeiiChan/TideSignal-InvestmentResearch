"""Deterministic citation numbering for assembly (local sources first, numeric only)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .rag.models import RagHit
from .system_time import SystemTimeContext, resolve_system_time

_FINANCIAL_TOOL_KEY = "mock_financial_profile_lookup"
_VALUATION_TOOL_KEY = "valuation_profile_lookup"
_STOCK_API_TOOL_KEY = "stock_evidence_api_lookup"
_HOTSPOT_FACT_TOOL_KEY = "hotspot_fact_lookup"
_HOTSPOT_SIGNAL_TOOL_KEY = "hotspot_signal_lookup"
_MARKET_RANKING_TOOL_KEY = "market_ranking_lookup"
_SECTOR_HEATMAP_TOOL_KEY = "sector_heatmap_lookup"
_LOCAL_KB_SOURCE_TYPES = frozenset({"financial", "announcement", "report", "qa", "knowledge", "market"})
_CITATION_FINANCIAL_RE = re.compile(r"\[citation:财务\]", re.IGNORECASE)
_CITATION_NUM_RE = re.compile(r"\[citation:(\d+)\]")
_BOGUS_REFERENCE_LINE_RE = re.compile(
    r"未覆盖|暂未覆盖|工具返回\s*N/A|本地知识库未覆盖",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CitationEntry:
    index: int
    title: str
    source_type: str
    doc_id: str = ""
    origin: str = ""


@dataclass
class CitationCatalog:
    entries: list[CitationEntry] = field(default_factory=list)
    doc_index: dict[str, int] = field(default_factory=dict)
    chunk_index: dict[str, int] = field(default_factory=dict)

    def valid_indices(self) -> set[int]:
        return {entry.index for entry in self.entries}

    def to_quality_payload(self) -> list[dict[str, str]]:
        return [
            {
                "index": str(entry.index),
                "title": entry.title,
                "source_type": entry.source_type,
                "doc_id": entry.doc_id,
                "origin": entry.origin,
            }
            for entry in self.entries
        ]


def _valuation_tool_payload(tool_result: dict[str, Any]) -> dict[str, Any] | None:
    payload = tool_result.get(_VALUATION_TOOL_KEY)
    return payload if isinstance(payload, dict) else None


def _valuation_snapshot(payload: dict[str, Any]) -> dict[str, Any] | None:
    snapshot = payload.get("valuation")
    return snapshot if isinstance(snapshot, dict) else None


def valuation_tool_is_usable(tool_result: dict[str, Any]) -> bool:
    payload = _valuation_tool_payload(tool_result)
    if payload is None or payload.get("found") is False:
        return False
    snapshot = _valuation_snapshot(payload)
    if snapshot is None:
        return False
    metrics = [snapshot.get("pe_ttm"), snapshot.get("pb"), snapshot.get("price")]
    present = [str(value).strip() for value in metrics if value is not None]
    return bool(present) and not all(value.upper() == "N/A" for value in present)


def valuation_reference_title(snapshot: dict[str, Any], *, has_history: bool = False) -> str:
    name = str(snapshot.get("stock_name", "")).strip() or "未知公司"
    if has_history:
        return f"{name} 估值画像（腾讯实时 + 东财历史分位）"
    return f"{name} 实时估值（腾讯行情）"


def _stock_api_tool_payload(tool_result: dict[str, Any]) -> dict[str, Any] | None:
    payload = tool_result.get(_STOCK_API_TOOL_KEY)
    return payload if isinstance(payload, dict) else None


def stock_api_tool_is_usable(tool_result: dict[str, Any]) -> bool:
    payload = _stock_api_tool_payload(tool_result)
    if payload is None or payload.get("found") is False:
        return False
    facts = payload.get("facts")
    return isinstance(facts, list) and bool(facts)


def stock_api_reference_title(payload: dict[str, Any]) -> str:
    name = str(payload.get("stock_name", "")).strip() or "标的"
    return f"{name} 公告与资讯（API）"


def _hotspot_fact_tool_payload(tool_result: dict[str, Any]) -> dict[str, Any] | None:
    payload = tool_result.get(_HOTSPOT_FACT_TOOL_KEY)
    if isinstance(payload, dict) and payload.get("tool") == _HOTSPOT_FACT_TOOL_KEY:
        return payload
    return None


def hotspot_fact_tool_is_usable(tool_result: dict[str, Any]) -> bool:
    return _hotspot_fact_tool_payload(tool_result) is not None


def hotspot_fact_reference_title(payload: dict[str, Any]) -> str:
    topic = str(payload.get("topic", "")).strip() or "市场热点"
    return f"{topic} 相关快讯与公告（东财资讯/巨潮）"


def _hotspot_signal_tool_payload(tool_result: dict[str, Any]) -> dict[str, Any] | None:
    payload = tool_result.get(_HOTSPOT_SIGNAL_TOOL_KEY)
    if isinstance(payload, dict) and payload.get("tool") == _HOTSPOT_SIGNAL_TOOL_KEY:
        return payload
    return None


def hotspot_signal_tool_is_usable(tool_result: dict[str, Any]) -> bool:
    return _hotspot_signal_tool_payload(tool_result) is not None


def hotspot_signal_reference_title(payload: dict[str, Any]) -> str:
    mode = str(payload.get("signal_mode", "")).strip()
    if mode == "kb_material":
        return "知识库热点月报整理摘要（时效滞后）"
    trade_date = str(payload.get("trade_date") or payload.get("time_range", "")).strip()
    label = "同花顺当日强势股题材标签"
    return f"{label}（{trade_date}）" if trade_date else label


def _market_ranking_tool_payload(tool_result: dict[str, Any]) -> dict[str, Any] | None:
    payload = tool_result.get(_MARKET_RANKING_TOOL_KEY)
    if isinstance(payload, dict) and payload.get("tool") == _MARKET_RANKING_TOOL_KEY:
        return payload
    return None


def market_ranking_tool_is_usable(tool_result: dict[str, Any]) -> bool:
    return _market_ranking_tool_payload(tool_result) is not None


def market_ranking_reference_title(payload: dict[str, Any]) -> str:
    industry = str(payload.get("industry", "")).strip() or "行情"
    mode = str(payload.get("ranking_mode", "")).strip()
    if mode == "board_stocks":
        return f"{industry} 板块成分股涨幅（东财 push2）"
    if mode == "industry_boards":
        return "全行业板块涨跌幅排行（东财 push2）"
    return f"{industry} 行情排行（东财 push2）"


def _sector_heatmap_tool_payload(tool_result: dict[str, Any]) -> dict[str, Any] | None:
    payload = tool_result.get(_SECTOR_HEATMAP_TOOL_KEY)
    if isinstance(payload, dict) and payload.get("tool") == _SECTOR_HEATMAP_TOOL_KEY:
        return payload
    return None


def sector_heatmap_tool_is_usable(tool_result: dict[str, Any]) -> bool:
    payload = _sector_heatmap_tool_payload(tool_result)
    return payload is not None and bool(payload.get("tiles"))


def sector_heatmap_reference_title(_payload: dict[str, Any]) -> str:
    return "行业板块热力图（东财 push2）"


def _financial_tool_payload(tool_result: dict[str, Any]) -> dict[str, Any] | None:
    payload = tool_result.get(_FINANCIAL_TOOL_KEY)
    return payload if isinstance(payload, dict) else None


def _financial_profile(payload: dict[str, Any]) -> dict[str, Any] | None:
    profile = payload.get("profile")
    return profile if isinstance(profile, dict) else None


def financial_tool_is_usable(tool_result: dict[str, Any]) -> bool:
    payload = _financial_tool_payload(tool_result)
    if payload is None:
        return False
    if payload.get("found") is False:
        return False
    profile = _financial_profile(payload)
    if profile is None:
        return False
    if str(profile.get("company_id", "")).strip() == "company_unknown":
        return False
    highlights = profile.get("highlights") or []
    if any("暂未覆盖" in str(item) for item in highlights):
        return False
    core_metrics = [profile.get("revenue"), profile.get("net_profit")]
    present = [str(value).strip() for value in core_metrics if value is not None]
    return not (present and all(value.upper() == "N/A" for value in present))


def financial_reference_title(profile: dict[str, Any]) -> str:
    name = str(profile.get("stock_name", "")).strip() or "未知公司"
    period = str(profile.get("time_period", "")).strip()
    if period.endswith("A") and len(period) >= 5:
        return f"{name} {period[:-1]} 年年度报告"
    if period:
        return f"{name} {period} 财务数据"
    return f"{name} 财务数据"


def valuation_citation_index(catalog: CitationCatalog) -> int | None:
    return catalog.doc_index.get("__valuation_tool__")


def resolve_doc_citation_index(catalog: CitationCatalog, doc_id: str) -> int | None:
    key = doc_id.strip()
    if not key:
        return None
    return catalog.doc_index.get(key)


def resolve_hit_citation_index(catalog: CitationCatalog, hit: dict[str, Any]) -> int | None:
    chunk_id = str(hit.get("chunk_id", "")).strip()
    if chunk_id and chunk_id in catalog.chunk_index:
        return catalog.chunk_index[chunk_id]
    doc_key = str(hit.get("doc_id", "")).strip() or str(hit.get("path", "")).strip()
    if doc_key:
        return catalog.doc_index.get(doc_key)
    return None


def strip_unusable_financial_tool(tool_result: dict[str, Any]) -> dict[str, Any]:
    """Remove unusable local financial tool output so the LLM cannot cite phantom data."""
    if not isinstance(tool_result, dict):
        return {}
    cleaned = dict(tool_result)
    if not financial_tool_is_usable(cleaned):
        cleaned.pop(_FINANCIAL_TOOL_KEY, None)
    return cleaned


def _rag_doc_tier(hit: RagHit, *, response_kind: str = "data") -> int:
    """Lower tier sorts earlier in the citation catalog."""
    if response_kind == "hotspot" and hit.source_type == "market":
        return 1
    if hit.source_type == "financial":
        return 2
    if hit.source_type == "announcement":
        return 3
    if hit.source_type == "report":
        return 4
    if hit.source_type in {"qa", "knowledge"}:
        return 5
    if hit.source_type == "market":
        return 6
    return 7


def _is_local_kb_hit(hit: RagHit) -> bool:
    return hit.source_type in _LOCAL_KB_SOURCE_TYPES


def _financial_doc_matches_tool(hit: RagHit, profile: dict[str, Any]) -> bool:
    if hit.source_type != "financial":
        return False
    stock_name = str(profile.get("stock_name", "")).strip()
    ticker = str(profile.get("ticker", "")).strip().split(".")[0]
    haystacks = " ".join([hit.title, hit.path, hit.doc_id]).lower()
    if stock_name and stock_name.lower() in haystacks:
        return True
    return bool(ticker and ticker in haystacks)


def build_citation_catalog(
    rag_hits: list[RagHit],
    tool_result: dict[str, Any],
    *,
    response_kind: str = "data",
) -> CitationCatalog:
    """Assign numeric citations: local financial tool first, then local KB docs by type."""
    catalog = CitationCatalog()
    next_index = 1
    financial_profile: dict[str, Any] | None = None

    if financial_tool_is_usable(tool_result):
        payload = _financial_tool_payload(tool_result) or {}
        financial_profile = _financial_profile(payload) or {}
        title = financial_reference_title(financial_profile)
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=title,
                source_type="financial",
                doc_id=str(financial_profile.get("company_id", "")),
                origin="local_financial_db",
            )
        )
        catalog.doc_index["__local_financial_tool__"] = next_index
        next_index += 1

    if valuation_tool_is_usable(tool_result):
        payload = _valuation_tool_payload(tool_result) or {}
        snapshot = _valuation_snapshot(payload) or {}
        has_history = bool((payload.get("valuation_history") or {}).get("found"))
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=valuation_reference_title(snapshot, has_history=has_history),
                source_type="market",
                doc_id=str(snapshot.get("ticker", "")),
                origin="tencent_quote_api",
            )
        )
        catalog.doc_index["__valuation_tool__"] = next_index
        next_index += 1

    if stock_api_tool_is_usable(tool_result):
        payload = _stock_api_tool_payload(tool_result) or {}
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=stock_api_reference_title(payload),
                source_type="announcement",
                doc_id=str(payload.get("stock_code", "")),
                origin="stock_evidence_api",
            )
        )
        catalog.doc_index["__stock_api_tool__"] = next_index
        next_index += 1

    if hotspot_fact_tool_is_usable(tool_result):
        payload = _hotspot_fact_tool_payload(tool_result) or {}
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=hotspot_fact_reference_title(payload),
                source_type="market",
                doc_id=str(payload.get("topic", "")),
                origin="hotspot_fact_api",
            )
        )
        catalog.doc_index["__hotspot_fact_tool__"] = next_index
        next_index += 1

    if hotspot_signal_tool_is_usable(tool_result):
        payload = _hotspot_signal_tool_payload(tool_result) or {}
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=hotspot_signal_reference_title(payload),
                source_type="market",
                doc_id=str(payload.get("topic", "")),
                origin="hotspot_signal_api",
            )
        )
        catalog.doc_index["__hotspot_signal_tool__"] = next_index
        next_index += 1

    if market_ranking_tool_is_usable(tool_result):
        payload = _market_ranking_tool_payload(tool_result) or {}
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=market_ranking_reference_title(payload),
                source_type="market",
                doc_id=str(payload.get("industry", "")),
                origin="eastmoney_ranking_api",
            )
        )
        catalog.doc_index["__market_ranking_tool__"] = next_index
        next_index += 1

    if sector_heatmap_tool_is_usable(tool_result):
        payload = _sector_heatmap_tool_payload(tool_result) or {}
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=sector_heatmap_reference_title(payload),
                source_type="market",
                doc_id="sector_heatmap",
                origin="eastmoney_heatmap_api",
            )
        )
        catalog.doc_index["__sector_heatmap_tool__"] = next_index
        next_index += 1

    local_docs: list[tuple[int, str, RagHit]] = []
    for hit in rag_hits:
        if not _is_local_kb_hit(hit):
            continue
        doc_key = hit.doc_id.strip() or hit.path.strip() or hit.title.strip()
        if not doc_key:
            continue
        if financial_profile and _financial_doc_matches_tool(hit, financial_profile):
            catalog.doc_index[doc_key] = catalog.doc_index["__local_financial_tool__"]
            if hit.chunk_id:
                catalog.chunk_index[hit.chunk_id] = catalog.doc_index["__local_financial_tool__"]
            continue
        if doc_key in catalog.doc_index:
            if hit.chunk_id:
                catalog.chunk_index[hit.chunk_id] = catalog.doc_index[doc_key]
            continue
        local_docs.append((_rag_doc_tier(hit, response_kind=response_kind), doc_key, hit))

    local_docs.sort(key=lambda item: (item[0], item[1]))
    for _tier, doc_key, hit in local_docs:
        if doc_key in catalog.doc_index:
            continue
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=hit.title.strip() or doc_key,
                source_type=hit.source_type,
                doc_id=hit.doc_id,
                origin="local_kb",
            )
        )
        catalog.doc_index[doc_key] = next_index
        next_index += 1

    for hit in rag_hits:
        doc_key = hit.doc_id.strip() or hit.path.strip() or hit.title.strip()
        if not doc_key:
            continue
        if hit.chunk_id and hit.chunk_id in catalog.chunk_index:
            continue
        if doc_key in catalog.doc_index:
            if hit.chunk_id:
                catalog.chunk_index[hit.chunk_id] = catalog.doc_index[doc_key]
            continue
        if _is_local_kb_hit(hit):
            continue
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=hit.title.strip() or doc_key,
                source_type=hit.source_type,
                doc_id=hit.doc_id,
                origin="external",
            )
        )
        catalog.doc_index[doc_key] = next_index
        if hit.chunk_id:
            catalog.chunk_index[hit.chunk_id] = next_index
        next_index += 1

    for hit in rag_hits:
        doc_key = hit.doc_id.strip() or hit.path.strip() or hit.title.strip()
        if hit.chunk_id and hit.chunk_id not in catalog.chunk_index and doc_key in catalog.doc_index:
            catalog.chunk_index[hit.chunk_id] = catalog.doc_index[doc_key]

    return catalog


def _catalog_index_for_hit(catalog: CitationCatalog, hit: RagHit) -> int | None:
    if hit.chunk_id and hit.chunk_id in catalog.chunk_index:
        return catalog.chunk_index[hit.chunk_id]
    doc_key = hit.doc_id.strip() or hit.path.strip() or hit.title.strip()
    if doc_key and doc_key in catalog.doc_index:
        return catalog.doc_index[doc_key]
    return None


def format_citation_context(
    catalog: CitationCatalog,
    rag_hits: list[RagHit],
    tool_result: dict[str, Any],
    *,
    ctx: SystemTimeContext | None = None,
) -> str:
    """Build numbered reference table + RAG snippets aligned to catalog indices."""
    if not catalog.entries and not rag_hits:
        return ""

    time_ctx = ctx or resolve_system_time()
    lines = [
        time_ctx.prompt_block(),
        "",
        "## 引用编号表（正文与 `### 参考来源` 只能使用下列数字编号 `[citation:N]`，禁止使用 `[citation:财务]`）",
        "",
    ]

    for entry in catalog.entries:
        lines.append(f"【{entry.index}】{entry.title}")

    payload = _financial_tool_payload(tool_result)
    profile = _financial_profile(payload) if payload else None
    periods_raw = payload.get("periods") if payload else None
    periods = [item for item in periods_raw if isinstance(item, dict)] if isinstance(periods_raw, list) else []
    if financial_tool_is_usable(tool_result) and periods:
        lines.extend(
            [
                "",
                "### 多期结构化财务数据（引用编号 1，须用 [citation:1]）",
                "按 time_period 从新到旧排列；综合基本面问题**必须**据此输出多期对比 Markdown 表并分析趋势/同比，"
                "不得只分析最新一期：",
                json.dumps(periods, ensure_ascii=False, indent=2),
            ]
        )
    elif financial_tool_is_usable(tool_result) and profile:
        lines.extend(
            [
                "",
                "### 结构化财务数据（引用编号 1，须用 [citation:1]）",
                json.dumps(profile, ensure_ascii=False, indent=2),
            ]
        )

    valuation_payload = _valuation_tool_payload(tool_result)
    valuation_snapshot = _valuation_snapshot(valuation_payload) if valuation_payload else None
    valuation_index = catalog.doc_index.get("__valuation_tool__")
    if valuation_tool_is_usable(tool_result) and valuation_snapshot and valuation_index:
        lines.extend(
            [
                "",
                f"### 结构化估值数据（引用编号 {valuation_index}，须用 [citation:{valuation_index}]）",
                json.dumps(valuation_snapshot, ensure_ascii=False, indent=2),
            ]
        )
        valuation_history = (valuation_payload or {}).get("valuation_history")
        if isinstance(valuation_history, dict) and valuation_history.get("found"):
            lines.extend(
                [
                    "",
                    f"### 估值历史分位（同引用编号 {valuation_index}，解读「贵不贵」须结合本节）",
                    json.dumps(valuation_history, ensure_ascii=False, indent=2),
                ]
            )

    stock_api_payload = _stock_api_tool_payload(tool_result)
    stock_api_index = catalog.doc_index.get("__stock_api_tool__")
    if stock_api_tool_is_usable(tool_result) and stock_api_payload and stock_api_index:
        facts = stock_api_payload.get("facts") or []
        lines.extend(
            [
                "",
                f"### API 公告与资讯（引用编号 {stock_api_index}，须用 [citation:{stock_api_index}]）",
                "以下为巨潮公告与东财快讯摘要，用于补充本地知识库未收录标的；引用时写明时间与来源：",
                json.dumps(facts, ensure_ascii=False, indent=2),
            ]
        )

    hotspot_fact_payload = _hotspot_fact_tool_payload(tool_result)
    hotspot_fact_index = catalog.doc_index.get("__hotspot_fact_tool__")
    if hotspot_fact_tool_is_usable(tool_result) and hotspot_fact_payload and hotspot_fact_index:
        facts = hotspot_fact_payload.get("facts") or []
        lines.extend(
            [
                "",
                f"### 热点事实快讯/公告（引用编号 {hotspot_fact_index}，须用 [citation:{hotspot_fact_index}]）",
                "东财全球资讯 + 巨潮公告；无命中时须写「未见可核验硬事实」，不得编造：",
                json.dumps(
                    {
                        "topic": hotspot_fact_payload.get("topic"),
                        "fact_count": hotspot_fact_payload.get("fact_count", len(facts)),
                        "facts": facts[:12],
                        "notes": hotspot_fact_payload.get("notes", ""),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ]
        )

    hotspot_signal_payload = _hotspot_signal_tool_payload(tool_result)
    hotspot_signal_index = catalog.doc_index.get("__hotspot_signal_tool__")
    if hotspot_signal_tool_is_usable(tool_result) and hotspot_signal_payload and hotspot_signal_index:
        lines.extend(
            [
                "",
                f"### 热点盘面信号（引用编号 {hotspot_signal_index}，须用 [citation:{hotspot_signal_index}]）",
                "同花顺强势股 reason 标签或知识库降级素材；`topic_matched=false` 时不得把无关标签写成主题热度：",
                json.dumps(
                    {
                        "signal_mode": hotspot_signal_payload.get("signal_mode"),
                        "topic": hotspot_signal_payload.get("topic"),
                        "topic_matched": hotspot_signal_payload.get("topic_matched"),
                        "trade_date": hotspot_signal_payload.get("trade_date"),
                        "stock_count": hotspot_signal_payload.get("stock_count", 0),
                        "themes": hotspot_signal_payload.get("themes") or [],
                        "stocks": (hotspot_signal_payload.get("stocks") or [])[:8],
                        "notes": hotspot_signal_payload.get("notes", ""),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ]
        )

    market_ranking_payload = _market_ranking_tool_payload(tool_result)
    market_ranking_index = catalog.doc_index.get("__market_ranking_tool__")
    if market_ranking_tool_is_usable(tool_result) and market_ranking_payload and market_ranking_index:
        rows = market_ranking_payload.get("rows") or []
        lines.extend(
            [
                "",
                f"### 板块/行情排行（引用编号 {market_ranking_index}，须用 [citation:{market_ranking_index}]）",
                "东财 push2 板块或成分股涨跌幅；数字须原样引用：",
                json.dumps(
                    {
                        "ranking_mode": market_ranking_payload.get("ranking_mode"),
                        "industry": market_ranking_payload.get("industry"),
                        "row_count": market_ranking_payload.get("row_count", len(rows)),
                        "time_range": market_ranking_payload.get("time_range"),
                        "rows": rows[:10],
                        "notes": market_ranking_payload.get("notes", ""),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ]
        )

    sector_heatmap_payload = _sector_heatmap_tool_payload(tool_result)
    sector_heatmap_index = catalog.doc_index.get("__sector_heatmap_tool__")
    if sector_heatmap_tool_is_usable(tool_result) and sector_heatmap_payload and sector_heatmap_index:
        lines.extend(
            [
                "",
                f"### 行业板块热力图（引用编号 {sector_heatmap_index}，须用 [citation:{sector_heatmap_index}]）",
                json.dumps(
                    {
                        "tiles": (sector_heatmap_payload.get("tiles") or [])[:12],
                        "notes": sector_heatmap_payload.get("notes", ""),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ]
        )

    if rag_hits:
        lines.extend(
            [
                "",
                "以下是从本地知识库检索到的参考片段；片段前的编号与引用编号表一致，"
                "正文段末请使用 `[citation:N]`：",
            ]
        )
        for hit in rag_hits:
            cite_index = _catalog_index_for_hit(catalog, hit)
            if cite_index is None:
                continue
            breadcrumb = f"，路径={hit.breadcrumb}" if hit.breadcrumb else ""
            period = f"，time_period={hit.time_period}" if hit.time_period.strip() else ""
            lines.append(
                f"【{cite_index}】{hit.title}（来源类型：{hit.source_type}，doc_id={hit.doc_id}{period}{breadcrumb}）\n"
                f"文件：{hit.path}\n{hit.snippet}"
            )

    return "\n\n".join(lines)


def _body_before_reference(content: str) -> str:
    marker = "### 参考来源"
    start = content.find(marker)
    if start == -1:
        return content
    return content[:start]


def _citation_indices_in_text(text: str) -> set[int]:
    return {int(match.group(1)) for match in _CITATION_NUM_RE.finditer(text)}


def _reference_section_lines(content: str) -> tuple[str, list[str], str]:
    marker = "### 参考来源"
    start = content.find(marker)
    if start == -1:
        return content, [], ""
    head = content[: start + len(marker)]
    tail = content[start + len(marker) :]
    next_heading = re.search(r"\n###\s+", tail)
    if next_heading is None:
        body, rest = tail, ""
    else:
        split_at = next_heading.start()
        body, rest = tail[:split_at], tail[split_at:]
    ref_lines = [line for line in body.splitlines() if line.strip()]
    return head, ref_lines, rest


def _format_reference_line(catalog: CitationCatalog, index: int) -> str:
    for entry in catalog.entries:
        if entry.index == index:
            return f"- [citation:{index}]{entry.title}"
    return ""


def _rebuild_reference_section(content: str, catalog: CitationCatalog, used_indices: set[int]) -> str:
    """Append reference lines for body citations when the LLM omitted or lost the section."""
    if not used_indices or not catalog.entries:
        return content
    head, ref_lines, rest = _reference_section_lines(content)
    if ref_lines:
        return content
    lines = [_format_reference_line(catalog, index) for index in sorted(used_indices)]
    lines = [line for line in lines if line]
    if not lines:
        return content
    body = content.rstrip()
    if "### 参考来源" in body:
        return content
    return f"{body}\n\n### 参考来源\n\n" + "\n".join(lines) + rest


def sanitize_reference_section(content: str, catalog: CitationCatalog) -> str:
    """Drop bogus reference lines and keep only catalog-backed citations."""
    head, ref_lines, rest = _reference_section_lines(content)
    if not ref_lines:
        return content

    valid_indices = catalog.valid_indices()
    financial_index = catalog.doc_index.get("__local_financial_tool__")
    used_in_body = _citation_indices_in_text(_body_before_reference(content))
    cleaned: list[str] = []
    for line in ref_lines:
        if _BOGUS_REFERENCE_LINE_RE.search(line):
            continue
        if financial_index is None and _CITATION_FINANCIAL_RE.search(line):
            continue
        nums = [int(value) for value in re.findall(r"\[citation:(\d+)\]", line)]
        if valid_indices and nums and not all(num in valid_indices for num in nums):
            continue
        if used_in_body:
            if not nums or not any(num in used_in_body for num in nums):
                continue
        elif nums:
            continue
        cleaned.append(line)

    if not cleaned:
        body_without_refs = content.split("### 参考来源", maxsplit=1)[0].rstrip()
        rebuilt = _rebuild_reference_section(body_without_refs, catalog, used_in_body)
        return rebuilt if rebuilt != body_without_refs else body_without_refs

    return f"{head}\n" + "\n".join(cleaned) + rest


def compact_used_citations(content: str) -> str:
    """Renumber in-body citations to a dense 1..N sequence (drops gaps from unused catalog slots)."""
    used = sorted({int(match.group(1)) for match in _CITATION_NUM_RE.finditer(content)})
    if not used or used == list(range(1, len(used) + 1)):
        return content
    mapping = {old: new for new, old in enumerate(used, start=1)}

    def _replace(match: re.Match[str]) -> str:
        old = int(match.group(1))
        return f"[citation:{mapping[old]}]"

    return _CITATION_NUM_RE.sub(_replace, content)


def normalize_assembly_citations(content: str, catalog: CitationCatalog) -> str:
    """Map legacy financial markers to numeric index and sanitize reference section."""
    financial_index = catalog.doc_index.get("__local_financial_tool__")
    normalized = content
    if financial_index is not None:
        normalized = _CITATION_FINANCIAL_RE.sub(f"[citation:{financial_index}]", normalized)
    else:
        normalized = _CITATION_FINANCIAL_RE.sub("", normalized)
    normalized = sanitize_reference_section(normalized, catalog)
    used_in_body = _citation_indices_in_text(_body_before_reference(normalized))
    normalized = _rebuild_reference_section(normalized, catalog, used_in_body)
    normalized = compact_used_citations(normalized)
    return normalized
