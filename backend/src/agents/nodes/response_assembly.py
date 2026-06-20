"""response_assembly node."""

from __future__ import annotations

import asyncio
import time
from typing import Any, cast
from uuid import uuid4

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
from ...services.conversation_context import build_conversation_context
from ...services.message_sanitizer import ensure_public_risk_notice, sanitize_rich_blocks
from ...services.rag.models import RagHit
from ...services.rag.service import RagService
from ...services.system_time import resolve_system_time
from ...settings import AppSettings
from ..assembly.citation_fix import (
    apply_citation_fix,
    build_citation_patch_prompt,
    pick_best_citation_content,
    relocate_citations_from_headings,
)
from ..assembly.profile import (
    PROFILE_MAX_TOKENS,
    AssemblyProfile,
    rag_hits_from_state,
    resolve_assembly_profile,
    use_compact_citation_context,
)
from ..assembly.prompt_builder import build_assembly_user_prompt
from ..assembly.template import finalize_template_content, try_template_assembly
from ._helpers import run_node_with_trace
from .citation_rules import (
    content_has_citation_markers,
    content_needs_citation_retry,
    count_paragraphs_missing_citations,
    evidence_requires_citations,
    paragraphs_missing_trailing_citations,
)


def _format_ranking_cell(field: str, value: Any) -> Any:
    if value is None or value == "":
        return None
    if field == "pct_change":
        try:
            pct = float(value)
        except (TypeError, ValueError):
            return value
        return f"{pct:+.2f}%"
    if field == "close_price":
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return value
    return value


def _build_ranking_table_payload(
    rows: list[dict[str, Any]],
    *,
    ranking_mode: str,
) -> dict[str, Any]:
    name_label = "板块" if ranking_mode == "industry_boards" else "股票"
    field_specs: tuple[tuple[str, str], ...] = (
        ("rank", "排名"),
        ("stock_name", name_label),
        ("pct_change", "涨跌幅"),
        ("close_price", "收盘价"),
    )
    columns = [label for _, label in field_specs]
    slim_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        formatted: dict[str, Any] = {}
        for field, label in field_specs:
            formatted[label] = _format_ranking_cell(field, row.get(field))
        slim_rows.append(formatted)
    return {"columns": columns, "rows": slim_rows}


def _fallback_assembly_content(evidence_pack: dict[str, Any], query: str) -> str:
    """Readable draft when the output model times out."""
    agent_result = str(evidence_pack.get("agent_result") or evidence_pack.get("agent_summary") or "").strip()
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


def _append_market_data_rich_blocks(
    blocks: list[dict[str, Any]],
    tool_result: dict[str, Any],
) -> None:
    """Attach sector heatmap / ranking table blocks from market tools."""
    heatmap_tool = tool_result.get("sector_heatmap_lookup")
    if isinstance(heatmap_tool, dict) and heatmap_tool.get("tiles"):
        source_label = str(heatmap_tool.get("source", "行情数据"))
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
    candidate = tool_result.get("market_ranking_lookup")
    if isinstance(candidate, dict) and candidate.get("rows"):
        ranking_tool = candidate
    rows = ranking_tool.get("rows") if isinstance(ranking_tool, dict) else None
    if not isinstance(rows, list) or not rows:
        return
    source_label = str(ranking_tool.get("source", "行情数据"))
    ranking_mode = str(ranking_tool.get("ranking_mode", ""))
    table_payload = _build_ranking_table_payload(rows, ranking_mode=ranking_mode)
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
            "payload": table_payload,
            "sources": [{"type": "market", "label": source_label}],
            "risk_notice": "以上内容仅为信息整理，不构成投资建议。",
        }
    )


