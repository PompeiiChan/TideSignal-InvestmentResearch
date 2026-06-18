"""Extract structured earnings forecast scenarios from RAG snippets / company reports."""

from __future__ import annotations

import re
from typing import Any

_SCENARIO_ORDER = ("bear", "base", "bull")

_TARGET_PRICE_RE = re.compile(
    r"目标价\s*([0-9]+(?:\.[0-9]+)?)\s*(?:港元|港币|元|人民币|RMB)?",
    re.IGNORECASE,
)
_EPS_TRIPLE_RE = re.compile(
    r"EPS\s*(?:分别)?(?:为|是)?\s*([0-9]+(?:\.[0-9]+)?)\s*[,，、]\s*"
    r"([0-9]+(?:\.[0-9]+)?)\s*[,，、]\s*([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
_PE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*倍\s*(?:PE|市盈率|pe)", re.IGNORECASE)
_YEAR_EPS_RE = re.compile(r"20(\d{2})E?\s*年?\s*EPS\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)

_REPORT_SOURCE_TYPES = frozenset({"report", "financial", "knowledge"})


def _source_from_hit(hit: dict[str, Any]) -> dict[str, str]:
    return {
        "doc_id": str(hit.get("doc_id", "")),
        "title": str(hit.get("title", "")),
        "path": str(hit.get("path", "")),
        "time_period": "",
        "excerpt": "",
        "origin": "local_kb",
    }


def _report_hits(rag_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for hit in rag_hits:
        if not isinstance(hit, dict):
            continue
        if str(hit.get("source_type", "")) in _REPORT_SOURCE_TYPES:
            hits.append(hit)
    return hits


def _best_source_hit(rag_hits: list[dict[str, Any]]) -> dict[str, Any] | None:
    for hit in _report_hits(rag_hits):
        haystack = " ".join([str(hit.get("title", "")), str(hit.get("snippet", ""))])
        if _EPS_TRIPLE_RE.search(haystack) or _TARGET_PRICE_RE.search(haystack):
            return hit
    return _report_hits(rag_hits)[0] if _report_hits(rag_hits) else None


def _hit_text(hit: dict[str, Any] | None) -> str:
    if not hit:
        return ""
    return " ".join([str(hit.get("title", "")), str(hit.get("snippet", ""))])


def _price_from_eps_pe(eps: float, pe: float) -> float:
    return round(eps * pe, 2)


def _with_source(scenario: dict[str, Any], source_hit: dict[str, Any] | None) -> dict[str, Any]:
    enriched = dict(scenario)
    if source_hit:
        enriched["source"] = _source_from_hit(source_hit)
    return enriched


def extract_earnings_forecast(
    rag_hits: list[dict[str, Any]] | None,
    *,
    stock_name: str = "",
) -> dict[str, Any]:
    """Return structured bear/base/bull scenarios with KB source metadata."""
    hits = rag_hits or []
    source_hit = _best_source_hit(hits)
    haystack = _hit_text(source_hit)
    if not haystack.strip():
        return {
            "tool": "earnings_forecast_lookup",
            "found": False,
            "stock_name": stock_name,
            "scenarios": {},
            "scenario_order": list(_SCENARIO_ORDER),
            "extraction_method": "",
            "primary_source": None,
            "source": "本地知识库研报摘录",
            "notes": "未命中可解析的盈利预测或目标价片段",
        }

    scenarios: dict[str, dict[str, Any]] = {}
    extraction_method = ""
    target_match = _TARGET_PRICE_RE.search(haystack)
    pe_match = _PE_RE.search(haystack)
    pe = float(pe_match.group(1)) if pe_match else None

    eps_triple = _EPS_TRIPLE_RE.search(haystack)
    if eps_triple and pe:
        low_eps, mid_eps, high_eps = (float(eps_triple.group(i)) for i in range(1, 4))
        extraction_method = "eps_pe_triple"
        scenarios["bear"] = _with_source(
            {
                "label": "保守",
                "eps": low_eps,
                "pe": round(pe * 0.9, 2),
                "target_price": _price_from_eps_pe(low_eps, pe * 0.9),
                "assumption": f"保守情景：较低 EPS {low_eps} × {pe * 0.9:.1f} 倍 PE",
            },
            source_hit,
        )
        scenarios["base"] = _with_source(
            {
                "label": "中性",
                "eps": mid_eps,
                "pe": pe,
                "target_price": _price_from_eps_pe(mid_eps, pe),
                "assumption": f"中性情景：EPS {mid_eps} × {pe} 倍 PE",
            },
            source_hit,
        )
        scenarios["bull"] = _with_source(
            {
                "label": "乐观",
                "eps": high_eps,
                "pe": round(pe * 1.1, 2),
                "target_price": _price_from_eps_pe(high_eps, pe * 1.1),
                "assumption": f"乐观情景：较高 EPS {high_eps} × {pe * 1.1:.1f} 倍 PE",
            },
            source_hit,
        )
    elif target_match:
        target = float(target_match.group(1))
        extraction_method = "target_price"
        scenarios["base"] = _with_source(
            {
                "label": "研报目标价",
                "target_price": target,
                "assumption": "摘录研报目标价作为中性情景",
            },
            source_hit,
        )
        scenarios["bear"] = _with_source(
            {
                "label": "保守",
                "target_price": round(target * 0.9, 2),
                "assumption": "目标价下浮 10% 作为保守情景",
            },
            source_hit,
        )
        scenarios["bull"] = _with_source(
            {
                "label": "乐观",
                "target_price": round(target * 1.1, 2),
                "assumption": "目标价上浮 10% 作为乐观情景",
            },
            source_hit,
        )

    year_eps = list(_YEAR_EPS_RE.finditer(haystack))
    if not scenarios and year_eps and pe:
        latest = year_eps[-1]
        eps = float(latest.group(2))
        extraction_method = "year_eps"
        scenarios["base"] = _with_source(
            {
                "label": "中性",
                "eps": eps,
                "pe": pe,
                "target_price": _price_from_eps_pe(eps, pe),
                "assumption": f"20{latest.group(1)}E EPS {eps} × {pe} 倍 PE",
            },
            source_hit,
        )

    found = bool(scenarios)
    return {
        "tool": "earnings_forecast_lookup",
        "found": found,
        "stock_name": stock_name,
        "scenarios": scenarios,
        "scenario_order": [key for key in _SCENARIO_ORDER if key in scenarios],
        "extraction_method": extraction_method,
        "primary_source": _source_from_hit(source_hit) if source_hit else None,
        "source": "本地知识库研报摘录",
        "notes": "情景价来自研报 EPS/PE 或目标价规则推导，仅供参数化测算",
    }
