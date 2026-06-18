"""response_assembly node."""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from ...integrations.langgraph.state import AgentState
from ...integrations.langgraph.status_phases import emit_stream_phase
from ...integrations.llm.client import LLMClientError
from ...integrations.llm.models import IntentResult, LLMCallMeta, ResponseKind
from ...integrations.llm.prompts.assembly import assembly_system_prompt
from ...integrations.llm.rich_block_builders import (
    build_calculator_rich_payload,
    build_scenario_calculator_rich_payload,
    build_sector_heatmap_payload,
)
from ...integrations.llm.service import LLMService
from ...services.citation_catalog import (
    CitationCatalog,
    build_citation_catalog,
    format_citation_context,
    normalize_assembly_citations,
    strip_unusable_financial_tool,
)
from ...services.message_sanitizer import ensure_public_risk_notice
from ...services.rag.models import RagHit
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ._helpers import run_node_with_trace
from .citation_rules import (
    content_needs_citation_retry,
    evidence_requires_citations,
    paragraphs_missing_trailing_citations,
)

_ASSEMBLY_EVIDENCE_MAX_CHARS = 12_000


def _compact_evidence_for_prompt(evidence_pack: dict[str, Any]) -> str:
    """Shrink evidence JSON so long hotspot/stock packs do not blow LLM timeouts."""
    compact = json.loads(json.dumps(evidence_pack, ensure_ascii=False))
    tool_result = compact.get("tool_result")
    if isinstance(tool_result, dict):
        for _key, payload in list(tool_result.items()):
            if not isinstance(payload, dict):
                continue
            for list_key in ("rows", "tiles", "articles", "announcements", "highlights"):
                items = payload.get(list_key)
                if isinstance(items, list) and len(items) > 8:
                    payload[list_key] = items[:8]
    rag_hits = compact.get("rag_hits")
    if isinstance(rag_hits, list) and len(rag_hits) > 6:
        compact["rag_hits"] = rag_hits[:6]
    text = json.dumps(compact, ensure_ascii=False)
    if len(text) <= _ASSEMBLY_EVIDENCE_MAX_CHARS:
        return text
    return text[:_ASSEMBLY_EVIDENCE_MAX_CHARS] + "…"


def _fallback_assembly_content(evidence_pack: dict[str, Any], query: str) -> str:
    """Readable draft when the output model times out."""
    agent_result = str(evidence_pack.get("agent_result") or "").strip()
    body = agent_result or f"以下是对「{query}」的简要整理（完整生成超时，展示已有证据摘要）。"
    return ensure_public_risk_notice(body)


def _build_intent_stub(state: AgentState) -> IntentResult:
    response_kind = str(state.get("response_kind", "data"))
    if response_kind not in {"stock", "data", "hotspot", "calculator"}:
        response_kind = "data"
    intent_id = str(state.get("intent_id", "data_query"))
    return IntentResult(
        response_kind=cast(ResponseKind, response_kind),
        intent_level_1=intent_id,
        intent_level_2="信息整理",
        subject_type="market",
        subject_name=str(state.get("normalized_query", ""))[:40],
        action_type="查询",
        risk_level="medium",
        route_reason=str(state.get("route_reason", "")),
        sub_agent="data_agent",
        agent_label="投研助手",
        meta=LLMCallMeta(
            model="langgraph",
            latency_ms=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            finish_reason="stop",
            raw_json={},
        ),
    )


def _rag_hits_from_state(state: AgentState) -> list[RagHit]:
    hits: list[RagHit] = []
    for item in state.get("rag_hits") or []:
        if isinstance(item, dict):
            try:
                hits.append(RagHit.model_validate(item))
            except Exception:
                continue
    return hits


def _append_market_data_rich_blocks(
    blocks: list[dict[str, Any]],
    tool_result: dict[str, Any],
) -> None:
    """Attach sector heatmap / ranking table blocks from market tools."""
    heatmap_tool = tool_result.get("sector_heatmap_lookup")
    if isinstance(heatmap_tool, dict) and heatmap_tool.get("tiles"):
        source_label = str(heatmap_tool.get("source", "行情数据"))
        if heatmap_tool.get("is_mock"):
            source_label = "本地 demo 行业板块（降级）"
        blocks.append(
            {
                "type": "sector_heatmap",
                "title": "行业板块热力图",
                "payload": build_sector_heatmap_payload(heatmap_tool),
                "sources": [{"type": "market", "label": source_label}],
                "risk_notice": "以上内容仅为信息整理，不构成投资建议。",
            }
        )

    ranking_tool: dict[str, Any] = {}
    for tool_key in ("market_ranking_lookup", "mock_market_ranking_lookup"):
        candidate = tool_result.get(tool_key)
        if isinstance(candidate, dict) and candidate.get("rows"):
            ranking_tool = candidate
            break
    rows = ranking_tool.get("rows") if isinstance(ranking_tool, dict) else None
    if not isinstance(rows, list) or not rows:
        return
    source_label = str(ranking_tool.get("source", "行情数据"))
    if ranking_tool.get("is_mock"):
        source_label = "本地 demo 行情（降级）"
    columns = ["rank", "stock_name", "pct_change", "close_price"]
    slim_rows = [{col: row.get(col) for col in columns} for row in rows if isinstance(row, dict)]
    ranking_mode = str(ranking_tool.get("ranking_mode", ""))
    industry_label = str(ranking_tool.get("industry", "")).strip()
    if ranking_mode == "board_stocks" and industry_label:
        title = f"{industry_label}成分股涨幅"
    elif ranking_mode == "industry_boards":
        title = "行业板块涨幅"
    else:
        title = "行情排行"
    blocks.append(
        {
            "type": "ranking_table",
            "title": title,
            "payload": {"columns": columns, "rows": slim_rows},
            "sources": [{"type": "market", "label": source_label}],
            "risk_notice": "以上内容仅为信息整理，不构成投资建议。",
        }
    )