def _prepare_rich_blocks_for_stream(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        normalized = dict(block)
        normalized.setdefault("id", f"block_{uuid4().hex[:10]}_{index:03d}")
        normalized.setdefault("title", "回答内容")
        normalized.setdefault("payload", {})
        normalized.setdefault("sources", [])
        normalized.setdefault(
            "risk_notice",
            "以上内容仅为信息整理，不构成投资建议。",
        )
        prepared.append(normalized)
    return sanitize_rich_blocks("assistant", prepared)


def _emit_stream_rich_blocks(
    stream_callback: Any,
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Push rich blocks to the client as soon as tool evidence is ready."""
    if not callable(stream_callback) or not blocks:
        return []
    prepared = _prepare_rich_blocks_for_stream(blocks)
    if prepared:
        stream_callback({"event": "rich_blocks", "data": {"rich_blocks": prepared}})
    return prepared


def _build_market_rich_blocks(
    *,
    response_kind: str,
    tool_result: dict[str, Any],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if response_kind in {"data", "hotspot", "compound_stock_data"}:
        _append_market_data_rich_blocks(blocks, tool_result)
    return blocks


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
    tool_result = evidence_pack.get("tool_result") if isinstance(evidence_pack.get("tool_result"), dict) else {}
    blocks = _build_market_rich_blocks(response_kind=response_kind, tool_result=tool_result)
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


def _build_assembly_detail_sections(assembly_trace: dict[str, Any]) -> list[dict[str, Any]]:
    prompt_stats = assembly_trace.get("prompt_stats") or {}
    items = [
        {"label": "assembly_profile", "value": str(assembly_trace.get("assembly_profile", ""))},
        {"label": "assembly_mode", "value": str(assembly_trace.get("assembly_mode", ""))},
        {"label": "LLM passes", "value": str(len(assembly_trace.get("llm_passes") or []))},
        {"label": "user prompt chars", "value": str(prompt_stats.get("user_chars", ""))},
        {"label": "citation context chars", "value": str(prompt_stats.get("citation_context_chars", ""))},
        {
            "label": "citation patch",
            "value": "yes" if assembly_trace.get("citation_patch_applied") else "no",
        },
    ]
    return [{"title": "组装性能", "items": items}]


def _patch_trace_step(result: dict[str, Any], assembly_trace: dict[str, Any]) -> None:
    steps = result.get("trace_steps") or []
    if not steps:
        return
    step = steps[-1]
    step["raw_json"] = {**step.get("raw_json", {}), **assembly_trace}
    step["detail_sections"] = _build_assembly_detail_sections(assembly_trace)


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
    rag_hits = rag_hits_from_state(state)
    time_ctx = resolve_system_time(settings)
    active_slots = state.get("active_slots") or state.get("slots") or {}
    history_summary = str(state.get("history_summary", "")).strip()
    conversation_context = build_conversation_context(
        history_summary=history_summary,
        active_slots=active_slots,
        inherited_slot_keys=state.get("inherited_slot_keys") or [],
        normalized_query=normalized_query,
    )
    profile = resolve_assembly_profile(state)
    assembly_trace: dict[str, Any] = {
        "assembly_profile": profile.value,
        "assembly_mode": "template" if profile == AssemblyProfile.TEMPLATE_SKIP else "llm",
        "prompt_stats": {},
        "llm_passes": [],
        "citation_retry_triggered": False,
        "citation_patch_applied": False,
        "citation_patch_paragraphs": 0,
    }

    input_data = {
        "query": normalized_query,
        "history_summary": history_summary,
        "active_slots": active_slots,
        "conversation_context": conversation_context,
        "response_kind": state.get("response_kind", "data"),
        "revision_suggestions": revision_suggestions,
        "assembly_profile": profile.value,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        tool_result = evidence_pack.get("tool_result") if isinstance(evidence_pack.get("tool_result"), dict) else {}
        cleaned_tool_result = strip_unusable_financial_tool(tool_result or {})
        assembly_evidence = {**evidence_pack, "tool_result": cleaned_tool_result}
        response_kind_str = str(state.get("response_kind", "data"))
        callback = stream_callback if callable(stream_callback) else None
        can_stream = callback is not None
        streamed_rich_blocks = (
            _emit_stream_rich_blocks(
                callback,
                _build_market_rich_blocks(
                    response_kind=response_kind_str,
                    tool_result=cleaned_tool_result,
                ),
            )
            if can_stream
            else []
        )
        rich_blocks_streamed = bool(streamed_rich_blocks)
        catalog = build_citation_catalog(
            rag_hits,
            cleaned_tool_result,
            response_kind=response_kind_str,
        )
        compact_citation = use_compact_citation_context(profile)
        citation_context = format_citation_context(
            catalog,
            rag_hits,
            cleaned_tool_result,
            ctx=time_ctx,
            compact=compact_citation,
        )
        prompt_parts = build_assembly_user_prompt(
            normalized_query=normalized_query,
            evidence_pack=assembly_evidence,
            citation_context=citation_context,
            catalog=catalog,
            conversation_context=conversation_context,
            revision_suggestions=list(revision_suggestions),
            time_ctx=time_ctx,
        )
        user_prompt = prompt_parts.user_prompt
        system_prompt = assembly_system_prompt(
            time_ctx,
            response_kind=response_kind_str,
            hotspot_evidence_mode=str(evidence_pack.get("hotspot_evidence_mode", "")),
            profile=profile.value,
        )
        assembly_trace["prompt_stats"] = {
            **prompt_parts.prompt_stats,
            "system_chars": len(system_prompt),
            "citation_context_mode": "compact" if compact_citation else "full",
        }

        requires_citation_validation = evidence_requires_citations(
            rag_hits=rag_hits,
            evidence_pack=assembly_evidence,
        )
        streamed_to_client = False

        def _emit_delta(delta: str) -> None:
            nonlocal streamed_to_client
            if can_stream and delta and callback is not None:
                streamed_to_client = True
                callback({"event": "content_delta", "data": {"delta": delta}})

        def _emit_content_replace(content: str) -> None:
            if can_stream and callback is not None:
                callback({"event": "content_done", "data": {"content": content}})

        async def _emit_buffered_content(content: str, *, chunk_size: int = 64) -> None:
            if not content:
                return
            for index in range(0, len(content), chunk_size):
                _emit_delta(content[index : index + chunk_size])
                await asyncio.sleep(0)

        max_tokens = PROFILE_MAX_TOKENS.get(profile, 2048)
        template_body = try_template_assembly(state) if profile == AssemblyProfile.TEMPLATE_SKIP else None
        content = ""

        if template_body:
            content = finalize_template_content(template_body, catalog)
            pre_notice_content = content
            content = ensure_public_risk_notice(content)
            if can_stream and content:
                if content != pre_notice_content:
                    _emit_delta(content[: len(pre_notice_content)])
                    _emit_delta(content[len(pre_notice_content) :])
                else:
                    await _emit_buffered_content(content)
            _emit_content_replace(content)
        else:
            client = llm._assembly_client()
            model_name = client.model

            async def _stream_completion(
                prompt: str,
                *,
                temperature: float,
                pass_name: str,
                stream_to_client: bool,
            ) -> str:
                started = time.perf_counter()
                parts: list[str] = []
                async for delta in client.chat_completion_stream(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    parts.append(delta)
                    if stream_to_client:
                        _emit_delta(delta)
                text = "".join(parts).strip()
                assembly_trace["llm_passes"].append(
                    {
                        "pass": pass_name,
                        "latency_ms": int((time.perf_counter() - started) * 1000),
                        "completion_tokens": len(text),
                        "streamed": stream_to_client,
                        "model": model_name,
                    }
                )
                return text

            try:
                content = await _stream_completion(
                    user_prompt,
                    temperature=0.4,
                    pass_name="first",
                    stream_to_client=can_stream,
                )
            except LLMClientError:
                content = _fallback_assembly_content(assembly_evidence, normalized_query)

            content = content or _fallback_assembly_content(assembly_evidence, normalized_query)
            content = normalize_assembly_citations(content, catalog)
            content, _ = relocate_citations_from_headings(content)
            draft_content = content
            heading_reloc_total = 0

            if requires_citation_validation and content_needs_citation_retry(content):
                assembly_trace["citation_missing_before_patch"] = count_paragraphs_missing_citations(
                    content
                )
                patched, patch_applied, patch_count = apply_citation_fix(content, catalog)
                assembly_trace["citation_patch_paragraphs"] = patch_count
                if patch_applied:
                    content = normalize_assembly_citations(patched, catalog)
                    assembly_trace["citation_patch_applied"] = True
                elif content_needs_citation_retry(patched):
                    content = patched
                    assembly_trace["citation_retry_triggered"] = True
                    emit_stream_phase(stream_callback, "rewriting")
                    missing = paragraphs_missing_trailing_citations(content)
                    patch_prompt = build_citation_patch_prompt(
                        missing_paragraphs=missing,
                        catalog=catalog,
                        needs_reference_section=not content_has_citation_markers(content)
                        or "### 参考来源" not in content,
                    )
                    retry_prompt = f"{content}\n\n{patch_prompt}"
                    try:
                        revised = await _stream_completion(
                            retry_prompt,
                            temperature=0.3,
                            pass_name="citation_patch",
                            stream_to_client=False,
                        )
                        revised = normalize_assembly_citations(revised or "", catalog)
                        content = pick_best_citation_content(
                            revised,
                            patched,
                            draft_content,
                        )
                        content = normalize_assembly_citations(content, catalog)
                    except LLMClientError:
                        content = normalize_assembly_citations(
                            pick_best_citation_content(patched, draft_content),
                            catalog,
                        )
                else:
                    content = normalize_assembly_citations(patched, catalog)
                    assembly_trace["citation_patch_applied"] = patch_count > 0
                assembly_trace["citation_missing_after_patch"] = count_paragraphs_missing_citations(
                    content
                )

            content, heading_reloc_final = relocate_citations_from_headings(content)
            heading_reloc_total += heading_reloc_final
            if heading_reloc_total:
                assembly_trace["citation_relocated_from_headings"] = heading_reloc_total
                content = normalize_assembly_citations(content, catalog)
                assembly_trace["citation_missing_after_patch"] = count_paragraphs_missing_citations(
                    content
                )

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
            "rich_blocks_streamed": rich_blocks_streamed,
            "response_meta": {
                "assembly": True,
                "citation_catalog": catalog.to_quality_payload(),
                "assembly_trace": assembly_trace,
            },
        }
        return output, "完成回答组装"

    result = await run_node_with_trace(
        state,
        node="response_assembly",
        input_data=input_data,
        summary="完成回答组装",
        fn=_execute,
    )
    _patch_trace_step(result, assembly_trace)
    return result
