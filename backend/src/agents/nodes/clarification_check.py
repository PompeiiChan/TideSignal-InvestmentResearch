"""clarification_check node."""

from __future__ import annotations

from typing import Any

from ...integrations.langgraph.state import AgentState
from ...integrations.llm.service import LLMService
from ...services.rag.chunker import resolve_kb_root
from ...services.rag.company_index import (
    is_kb_resolvable_document_query,
    is_kb_resolved_stock,
    is_truly_ambiguous_stock_name,
)
from ...services.rag.service import RagService
from ...settings import BACKEND_ROOT, AppSettings
from ._helpers import normalize_string_list, run_node_with_trace

_CONFIDENCE_THRESHOLD = 0.70
_DEFAULTABLE_SLOTS = frozenset({"time_range"})
_OPTIONAL_STOCK_SLOTS = frozenset({"stock_code", "analysis_dimension"})


def _slot_value(slots: dict[str, Any], key: str) -> str:
    value = slots.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _has_stock_identifier(slots: dict[str, Any]) -> bool:
    return bool(_slot_value(slots, "stock_name") or _slot_value(slots, "stock_code"))


def _has_document_reference(slots: dict[str, Any], context_pack: dict[str, Any]) -> bool:
    if _slot_value(slots, "document_id"):
        return True
    return bool(context_pack.get("active_document_id") or context_pack.get("has_document_context"))


def _missing_core_slots(
    intent_id: str,
    slots: dict[str, Any],
    context_pack: dict[str, Any],
    *,
    normalized_query: str = "",
    kb_root: Any = None,
) -> list[str]:
    missing: list[str] = []
    if intent_id == "stock_analysis" and not _has_stock_identifier(slots):
        missing.append("stock_name")
    if intent_id == "data_query" and not _slot_value(slots, "metric"):
        missing.append("metric")
    if intent_id == "document_qa" and not _has_document_reference(slots, context_pack):
        if kb_root is not None and is_kb_resolvable_document_query(normalized_query, slots, kb_root):
            pass
        else:
            missing.append("document_id")
    return missing


def _normalize_slot_lists_for_clarification(
    *,
    intent_id: str,
    query: str,
    slots: dict[str, Any],
    missing_slots: list[str],
    ambiguous_slots: list[str],
    kb_root: Any,
) -> tuple[list[str], list[str]]:
    """Drop optional / auto-resolvable slots from clarification triggers."""
    filtered_missing = list(missing_slots)
    filtered_ambiguous = list(ambiguous_slots)

    if intent_id == "document_qa" and is_kb_resolvable_document_query(query, slots, kb_root):
        filtered_missing = [name for name in filtered_missing if name != "document_id"]
        return filtered_missing, filtered_ambiguous

    if intent_id != "stock_analysis":
        return filtered_missing, filtered_ambiguous

    if _has_stock_identifier(slots):
        filtered_missing = [name for name in filtered_missing if name not in _OPTIONAL_STOCK_SLOTS]

    stock_name = _slot_value(slots, "stock_name")
    kb_resolved = is_kb_resolved_stock(query, slots, kb_root)
    if stock_name and kb_resolved and not is_truly_ambiguous_stock_name(stock_name):
        filtered_ambiguous = [
            name for name in filtered_ambiguous if name not in {"stock_code", "stock_name"}
        ]
    elif _slot_value(slots, "stock_name") and _slot_value(slots, "stock_code"):
        filtered_ambiguous = [name for name in filtered_ambiguous if name != "stock_code"]

    return filtered_missing, filtered_ambiguous