def _build_rich_blocks_from_evidence(
    llm: LLMService,
    *,
    content: str,
    response_kind: ResponseKind,
    evidence_pack: dict[str, Any],
    rag_hits: list[RagHit],
    catalog: CitationCatalog | None = None,
) -> list[dict[str, Any]]:
    """Attach only interactive rich blocks; citations and risk live in Markdown content."""
    blocks: list[dict[str, Any]] = []
    tool_result = evidence_pack.get("tool_result") or {}
    if response_kind in {"data", "hotspot", "compound_stock_data"} and isinstance(tool_result, dict):
        _append_market_data_rich_blocks(blocks, tool_result)
    if response_kind == "data" and isinstance(tool_result, dict):
        calc_tool = tool_result.get("local_return_calculator") or {}
        if isinstance(calc_tool, dict) and "net_profit" in calc_tool:
            if calc_tool.get("scenario_return_mode") and catalog is not None:
                forecast_tool = tool_result.get("earnings_forecast_lookup")
                blocks.append(
                    {
                        "type": "scenario_calculator",
                        "title": "预期回报率情景测算",
                        "payload": build_scenario_calculator_rich_payload(
                            calc_tool,
                            forecast_tool if isinstance(forecast_tool, dict) else None,
                            catalog,
                        ),
                        "sources": [{"type": "market", "label": "情景测算（现价 + 机构一致预期 EPS×PE）"}],
                        "risk_notice": "测算结果仅供参考，不构成投资建议。",
                    }
                )
            elif not calc_tool.get("scenario_return_mode"):
                blocks.append(
                    {
                        "type": "calculator",
                        "title": "收益率测算",
                        "payload": build_calculator_rich_payload(calc_tool),
                        "sources": [{"type": "knowledge", "label": "本地公式计算"}],
                        "risk_notice": "测算结果仅供参考，不构成投资建议。",
                    }
                )
    if (
        response_kind == "stock"
        and isinstance(tool_result, dict)
        and isinstance(calc_tool := tool_result.get("local_return_calculator") or {}, dict)
        and calc_tool.get("scenario_return_mode")
        and "net_profit" in calc_tool
        and catalog is not None
        and not any(block.get("type") == "scenario_calculator" for block in blocks)
    ):
        forecast_tool = tool_result.get("earnings_forecast_lookup")
        blocks.append(
            {
                "type": "scenario_calculator",
                "title": "预期回报率情景测算",
                "payload": build_scenario_calculator_rich_payload(
                    calc_tool,
                    forecast_tool if isinstance(forecast_tool, dict) else None,
                    catalog,
                ),
                "sources": [{"type": "market", "label": "情景测算（现价 + 机构一致预期 EPS×PE）"}],
                "risk_notice": "测算结果仅供参考，不构成投资建议。",
            }
        )
    return llm.enrich_rich_blocks(content, blocks, response_kind, rag_hits)


