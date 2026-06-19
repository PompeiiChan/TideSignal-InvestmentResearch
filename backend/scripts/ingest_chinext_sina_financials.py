#!/usr/bin/env python3
"""Ingest ChiNext (300xxx) financial reports from Sina Finance API into knowledge-base.

Usage:
    cd backend && PYTHONPATH=.. python scripts/ingest_chinext_sina_financials.py
    cd backend && PYTHONPATH=.. python scripts/ingest_chinext_sina_financials.py --dry-run
    cd backend && PYTHONPATH=.. python scripts/ingest_chinext_sina_financials.py --refresh
    cd backend && PYTHONPATH=.. python scripts/ingest_chinext_sina_financials.py --refresh --codes 300296,300033
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.services.rag.financial_ingest import (
    count_financial_data_sections,
    pick_financial_periods,
    summarize_financial_kb_file,
)

KB_ROOT = BACKEND_ROOT / "data" / "knowledge-base"
FINANCIALS_DIR = KB_ROOT / "financials"
STRUCTURED_DIR = KB_ROOT / "structured-data"
COMPANIES_MD = STRUCTURED_DIR / "companies.md"
MANIFEST_MD = STRUCTURED_DIR / "document_manifest.md"
DELIVERY_JSON = STRUCTURED_DIR / "companies_chinext_batch1.json"
REPORT_MD = PROJECT_ROOT / ".sdd" / "test-reports" / "T-024-ingestion-report.md"
SINA_REPORT_NUM = 12

RANDOM_SEED = 20260612
SAMPLE_SIZE = 50
EXCLUDE_CODES = {"300750"}
MIN_INTERVAL = 1.0

SINA_URL = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
EM_CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

LRB_KEYS = [
    "营业总收入",
    "营业收入",
    "营业成本",
    "营业利润",
    "利润总额",
    "净利润",
    "归属于母公司所有者的净利润",
    "基本每股收益",
    "稀释每股收益",
]
FZB_KEYS = [
    "资产总计",
    "负债和所有者权益(或股东权益)总计",
    "所有者权益(或股东权益)合计",
    "归属于母公司所有者权益合计",
    "流动资产合计",
    "流动负债合计",
]
LLB_KEYS = [
    "经营活动产生的现金流量净额",
    "投资活动产生的现金流量净额",
    "筹资活动产生的现金流量净额",
    "现金及现金等价物净增加额",
]

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.headers.update({"User-Agent": UA})
_last_call = 0.0


@dataclass
class CompanyInfo:
    code: str
    name: str
    industry: str = ""


@dataclass
class PeriodReport:
    period_key: str
    period_date: str
    lrb: dict[str, str]
    fzb: dict[str, str]
    llb: dict[str, str]


@dataclass
class IngestResult:
    code: str
    name: str
    slug: str
    file_path: Path
    doc_ids: list[str] = field(default_factory=list)
    period_keys: list[str] = field(default_factory=list)
    error: str | None = None


def _throttled_get(url: str, params: dict[str, Any] | None = None, *, timeout: int = 20) -> requests.Response:
    global _last_call
    last_exc: Exception | None = None
    for attempt in range(3):
        wait = MIN_INTERVAL - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout)
            _last_call = time.time()
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            _last_call = time.time()
            time.sleep(1.5 * (attempt + 1))
    raise last_exc or RuntimeError("request failed")


def _parse_clist_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    diff = payload.get("data", {}).get("diff")
    if not diff:
        return []
    if isinstance(diff, dict):
        return [item for item in diff.values() if isinstance(item, dict)]
    if isinstance(diff, list):
        return [item for item in diff if isinstance(item, dict)]
    return []


def fetch_chinext_universe() -> list[CompanyInfo]:
    """Fetch all ChiNext (300xxx) listed stocks from Eastmoney."""
    companies: list[CompanyInfo] = []
    page = 1
    page_size = 500
    while True:
        params = {
            "pn": str(page),
            "pz": str(page_size),
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fs": "m:0+t:80",
            "fields": "f12,f14,f100",
        }
        resp = _throttled_get(EM_CLIST_URL, params)
        payload = resp.json()
        items = _parse_clist_items(payload)
        if not items:
            break
        for item in items:
            code = str(item.get("f12", "")).zfill(6)
            if not code.startswith("300"):
                continue
            companies.append(
                CompanyInfo(
                    code=code,
                    name=str(item.get("f14", "")).strip(),
                    industry=str(item.get("f100") or "").strip(),
                )
            )
        total = int(payload.get("data", {}).get("total") or 0)
        if page * page_size >= total:
            break
        page += 1
    return companies


def sample_companies(companies: list[CompanyInfo], *, seed: int, size: int) -> list[CompanyInfo]:
    pool = [c for c in companies if c.code not in EXCLUDE_CODES]
    rng = random.Random(seed)
    if len(pool) < size:
        raise RuntimeError(f"ChiNext pool too small: {len(pool)} < {size}")
    return sorted(rng.sample(pool, size), key=lambda c: c.code)


def _slugify(name: str, code: str) -> str:
    try:
        from pypinyin import lazy_pinyin

        slug = "-".join(lazy_pinyin(name))
    except ImportError:
        slug = f"chinext-{code}"
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or f"chinext-{code}"


def _period_date(period_key: str) -> str:
    return f"{period_key[:4]}-{period_key[4:6]}-{period_key[6:8]}"


def _pick_periods(report_lists: dict[str, dict[str, Any]]) -> list[str]:
    return pick_financial_periods(report_lists)


def _extract_items(report_obj: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for it in report_obj.get("data", []) or []:
        title = str(it.get("item_title") or "").strip()
        val = it.get("item_value")
        if title and val not in (None, ""):
            out[title] = str(val)
    return out


def sina_fetch_report_list(code: str, report_type: str, num: int = SINA_REPORT_NUM) -> dict[str, dict[str, Any]]:
    params = {
        "paperCode": f"sz{code}",
        "source": report_type,
        "type": "0",
        "page": "1",
        "num": str(num),
    }
    resp = _throttled_get(SINA_URL, params)
    return resp.json().get("result", {}).get("data", {}).get("report_list", {}) or {}


def fetch_period_reports(code: str) -> dict[str, PeriodReport]:
    lrb_list = sina_fetch_report_list(code, "lrb")
    fzb_list = sina_fetch_report_list(code, "fzb")
    llb_list = sina_fetch_report_list(code, "llb")
    all_keys = set(lrb_list) | set(fzb_list) | set(llb_list)
    selected_keys = _pick_periods({key: {} for key in all_keys})
    reports: dict[str, PeriodReport] = {}
    for key in selected_keys:
        reports[key] = PeriodReport(
            period_key=key,
            period_date=_period_date(key),
            lrb=_extract_items(lrb_list.get(key, {})),
            fzb=_extract_items(fzb_list.get(key, {})),
            llb=_extract_items(llb_list.get(key, {})),
        )
    return reports


def _first_value(data: dict[str, str], keys: list[str]) -> str | None:
    for k in keys:
        if k in data and data[k]:
            return data[k]
    return None


def _fmt_amount(raw: str | None) -> str:
    if raw is None:
        return "—"
    try:
        val = float(raw)
    except ValueError:
        return raw
    if abs(val) >= 1e8:
        return f"{val / 1e8:.4f} 亿元"
    if abs(val) >= 1e4:
        return f"{val / 1e4:.2f} 万元"
    return f"{val:.2f} 元"


def _compute_gross_margin(lrb: dict[str, str]) -> str | None:
    revenue = _first_value(lrb, ["营业收入", "营业总收入"])
    cost = lrb.get("营业成本")
    if not revenue or not cost:
        return None
    try:
        rev, c = float(revenue), float(cost)
        if rev == 0:
            return None
        return f"{(rev - c) / rev * 100:.2f}%"
    except ValueError:
        return None


def _compute_roe(lrb: dict[str, str], fzb: dict[str, str]) -> str | None:
    profit = _first_value(lrb, ["归属于母公司所有者的净利润", "净利润"])
    equity = _first_value(
        fzb,
        ["归属于母公司所有者权益合计", "所有者权益(或股东权益)合计"],
    )
    if not profit or not equity:
        return None
    try:
        p, e = float(profit), float(equity)
        if e == 0:
            return None
        return f"{p / e * 100:.2f}%"
    except ValueError:
        return None


def _report_kind(period_key: str) -> tuple[str, str, str]:
    """Return (doc_type, time_period, section_title)."""
    if period_key.endswith("1231"):
        year = period_key[:4]
        return "annual_report", f"{year}A", f"{year} 年年度报告"
    if period_key.endswith("0331"):
        year = period_key[:4]
        return "quarterly_report", f"{year}Q1", f"{year} 年第一季度报告"
    month = period_key[4:6]
    day = period_key[6:8]
    year = period_key[:4]
    return "quarterly_report", f"{year}Q{int(month) // 3 or 1}", f"{year} 年{month}月{day}日报告"


def _doc_id(doc_type: str, code: str, period_key: str) -> str:
    year = period_key[:4]
    if doc_type == "annual_report":
        return f"ann_{code}_{year}"
    if period_key.endswith("0331"):
        return f"q1_{code}_{year}"
    return f"q_{code}_{period_key}"


def _metadata_table(
    *,
    doc_id: str,
    doc_type: str,
    title: str,
    code: str,
    name: str,
    industry_id: str,
    time_period: str,
    filename: str,
) -> str:
    lines = [
        "| 字段 | 内容 |",
        "|---|---|",
        f"| doc_id | {doc_id} |",
        f"| 资料类型 | {doc_type} |",
        f"| 标题 | {title} |",
        f"| 公司ID | company_{code} |",
        f"| 行业ID | {industry_id} |",
        f"| 时间口径 | {time_period} |",
        "| 发布日期 |  |",
        "| 来源 | 新浪财经公开 API |",
        f"| 原始路径 | sina://finance/{code} |",
        "| is_mock | false |",
        "| 备注 | T-019 新浪财报 API 入库 |",
        "| 迁移后目录 | financials |",
        f"| 迁移文件 | {filename} |",
    ]
    return "\n".join(lines)


def _financial_tables(report: PeriodReport) -> str:
    rows: list[tuple[str, str, str]] = []

    def add_section(label: str, data: dict[str, str], keys: list[str]) -> None:
        for k in keys:
            if k in data:
                rows.append((label, k, _fmt_amount(data[k])))

    add_section("利润表", report.lrb, LRB_KEYS)
    gm = _compute_gross_margin(report.lrb)
    if gm:
        rows.append(("利润表", "毛利率（推算）", gm))
    roe = _compute_roe(report.lrb, report.fzb)
    if roe:
        rows.append(("指标", "净资产收益率 ROE（推算）", roe))
    add_section("资产负债表", report.fzb, FZB_KEYS)
    add_section("现金流量表", report.llb, LLB_KEYS)

    if not rows:
        return "_（新浪 API 未返回可用财务科目）_\n"

    lines = [
        "| 报表 | 科目 | 数值 |",
        "| --- | --- | --- |",
    ]
    for section, item, val in rows:
        lines.append(f"| {section} | {item} | {val} |")
    return "\n".join(lines) + "\n"


def _sorted_period_keys(reports: dict[str, PeriodReport]) -> list[str]:
    """Interim reports first, then annuals newest-to-oldest."""
    keys = list(reports.keys())
    interim = [key for key in keys if not key.endswith("1231")]
    annuals = sorted([key for key in keys if key.endswith("1231")], reverse=True)
    ordered: list[str] = []
    for key in interim:
        if key not in ordered:
            ordered.append(key)
    for key in annuals:
        if key not in ordered:
            ordered.append(key)
    return ordered


def _periods_label(reports: dict[str, PeriodReport]) -> str:
    labels: list[str] = []
    for key in _sorted_period_keys(reports):
        _, tp, _ = _report_kind(key)
        labels.append(tp)
    return "-".join(labels) if labels else "unknown"


def build_markdown(
    company: CompanyInfo, reports: dict[str, PeriodReport], slug: str
) -> tuple[str, list[str], list[str]]:
    code = company.code
    industry_id = "industry_chinext"
    plabel = _periods_label(reports)
    filename = f"{code}-{slug}-financial-{plabel}.md"
    doc_ids: list[str] = []

    parts = [
        f"# {company.name}（{code}）财务资料：{plabel}",
        "",
        "> 迁移说明：本文由新浪财经公开 API 整理为 Markdown，用于智能投研 demo、RAG 检索与评测。本文不构成投资建议。",
        "",
        "## 迁移元数据",
        "",
    ]

    header_tables: list[str] = []
    for key in _sorted_period_keys(reports):
        doc_type, time_period, section_title = _report_kind(key)
        doc_id = _doc_id(doc_type, code, key)
        doc_ids.append(doc_id)
        title = f"{company.name}{section_title.replace(' ', '')}"
        header_tables.append(
            _metadata_table(
                doc_id=doc_id,
                doc_type=doc_type,
                title=title,
                code=code,
                name=company.name,
                industry_id=industry_id,
                time_period=time_period,
                filename=filename,
            )
        )
    parts.append("\n\n".join(header_tables))
    parts.extend(
        [
            "",
            "## 文件说明",
            "",
            f"本文合并 {company.name} 的新浪财经三表数据（利润表/资产负债表/现金流量表），"
            f"报告期：{', '.join(r.period_date for r in reports.values())}。",
            "",
        ]
    )

    for key in _sorted_period_keys(reports):
        report = reports[key]
        doc_type, time_period, section_title = _report_kind(key)
        doc_id = _doc_id(doc_type, code, key)
        title = f"{company.name}{section_title.replace(' ', '')}"
        parts.extend(
            [
                f"## {section_title}",
                "",
                _metadata_table(
                    doc_id=doc_id,
                    doc_type=doc_type,
                    title=title,
                    code=code,
                    name=company.name,
                    industry_id=industry_id,
                    time_period=time_period,
                    filename=filename,
                ),
                "",
                "### 主要财务数据",
                "",
                _financial_tables(report),
            ]
        )

    period_keys = _sorted_period_keys(reports)
    return "\n".join(parts), doc_ids, period_keys


def ingest_company(company: CompanyInfo) -> IngestResult:
    slug = _slugify(company.name, company.code)
    try:
        reports = fetch_period_reports(company.code)
        if not reports:
            return IngestResult(
                code=company.code,
                name=company.name,
                slug=slug,
                file_path=FINANCIALS_DIR / f"{company.code}-{slug}-financial-unknown.md",
                error="no report periods",
            )
        content, doc_ids, period_keys = build_markdown(company, reports, slug)
        plabel = _periods_label(reports)
        out_path = FINANCIALS_DIR / f"{company.code}-{slug}-financial-{plabel}.md"
        removed_paths = _remove_stale_financial_files(company.code, keep_path=out_path)
        _ = removed_paths
        out_path.write_text(content, encoding="utf-8")
        section_count = count_financial_data_sections(content)
        return IngestResult(
            code=company.code,
            name=company.name,
            slug=slug,
            file_path=out_path,
            doc_ids=doc_ids,
            period_keys=period_keys,
            error=None if section_count >= 2 else f"only {section_count} financial sections",
        )
    except Exception as exc:
        return IngestResult(
            code=company.code,
            name=company.name,
            slug=slug,
            file_path=FINANCIALS_DIR / f"{company.code}-{slug}-financial-unknown.md",
            error=str(exc),
        )


def _remove_stale_financial_files(code: str, *, keep_path: Path) -> list[Path]:
    removed: list[Path] = []
    for path in FINANCIALS_DIR.glob(f"{code}-*.md"):
        if path.resolve() == keep_path.resolve():
            continue
        path.unlink(missing_ok=True)
        removed.append(path)
    return removed


def _remove_manifest_rows_for_codes(text: str, codes: set[str]) -> str:
    if not codes:
        return text
    pattern = re.compile(r"^\| (?:ann|q1|q)_(" + "|".join(re.escape(code) for code in sorted(codes)) + r")_")
    lines = []
    for line in text.splitlines():
        if pattern.match(line):
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _load_companies_from_json(path: Path) -> list[CompanyInfo]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [CompanyInfo(code=str(item["code"]).zfill(6), name=str(item["name"])) for item in payload]


def _filter_companies(
    companies: list[CompanyInfo],
    *,
    codes: set[str] | None,
    limit: int | None,
) -> list[CompanyInfo]:
    filtered = companies
    if codes:
        filtered = [company for company in filtered if company.code in codes]
    if limit is not None and limit > 0:
        filtered = filtered[:limit]
    return filtered


def _manifest_row(doc_id: str, company: CompanyInfo, period_key: str, file_path: Path) -> str:
    doc_type, time_period, section_title = _report_kind(period_key)
    rel = file_path.relative_to(BACKEND_ROOT)
    return (
        f"| {doc_id} | {doc_type} | {company.name}{section_title.replace(' ', '')} | company_{company.code} | industry_chinext | "
        f"{time_period} |  | 新浪财经公开 API | {rel.as_posix()} | false | T-019 新浪财报 API 入库 |"
    )


def _company_row(company: CompanyInfo) -> str:
    return (
        f"| company_{company.code} | {company.name} | {company.code}.SZ | SZSE_CHINEXT | industry_chinext | A股 | "
        f"创业板上市公司，新浪财经财报 API 入库（T-019） |"
    )


def _update_companies_md(companies: list[CompanyInfo]) -> None:
    text = COMPANIES_MD.read_text(encoding="utf-8")
    for company in companies:
        marker = f"company_{company.code}"
        if marker in text:
            continue
        text += "\n" + _company_row(company)
    existing_rows = len(re.findall(r"^\| company_\d", text, re.MULTILINE))
    text = re.sub(r"- 数据行数：\d+", f"- 数据行数：{existing_rows}", text, count=1)
    COMPANIES_MD.write_text(text, encoding="utf-8")


def _update_manifest_md(results: list[IngestResult], *, refresh_codes: set[str] | None = None) -> None:
    text = MANIFEST_MD.read_text(encoding="utf-8")
    if refresh_codes:
        text = _remove_manifest_rows_for_codes(text, refresh_codes)
    new_rows: list[str] = []
    for res in results:
        if res.error or not res.doc_ids:
            continue
        company = CompanyInfo(code=res.code, name=res.name)
        for doc_id, period_key in zip(res.doc_ids, res.period_keys, strict=False):
            if doc_id in text:
                continue
            new_rows.append(_manifest_row(doc_id, company, period_key, res.file_path))
    if new_rows:
        text = text.rstrip() + "\n" + "\n".join(new_rows) + "\n"
    total_rows = len(re.findall(r"^\| (?:ann_|q1_|q_|research_|event_|industry_)", text, re.MULTILINE))
    text = re.sub(r"- 数据行数：\d+", f"- 数据行数：{total_rows}", text, count=1)
    text = re.sub(
        r"- mock 标记统计：`is_mock=true` \d+ 行，`is_mock=false` \d+ 行。",
        f"- mock 标记统计：`is_mock=true` 0 行，`is_mock=false` {total_rows} 行。",
        text,
        count=1,
    )
    MANIFEST_MD.write_text(text, encoding="utf-8")


def _write_delivery_json(companies: list[CompanyInfo], *, merge: bool = False) -> None:
    if merge and DELIVERY_JSON.exists():
        existing: dict[str, dict[str, str]] = {}
        for item in json.loads(DELIVERY_JSON.read_text(encoding="utf-8")):
            code = str(item.get("code", "")).zfill(6)
            if code:
                existing[code] = {"code": code, "name": str(item.get("name", ""))}
        for company in companies:
            existing[company.code] = {"code": company.code, "name": company.name}
        payload = [existing[code] for code in sorted(existing)]
    else:
        payload = [{"code": c.code, "name": c.name} for c in companies]
    DELIVERY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_report(
    *,
    sampled: list[CompanyInfo],
    results: list[IngestResult],
    pytest_summary: str,
    mode: str,
) -> None:
    ok = [r for r in results if not r.error]
    fail = [r for r in results if r.error]
    section_samples: list[str] = []
    for res in ok[:8]:
        summary = summarize_financial_kb_file(res.file_path)
        section_samples.append(
            f"- `{res.code}` {res.name}: sections={summary['financial_sections']} "
            f"annual={summary['annual_sections']} interim={summary['interim_sections']} "
            f"periods={','.join(res.period_keys)}"
        )
    lines = [
        "# T-024 知识库财报扩容入库报告",
        "",
        f"- 生成时间（UTC）：{datetime.now(UTC).isoformat()}",
        f"- 模式：{mode}",
        f"- 随机种子：{RANDOM_SEED}",
        f"- 处理数量：{len(sampled)}",
        f"- 成功：{len(ok)}",
        f"- 失败：{len(fail)}",
        "",
        "## 期数抽样",
        "",
        *section_samples,
        "",
        "## 样本 doc_id",
        "",
    ]
    for r in ok[:5]:
        lines.append(f"- `{r.code}` {r.name}: {', '.join(r.doc_ids)}")
    if fail:
        lines.extend(["", "## 失败列表", ""])
        for r in fail:
            lines.append(f"- `{r.code}` {r.name}: {r.error}")
    lines.extend(["", "## 检索冒烟 / pytest", "", pytest_summary, ""])
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _run_pytest_summary() -> str:
    import subprocess

    cmd = [sys.executable, "-m", "pytest", "backend/tests/test_rag_service.py", "-q", "--tb=no"]
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return out.strip() or f"pytest exit {proc.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest ChiNext Sina financials into knowledge-base.")
    parser.add_argument("--dry-run", action="store_true", help="Only sample and print targets, no writes.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-ingest companies from delivery JSON (T-024 KB upgrade).",
    )
    parser.add_argument(
        "--from-json",
        type=Path,
        default=None,
        help="Reuse sampled companies from delivery JSON (skip Eastmoney universe fetch).",
    )
    parser.add_argument(
        "--codes",
        type=str,
        default="",
        help="Comma-separated stock codes to process (with --refresh or --from-json).",
    )
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N companies.")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--size", type=int, default=SAMPLE_SIZE)
    args = parser.parse_args()

    code_filter = {code.strip().zfill(6) for code in args.codes.split(",") if code.strip()}
    limit = args.limit if args.limit > 0 else None

    if args.refresh or args.from_json:
        source = args.from_json or DELIVERY_JSON
        sampled = _load_companies_from_json(source)
        mode = "refresh" if args.refresh else "from-json"
    else:
        universe = fetch_chinext_universe()
        sampled = sample_companies(universe, seed=args.seed, size=args.size)
        mode = "sample"

    sampled = _filter_companies(sampled, codes=code_filter or None, limit=limit)
    if args.dry_run:
        for c in sampled:
            print(c.code, c.name)
        return 0

    results: list[IngestResult] = []
    for company in sampled:
        results.append(ingest_company(company))

    ok_results = [r for r in results if not r.error]
    refresh_codes = {res.code for res in ok_results} if mode == "refresh" else None
    _update_companies_md(sampled)
    _update_manifest_md(ok_results, refresh_codes=refresh_codes)
    _write_delivery_json(sampled, merge=bool(code_filter))
    pytest_summary = _run_pytest_summary()
    _write_report(sampled=sampled, results=results, pytest_summary=pytest_summary, mode=mode)

    ok = len(ok_results)
    fail = len(results) - ok
    print(f"Done: success={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
