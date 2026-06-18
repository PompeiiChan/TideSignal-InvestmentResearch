"""Financial profile lookup: local cache → KB file → Sina Finance HTTP."""

from __future__ import annotations

import logging
from typing import Any, Literal

from ...integrations.market_data.sina_finance_client import fetch_multi_period_profiles
from ...integrations.market_data.stock_code_resolver import resolve_stock_code
from ...services.rag.chunker import resolve_kb_root
from ...services.rag.kb_financial_loader import (
    find_financial_kb_file,
    load_all_profiles_from_kb_file,
)
from ...settings import BACKEND_ROOT, get_settings

logger = logging.getLogger(__name__)

_PROFILES: dict[str, dict[str, Any]] = {
    "泸州老窖": {
        "company_id": "company_000568",
        "ticker": "000568.SZ",
        "stock_name": "泸州老窖",
        "industry": "白酒",
        "time_period": "2025A",
        "revenue": "312.5亿元",
        "net_profit": "132.8亿元",
        "gross_margin": "88.2%",
        "roe": "28.6%",
        "pe_ttm": "18.5",
        "highlights": ["高端白酒龙头", "渠道改革持续推进", "2025A 营收同比+8.2%"],
    },
    "宁德时代": {
        "company_id": "company_300750",
        "ticker": "300750.SZ",
        "stock_name": "宁德时代",
        "industry": "动力电池",
        "time_period": "2025A",
        "revenue": "4012亿元",
        "net_profit": "502亿元",
        "gross_margin": "22.1%",
        "roe": "19.4%",
        "pe_ttm": "22.3",
        "highlights": ["全球动力电池龙头", "储能业务快速增长", "海外产能持续扩张"],
    },
    "寒武纪": {
        "company_id": "company_688256",
        "ticker": "688256.SH",
        "stock_name": "寒武纪",
        "industry": "AI芯片",
        "time_period": "2025A",
        "revenue": "18.6亿元",
        "net_profit": "-2.1亿元",
        "gross_margin": "56.3%",
        "roe": "-5.2%",
        "pe_ttm": "N/A",
        "highlights": ["AI推理芯片国产替代", "研发投入占比高", "客户结构持续优化"],
    },
    "罗莱生活": {
        "company_id": "company_002293",
        "ticker": "002293.SZ",
        "stock_name": "罗莱生活",
        "industry": "家纺",
        "time_period": "2026Q1",
        "revenue": "11.58亿元",
        "net_profit": "1.48亿元",
        "gross_margin": "N/A",
        "roe": "3.45%",
        "pe_ttm": "N/A",
        "highlights": ["2026Q1 营收同比+5.87%", "归母净利润同比+30.54%", "家纺龙头"],
    },
}

DataOrigin = Literal["local_profile_cache", "local_kb_file", "sina_api"]


def _success_payload(
    profile: dict[str, Any],
    *,
    periods: list[dict[str, Any]],
    analysis_dimension: str,
    data_origin: DataOrigin,
    source: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "tool": "mock_financial_profile_lookup",
        "found": True,
        "analysis_dimension": analysis_dimension,
        "profile": profile,
        "periods": periods,
        "source": source,
        "data_origin": data_origin,
        "is_mock": False,
        "notes": notes,
    }


def _not_found_payload(*, analysis_dimension: str) -> dict[str, Any]:
    return {
        "tool": "mock_financial_profile_lookup",
        "found": False,
        "analysis_dimension": analysis_dimension,
        "profile": None,
        "periods": [],
        "source": "",
        "data_origin": "",
        "is_mock": False,
        "notes": "本地财报库与新浪财经 API 均未返回可用财务画像",
    }


def _lookup_cached_profile(stock_name: str, stock_code: str) -> dict[str, Any] | None:
    profile = _PROFILES.get(stock_name.strip())
    if profile is None and stock_code:
        normalized = stock_code.replace(".", "").upper()
        for item in _PROFILES.values():
            ticker = str(item["ticker"]).replace(".", "").upper()
            if ticker.startswith(normalized) or normalized.startswith(ticker[:6]):
                profile = item
                break
    return profile


def lookup_financial_profile(
    *,
    stock_name: str = "",
    stock_code: str = "",
    analysis_dimension: str = "基本面",
    **_extra: Any,
) -> dict[str, Any]:
    """Return structured financial profile with local → KB → Sina fallback."""
    settings = get_settings()
    kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)
    resolved_code, resolved_name = resolve_stock_code(stock_name, stock_code, settings=settings)

    cached = _lookup_cached_profile(resolved_name or stock_name, stock_code)
    if cached is not None:
        periods = [dict(cached)]
        return _success_payload(
            periods[0],
            periods=periods,
            analysis_dimension=analysis_dimension,
            data_origin="local_profile_cache",
            source="backend/data/knowledge-base/financials/",
            notes="结构化财务画像（内置样本缓存）",
        )

    if resolved_code and kb_root.exists():
        kb_file = find_financial_kb_file(kb_root, resolved_code)
        if kb_file is not None:
            kb_periods = load_all_profiles_from_kb_file(
                kb_file,
                stock_name=resolved_name or stock_name,
                stock_code=resolved_code,
            )
            if kb_periods:
                return _success_payload(
                    kb_periods[0],
                    periods=kb_periods,
                    analysis_dimension=analysis_dimension,
                    data_origin="local_kb_file",
                    source=str(kb_file.relative_to(kb_root.parent.parent)),
                    notes="结构化财务画像，源自本地知识库 financials/ Markdown（含多期）",
                )

    if resolved_code:
        try:
            sina_periods = fetch_multi_period_profiles(
                resolved_code,
                stock_name=resolved_name or stock_name,
            )
        except Exception as exc:
            logger.warning("Sina financial profile lookup failed for %s: %s", resolved_code, exc)
            sina_periods = []
        if sina_periods:
            return _success_payload(
                sina_periods[0],
                periods=sina_periods,
                analysis_dimension=analysis_dimension,
                data_origin="sina_api",
                source="https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022",
                notes="结构化财务画像，源自新浪财经公开 API 实时拉取（含多期）",
            )

    return _not_found_payload(analysis_dimension=analysis_dimension)