async def response_assembly(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Stream final answer from evidence_pack and enrich rich blocks."""
    _ = rag
    normalized_query = str(state.get("normalized_query", "")).strip()
    evidence_pack = state.get("evidence_pack") or {}
    revision_suggestions = state.get("revision_suggestions") or []
    stream_callback = state.get("stream_callback")
    intent_stub = _build_intent_stub(state)
    rag_hits = _rag_hits_from_state(state)
    time_ctx = resolve_system_time(settings)

    input_data = {
        "query": normalized_query,
        "response_kind": state.get("response_kind", "data"),
        "revision_suggestions": revision_suggestions,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        tool_result = evidence_pack.get("tool_result") if isinstance(evidence_pack.get("tool_result"), dict) else {}
        cleaned_tool_result = strip_unusable_financial_tool(tool_result or {})
        assembly_evidence = {**evidence_pack, "tool_result": cleaned_tool_result}
        response_kind_str = str(state.get("response_kind", "data"))
        catalog = build_citation_catalog(
            rag_hits,
            cleaned_tool_result,
            response_kind=response_kind_str,
        )
        citation_context = format_citation_context(
            catalog,
            rag_hits,
            cleaned_tool_result,
            ctx=time_ctx,
        )
        evidence_text = _compact_evidence_for_prompt(assembly_evidence)
        user_prompt = (
            f"用户问题：{normalized_query}\n\n"
            f"evidence_pack：\n{evidence_text}\n\n"
        )
        if revision_suggestions:
            user_prompt += f"质检修订建议：{'; '.join(revision_suggestions)}\n\n"
        if citation_context:
            user_prompt += f"{citation_context}\n\n"
        if assembly_evidence.get("stock_narrative_evidence_missing") or assembly_evidence.get(
            "stock_kb_uncovered"
        ):
            user_prompt += (
                "【强制约束】本地未收录该公司券商深度研报或本轮未命中 company-reports/industry-reports 片段。"
                "不得编造具体药品、靶点或管线品种名称；须先声明证据不足。\n\n"
            )
        user_prompt += "请直接输出 Markdown 正文。"

        system_prompt = assembly_system_prompt(
            time_ctx,
            response_kind=response_kind_str,
            hotspot_evidence_mode=str(evidence_pack.get("hotspot_evidence_mode", "")),
        )
        client = llm._output_client()

        requires_citation_validation = evidence_requires_citations(
            rag_hits=rag_hits,
            evidence_pack=assembly_evidence,
        )
        can_stream = callable(stream_callback)
        streamed_to_client = False

        def _emit_delta(delta: str) -> None:
            nonlocal streamed_to_client
            if can_stream and delta:
                streamed_to_client = True
                stream_callback({"event": "content_delta", "data": {"delta": delta}})

        def _emit_content_replace(content: str) -> None:
            if can_stream:
                stream_callback({"event": "content_done", "data": {"content": content}})

        async def _emit_buffered_content(content: str, *, chunk_size: int = 64) -> None:
            """Reveal buffered text with a typewriter effect when LLM output was not streamed."""
            if not content:
                return
            for index in range(0, len(content), chunk_size):
                _emit_delta(content[index : index + chunk_size])
                await asyncio.sleep(0)

        async def _stream_completion(
            prompt: str,
            *,
            temperature: float,
            stream_to_client: bool,
        ) -> str:
            parts: list[str] = []
            async for delta in client.chat_completion_stream(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=2048,
            ):
                parts.append(delta)
                if stream_to_client:
                    _emit_delta(delta)
            return "".join(parts).strip()

        try:
            content = await _stream_completion(
                user_prompt,
                temperature=0.4,
                stream_to_client=can_stream,
            )
        except LLMClientError:
            content = _fallback_assembly_content(assembly_evidence, normalized_query)
        content = content or _fallback_assembly_content(assembly_evidence, normalized_query)
        content = normalize_assembly_citations(content, catalog)
        draft_content = content
        if requires_citation_validation and content_needs_citation_retry(content):
            emit_stream_phase(stream_callback, "rewriting")
            if can_stream and streamed_to_client:
                stream_callback({"event": "content_reset", "data": {}})
                streamed_to_client = False
            missing = paragraphs_missing_trailing_citations(content)
            missing_hint = ""
            if missing:
                missing_hint = (
                    "以下段落引用了事实/数字但段末缺少 citation，请逐段补在段末："
                    + "；".join(missing[:3])
                    + "。"
                )
            valid_nums = ", ".join(str(entry.index) for entry in catalog.entries) or "1"
            retry_prompt = (
                f"{user_prompt}\n\n"
                "【强制修订】正文须按**段落**标注引用：凡写入知识库/工具/研报事实或数字的段落，"
                f"在该段落**最后一句话末尾**仅使用 `[citation:N]`（N 为引用编号表中的数字：{valid_nums}），"
                "多来源合并写在段末（如 `[citation:2][citation:3]`）。"
                "禁止使用 `[citation:财务]`；无本地财报数据时不要编造财务类参考来源。"
                "禁止只在 `### 参考来源` 列文献而正文无 citation。"
                f"{missing_hint}"
                "文末须有 `### 参考来源` 并合并同源条目。"
            )
            try:
                revised = await _stream_completion(
                    retry_prompt,
                    temperature=0.3,
                    stream_to_client=can_stream,
                )
                revised = normalize_assembly_citations(revised or "", catalog)
                if revised.strip() and not content_needs_citation_retry(revised):
                    content = revised
                else:
                    content = draft_content
            except LLMClientError:
                content = draft_content

        pre_notice_content = content
        content = ensure_public_risk_notice(content)

        if not streamed_to_client and content:
            await _emit_buffered_content(content)
        elif content != pre_notice_content:
            _emit_delta(content[len(pre_notice_content) :])

        _emit_content_replace(content)
        response_kind = cast(ResponseKind, intent_stub.response_kind)
        rich_blocks = _build_rich_blocks_from_evidence(
            llm,
            content=content,
            response_kind=response_kind,
            evidence_pack=evidence_pack,
            rag_hits=rag_hits,
            catalog=catalog,
        )
        output = {
            "final_response": content,
            "response_kind": response_kind_str,
            "rich_blocks": rich_blocks,
            "response_meta": {"assembly": True, "citation_catalog": catalog.to_quality_payload()},
        }
        return output, "完成回答组装"

    return await run_node_with_trace(
        state,
        node="response_assembly",
        input_data=input_data,
        summary="完成回答组装",
        fn=_execute,
    )
