"""Time-aware hotspot evidence routing: API-primary vs RAG-primary."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

HotspotEvidenceMode = Literal["api_primary", "rag_primary"]

# Local hotspots/ monthly report coverage end dates (see knowledge-base/README.md).
_HOTSPOT_MONTH_COVERAGE_END: dict[str, str] = {
    "2026-04": "2026-04-30",
    "2026-05": "2026-05-29",
    "2026-06": "2026-06-11",
}

_RECENT_TIME_RE = re.compile(
    r"今天|今日|本周|这周|本週|最近|近来|刚刚|最新|当前|实时|盘面|这几天|近几天|眼下|现在|"
    r"近一周|近1周|近七日|近7天|这几天|为啥火|为什么火|怎么突然|突然涨",
    re.IGNORECASE,
)

_RETROSPECTIVE_RE = re.compile(
    r"复盘|收官|全月|整月|月度回顾|月度复盘|上月|上个月|前月|整月表现|月内走势|回顾|演变",
    re.IGNORECASE,
)

_EXPLICIT_MONTH_RE = re.compile(r"(20\d{2})[年\-/]?(\d{1,2})月?|(\d{1,2})月")
_MONTH_RANGE_RE = re.compile(
    r"(?:20\d{2}[年\-/]?)?(\d{1,2})月(?:份)?\s*(?:到|至|—|-)\s*(?:20\d{2}[年\-/]?)?(\d{1,2})月",
    re.IGNORECASE,
)


def _month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _coverage_end(month_key: str) -> date | None:
    raw = _HOTSPOT_MONTH_COVERAGE_END.get(month_key, "")
    return _parse_date(raw) if raw else None


def _kb_stale_for_month(month_key: str, current: date) -> bool:
    end = _coverage_end(month_key)
    if end is None:
        return True
    return current > end


def _extract_month_keys(text: str) -> list[str]:
    keys: list[str] = []
    for match in _EXPLICIT_MONTH_RE.finditer(text):
        if match.group(1) and match.group(2):
            keys.append(_month_key(int(match.group(1)), int(match.group(2))))
        elif match.group(3):
            keys.append(_month_key(2026, int(match.group(3))))
    return keys


def extract_hotspot_month_keys(text: str, *, default_year: int = 2026) -> list[str]:
    """Parse explicit YYYY-MM and ranges like「4月到6月」for multi-month hotspot RAG."""
    keys = _extract_month_keys(text)
    for match in _MONTH_RANGE_RE.finditer(text):
        start_month = int(match.group(1))
        end_month = int(match.group(2))
        if start_month <= end_month:
            for month in range(start_month, end_month + 1):
                keys.append(_month_key(default_year, month))
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return sorted(ordered)


def is_hotspot_replay_query(query: str, slots: dict[str, Any] | None = None) -> bool:
    """Historical replay / multi-month evolution — skip intraday signal tools."""
    slots = slots or {}
    haystack = " ".join(
        [
            query.strip(),
            str(slots.get("time_range", "")),
            str(slots.get("topic", "")),
            str(slots.get("event", "")),
        ]
    )
    if _RETROSPECTIVE_RE.search(haystack) or _MONTH_RANGE_RE.search(haystack):
        return True
    return len(extract_hotspot_month_keys(haystack)) >= 2


def _is_current_month_reference(text: str, current: date) -> bool:
    current_key = _month_key(current.year, current.month)
    if current_key in text or f"{current.month}月" in text:
        return True
    return current_key in _extract_month_keys(text)


def classify_hotspot_evidence_mode(
    query: str,
    slots: dict[str, Any] | None,
    *,
    current_date: date,
) -> tuple[HotspotEvidenceMode, str]:
    """Return evidence mode and a short reason for Trace / planning."""
    slots = slots or {}
    time_range = str(slots.get("time_range", "")).strip()
    haystack = " ".join([query.strip(), time_range, str(slots.get("topic", "")), str(slots.get("event", ""))])

    if _RECENT_TIME_RE.search(haystack):
        return "api_primary", "问题含近期/实时口径，优先数据接口"

    if time_range in {"今天", "今日", "本周", "这周", "最近", "近一周", "近7天", "近七日"}:
        return "api_primary", f"time_range={time_range}，优先数据接口"

    if _RETROSPECTIVE_RE.search(haystack):
        return "rag_primary", "问题为月度复盘/收官口径，优先本地月报 RAG"

    month_keys = _extract_month_keys(haystack)
    current_key = _month_key(current_date.year, current_date.month)
    past_month_keys = [key for key in month_keys if key != current_key]
    if past_month_keys and not _RECENT_TIME_RE.search(haystack):
        return "rag_primary", f"明确历史月份 {past_month_keys[0]}，优先本地月报 RAG"

    if _is_current_month_reference(haystack, current_date):
        if _kb_stale_for_month(current_key, current_date):
            end = _coverage_end(current_key)
            end_label = end.isoformat() if end else "未知"
            return (
                "api_primary",
                f"当月月报仅覆盖至 {end_label}，当前 {current_date.isoformat()}，优先数据接口",
            )
        return "rag_primary", "当月月报仍有效，可用 RAG 月报"

    if time_range and _kb_stale_for_month(time_range[:7], current_date) if len(time_range) >= 7 else False:
        return "api_primary", "槽位月份月报已滞后，优先数据接口"

    return "rag_primary", "默认月度热点归因，RAG 月报主证据"


def build_hotspot_execution_plan(
    query: str,
    slots: dict[str, Any] | None,
    *,
    current_date: date,
) -> dict[str, Any]:
    """Build hotspot execution_plan with time-aware RAG vs API priority."""
    mode, reason = classify_hotspot_evidence_mode(query, slots, current_date=current_date)
    slots = slots or {}
    replay = is_hotspot_replay_query(query, slots)
    month_keys = extract_hotspot_month_keys(
        " ".join(
            [
                query.strip(),
                str(slots.get("time_range", "")),
                str(slots.get("topic", "")),
            ]
        ),
        default_year=current_date.year,
    )
    if replay:
        tool_names = ["hotspot_fact_lookup"]
    else:
        tool_names = ["hotspot_fact_lookup", "hotspot_signal_lookup"]
    plan: dict[str, Any] = {
        "needs_rag": True,
        "needs_tool": True,
        "tool_names": tool_names,
        "hotspot_evidence_mode": mode,
        "hotspot_evidence_mode_reason": reason,
    }
    if mode == "api_primary":
        plan["retrieval_config"] = {
            "top_k": 5,
            "strategy": "hotspot_industry_only",
            "filters": {},
        }
        plan["tool_params_defaults"] = {
            "news_limit": 40,
            "announcement_limit": 10,
            "signal_limit": 12,
        }
        plan["data_source_hint"] = "东财快讯/巨潮公告 + 同花顺盘面信号（主）；行业研报 RAG（辅）"
    else:
        plan["retrieval_config"] = {
            "top_k": 10,
            "strategy": "hotspot_dual",
            "filters": {},
        }
        if len(month_keys) >= 2:
            plan["retrieval_config"]["hotspot_month_keys"] = month_keys
        plan["tool_params_defaults"] = {
            "news_limit": 30,
            "announcement_limit": 8,
            "signal_limit": 10,
        }
        plan["data_source_hint"] = "RAG 热点月报/行业研报（主）+ 东财快讯/巨潮公告 + 同花顺信号（辅）"
    return plan
