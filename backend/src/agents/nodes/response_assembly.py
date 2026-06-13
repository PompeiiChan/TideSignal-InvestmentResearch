"""response_assembly node."""

from __future__ import annotations

import json
from typing import Any, cast

from ...integrations.langgraph.state import AgentState
from ...integrations.langgraph.status_phases import emit_stream_phase
from ...integrations.llm.models import IntentResult, LLMCallMeta, ResponseKind
from ...integrations.llm.prompts.assembly import assembly_system_prompt
from ...integrations.llm.rich_block_builders import (
    build_calculator_rich_payload,
    build_sector_heatmap_payload,
)
from ...integrations.llm.service import LLMService
from ...services.citation_catalog import (
    build_citation_catalog,
    format_citation_context,
    normalize_assembly_citations,
    strip_unusable_financial_tool,
)
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


def _build_rich_blocks_from_evidence(
    llm: LLMService,
    *,
    content: str,
    response_kind: ResponseKind,
    evidence_pack: dict[str, Any],
    rag_hits: list[RagHit],
) -> list[dict[str, Any]]:
    """Attach only interactive rich blocks; citations and risk live in Markdown content."""
    blocks: list[dict[str, Any]] = []
    tool_result = evidence_pack.get("tool_result") or {}
    if response_kind == "data" and isinstance(tool_result, dict):
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
        else:
            ranking_tool: dict[str, Any] = {}
            for tool_key in ("market_ranking_lookup", "mock_market_ranking_lookup"):
                candidate = tool_result.get(tool_key)
                if isinstance(candidate, dict) and candidate.get("rows"):
                    ranking_tool = candidate
                    break
            rows = ranking_tool.get("rows") if isinstance(ranking_tool, dict) else None
            if isinstance(rows, list) and rows:
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
        calc_tool = tool_result.get("local_return_calculator") or {}
        if isinstance(calc_tool, dict) and "net_profit" in calc_tool:
            blocks.append(
                {
                    "type": "calculator",
                    "title": "收益率测算",
                    "payload": build_calculator_rich_payload(calc_tool),
                    "sources": [{"type": "knowledge", "label": "本地公式计算"}],
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
        cleaned_tool_result = strip_unusable_financial_tool(tool_result)
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
        evidence_text = json.dumps(assembly_evidence, ensure_ascii=False)
        user_prompt = (
            f"用户问题：{normalized_query}\n\n"
            f"evidence_pack：\n{evidence_text}\n\n"
        )
        if revision_suggestions:
            user_prompt += f"质检修订建议：{'; '.join(revision_suggestions)}\n\n"
        if citation_context:
            user_prompt += f"{citation_context}\n\n"
        user_prompt += "请直接输出 Markdown 正文。"

        system_prompt = assembly_system_prompt(time_ctx, response_kind=response_kind_str)
        client = llm._output_client()

        def _emit_delta(delta: str) -> None:
            if callable(stream_callback) and delta:
                stream_callback({"event": "content_delta", "data": {"delta": delta}})

        def _emit_content_replace(content: str) -> None:
            if callable(stream_callback):
                stream_callback({"event": "content_done", "data": {"content": content}})

        def _emit_content_reset() -> None:
            if callable(stream_callback):
                stream_callback({"event": "content_reset", "data": {}})

        async def _stream_completion(prompt: str, *, temperature: float) -> str:
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
                _emit_delta(delta)
            return "".join(parts).strip()

        content = await _stream_completion(user_prompt, temperature=0.4) or "以下是对您问题的整理。"
        content = normalize_assembly_citations(content, catalog)
        if evidence_requires_citations(rag_hits=rag_hits, evidence_pack=assembly_evidence):
            if content_needs_citation_retry(content):
                emit_stream_phase(stream_callback, "rewriting")
                _emit_content_reset()
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
                content = await _stream_completion(retry_prompt, temperature=0.3) or content
                content = normalize_assembly_citations(content, catalog)

        _emit_content_replace(content)
        response_kind = cast(ResponseKind, intent_stub.response_kind)
        rich_blocks = _build_rich_blocks_from_evidence(
            llm,
            content=content,
            response_kind=response_kind,
            evidence_pack=evidence_pack,
            rag_hits=rag_hits,
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