def _build_clarification_questions(
    *,
    intent_id: str,
    missing_core: list[str],
    ambiguous_slots: list[str],
    low_confidence: bool,
) -> list[str]:
    questions: list[str] = []
    if low_confidence:
        questions.append("请补充说明您想了解的热点解读、个股分析、数据查询还是文档问答？")
    for slot_name in ambiguous_slots:
        if slot_name == "stock_name":
            questions.append("您提到的标的存在歧义，请确认具体股票名称或代码。")
        else:
            questions.append(f"请澄清「{slot_name}」的具体含义。")
    for slot_name in missing_core:
        if slot_name == "stock_name":
            questions.append("请提供您想分析的股票名称或代码。")
        elif slot_name == "metric":
            questions.append("请说明您想查询的具体指标或排行类型。")
        elif slot_name == "document_id":
            questions.append("请指定要解读的研报、年报或公告文档。")
        else:
            questions.append(f"请补充「{slot_name}」信息。")
    return questions


async def clarification_check(
    state: AgentState,
    *,
    llm: LLMService,
    rag: RagService,
    settings: AppSettings,
) -> dict[str, Any]:
    """Pure-rule clarification gate before routing."""
    _ = (llm, rag)
    intent_id = str(state.get("intent_id", "unknown"))
    intent_confidence = float(state.get("intent_confidence", 0.0))
    normalized_query = str(state.get("normalized_query", "")).strip()
    slots = state.get("slots") or {}
    context_pack = state.get("context_pack") or {}
    kb_root = resolve_kb_root(settings.local_kb_path, BACKEND_ROOT)
    raw_missing = normalize_string_list(state.get("missing_slots"))
    raw_ambiguous = normalize_string_list(state.get("ambiguous_slots"))
    missing_slots, ambiguous_slots = _normalize_slot_lists_for_clarification(
        intent_id=intent_id,
        query=normalized_query,
        slots=slots,
        missing_slots=raw_missing,
        ambiguous_slots=raw_ambiguous,
        kb_root=kb_root,
    )

    input_data = {
        "intent_id": intent_id,
        "intent_confidence": intent_confidence,
        "slots": slots,
        "missing_slots": missing_slots,
        "ambiguous_slots": ambiguous_slots,
    }

    async def _execute() -> tuple[dict[str, Any], str]:
        reasons: list[str] = []
        need_clarification = False

        low_confidence = intent_confidence < _CONFIDENCE_THRESHOLD
        if low_confidence:
            need_clarification = True
            reasons.append(f"意图置信度 {intent_confidence:.2f} 低于阈值 {_CONFIDENCE_THRESHOLD}")

        missing_core = _missing_core_slots(
            intent_id,
            slots,
            context_pack,
            normalized_query=normalized_query,
            kb_root=kb_root,
        )
        if missing_core:
            need_clarification = True
            reasons.append(f"核心槽位缺失：{', '.join(missing_core)}")

        if ambiguous_slots:
            need_clarification = True
            reasons.append(f"槽位存在歧义：{', '.join(ambiguous_slots)}")

        defaultable_missing = [name for name in missing_slots if name in _DEFAULTABLE_SLOTS]
        non_defaultable_missing = [name for name in missing_slots if name not in _DEFAULTABLE_SLOTS]
        if non_defaultable_missing and not need_clarification:
            need_clarification = True
            reasons.append(f"关键槽位缺失：{', '.join(non_defaultable_missing)}")

        if defaultable_missing and not need_clarification:
            reasons.append(
                f"{'、'.join(defaultable_missing)} 缺失但可使用默认近一交易日"
            )

        clarification_questions = _build_clarification_questions(
            intent_id=intent_id,
            missing_core=missing_core,
            ambiguous_slots=ambiguous_slots,
            low_confidence=low_confidence,
        )

        output = {
            "need_clarification": need_clarification,
            "clarification_reason": "；".join(reasons) if reasons else "信息足够，进入路由",
            "clarification_questions": clarification_questions,
        }
        summary = "需要澄清" if need_clarification else "无需澄清，进入路由"
        return output, summary

    return await run_node_with_trace(
        state,
        node="clarification_check",
        input_data=input_data,
        summary="完成澄清判断",
        fn=_execute,
    )
