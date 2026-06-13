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


def valuation_reference_title(snapshot: dict[str, Any]) -> str:
    name = str(snapshot.get("stock_name", "")).strip() or "未知公司"
    return f"{name} 实时估值（腾讯行情）"


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
    if present and all(value.upper() == "N/A" for value in present):
        return False
    return True


def financial_reference_title(profile: dict[str, Any]) -> str:
    name = str(profile.get("stock_name", "")).strip() or "未知公司"
    period = str(profile.get("time_period", "")).strip()
    if period.endswith("A") and len(period) >= 5:
        return f"{name} {period[:-1]} 年年度报告"
    if period:
        return f"{name} {period} 财务数据"
    return f"{name} 财务数据"


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
    if ticker and ticker in haystacks:
        return True
    return False


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
        catalog.entries.append(
            CitationEntry(
                index=next_index,
                title=valuation_reference_title(snapshot),
                source_type="market",
                doc_id=str(snapshot.get("ticker", "")),
                origin="tencent_quote_api",
            )
        )
        catalog.doc_index["__valuation_tool__"] = next_index
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


def sanitize_reference_section(content: str, catalog: CitationCatalog) -> str:
    """Drop bogus reference lines and keep only catalog-backed citations."""
    head, ref_lines, rest = _reference_section_lines(content)
    if not ref_lines:
        return content

    valid_indices = catalog.valid_indices()
    financial_index = catalog.doc_index.get("__local_financial_tool__")
    cleaned: list[str] = []
    for line in ref_lines:
        if _BOGUS_REFERENCE_LINE_RE.search(line):
            continue
        if financial_index is None and _CITATION_FINANCIAL_RE.search(line):
            continue
        if valid_indices:
            nums = [int(value) for value in re.findall(r"\[citation:(\d+)\]", line)]
            if nums and not all(num in valid_indices for num in nums):
                continue
        cleaned.append(line)

    if not cleaned:
        body_without_refs = content.split("### 参考来源", maxsplit=1)[0].rstrip()
        return body_without_refs

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
    normalized = compact_used_citations(normalized)
    return normalized
