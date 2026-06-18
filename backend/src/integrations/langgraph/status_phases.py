"""User-facing progress timeline for LangGraph chat streams."""

from __future__ import annotations

from typing import Any, Literal

from ...integrations.langgraph.state import AgentState

StreamPhase = Literal["thinking", "checking", "writing", "rewriting", "enriching"]

_EXPERT_LABELS: dict[str, str] = {
    "stock_analysis_agent": "问股分析",
    "data_query_agent": "数据查询",
    "hotspot_agent": "热点解读",
    "document_qa_agent": "文档问答",
}

_CLARIFY_SLOT_SUFFIX: dict[str, str] = {
    "stock_name": "请补充股票名称或代码",
    "stock_code": "请补充股票名称或代码",
    "metric": "请补充关注的指标或分析维度",
    "time_range": "请补充时间范围",
    "document_id": "请指定要解读的文档或研报",
}

_FALLBACK_SUFFIX: dict[str, str] = {
    "prediction_request": "无法提供预测性结论",
    "quality_reject": "相关资料不足",
    "tool_failure": "数据暂时不可用",
    "out_of_scope": "超出投研范围",
    "general": "暂无法给出可靠结论",
}


class ProgressTimelineTracker:
    """Emit step_start / step_complete / response_stream_start SSE events."""

    def __init__(self, stream_callback: Any) -> None:
        self._cb = stream_callback
        self._started: set[str] = set()
        self._completed: set[str] = set()
        self._expert_label: str | None = None
        self._recognize_started = False
        self._fetch_materials_started = False
        self._stream_started = False
        self._needs_tool = False
        self._needs_rag = False
        self._tool_finished = False
        self._rag_finished = False
        self._branch: Literal["main", "clarify", "fallback"] = "main"

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if callable(self._cb):
            self._cb({"event": event, "data": data})

    def start_step(
        self,
        step_id: str,
        label: str,
        *,
        parent_id: str | None = None,
    ) -> None:
        _ = parent_id
        if step_id in self._started:
            return
        self._started.add(step_id)
        step: dict[str, Any] = {
            "step_id": step_id,
            "status": "running",
            "label": label,
        }
        self._emit("step_start", {"step": step})

    def complete_step(self, step_id: str) -> None:
        if step_id not in self._started or step_id in self._completed:
            return
        self._completed.add(step_id)
        self._emit("step_complete", {"step_id": step_id})

    def on_response_stream_start(self) -> None:
        if self._stream_started:
            return
        self._stream_started = True
        if "generate_answer" in self._started:
            self.complete_step("generate_answer")
        summary_parts: list[str] = []
        if self._expert_label:
            summary_parts.append(self._expert_label)
        payload: dict[str, Any] = {}
        if summary_parts:
            payload["summary"] = " · ".join(summary_parts)
        self._emit("response_stream_start", payload)

    def on_routing_complete(self, route_target: str, execution_plan: dict[str, Any]) -> None:
        self._needs_tool = bool(execution_plan.get("needs_tool"))
        self._needs_rag = bool(execution_plan.get("needs_rag"))
        if route_target == "fallback_response":
            self._branch = "fallback"
            return
        expert = _EXPERT_LABELS.get(route_target, "")
        label = "正在匹配投研专家"
        if expert:
            label = f"{label} · {expert}"
            self._expert_label = expert
        self.start_step("match_expert", label)
        self.complete_step("match_expert")

    def ensure_fetch_materials(self) -> None:
        if self._fetch_materials_started:
            return
        self._fetch_materials_started = True
        self.start_step("fetch_materials", "正在获取相关资料")

    def maybe_complete_fetch_materials(self) -> None:
        if not self._fetch_materials_started:
            return
        if self._needs_tool and not self._tool_finished:
            return
        if self._needs_rag and not self._rag_finished:
            return
        self.complete_step("fetch_materials")

    def on_tool_started(self, tool_names: list[str], slots: dict[str, Any]) -> None:
        _ = tool_names, slots
        if not tool_names:
            self._tool_finished = True
            self.maybe_complete_fetch_materials()
            return
        self.ensure_fetch_materials()

    def on_tool_finished(self, tool_names: list[str]) -> None:
        _ = tool_names
        self._tool_finished = True
        self.maybe_complete_fetch_materials()

    def on_rag_started(self, route_target: str, *, supplement: bool = False) -> None:
        _ = route_target, supplement
        self.ensure_fetch_materials()

    def on_rag_finished(self, route_target: str) -> None:
        _ = route_target
        self._rag_finished = True
        self.maybe_complete_fetch_materials()


def _clarify_suffix(state: AgentState | dict[str, Any]) -> str:
    if normalize_low_confidence(state):
        return "请补充您想了解的方向"
    ambiguous = state.get("ambiguous_slots") or []
    if isinstance(ambiguous, list):
        for slot in ambiguous:
            if str(slot) in {"stock_name", "stock_code"}:
                return "请确认您指的是哪只股票"
    missing = state.get("missing_slots") or state.get("pending_slots") or []
    if isinstance(missing, list):
        for slot in missing:
            key = str(slot)
            if key in _CLARIFY_SLOT_SUFFIX:
                return _CLARIFY_SLOT_SUFFIX[key]
    reason = str(state.get("clarification_reason", "")).strip()
    if "歧义" in reason:
        return "请确认您指的是哪只股票"
    if "股票" in reason:
        return "请补充股票名称或代码"
    if "指标" in reason or "metric" in reason:
        return "请补充关注的指标或分析维度"
    if "时间" in reason:
        return "请补充时间范围"
    if "文档" in reason:
        return "请指定要解读的文档或研报"
    if "意图" in reason or "方向" in reason:
        return "请补充您想了解的方向"
    return "需要更多信息才能继续"


def normalize_low_confidence(state: AgentState | dict[str, Any]) -> bool:
    try:
        confidence = float(state.get("intent_confidence", 1.0))
    except (TypeError, ValueError):
        confidence = 1.0
    return confidence < 0.70


def _fallback_suffix(state: AgentState) -> str:
    intent_id = str(state.get("intent_id", ""))
    if intent_id == "prediction_request" or state.get("risk_hint") == "prediction_boundary":
        return _FALLBACK_SUFFIX["prediction_request"]
    if state.get("quality_status") == "reject":
        return _FALLBACK_SUFFIX["quality_reject"]
    if state.get("tool_status") == "failed":
        return _FALLBACK_SUFFIX["tool_failure"]
    if intent_id in {"chit_chat", "unknown"}:
        return _FALLBACK_SUFFIX["out_of_scope"]
    reason_code = str(state.get("fallback_reason_code", state.get("fallback_reason", "general")))
    return _FALLBACK_SUFFIX.get(reason_code, _FALLBACK_SUFFIX["general"])


def get_progress_tracker(state: AgentState) -> ProgressTimelineTracker | None:
    tracker = state.get("progress_tracker")
    if isinstance(tracker, ProgressTimelineTracker):
        return tracker
    return None


def attach_progress_tracker(state: AgentState, tracker: ProgressTimelineTracker) -> None:
    state["progress_tracker"] = tracker


def emit_node_entry_status(state: AgentState, node: str) -> None:
    """Push progress step events when a node starts executing."""
    tracker = get_progress_tracker(state)
    if tracker is None:
        return

    if node == "context_preprocess":
        tracker.start_step("understand_query", "正在理解您的问题")
        return

    if node == "intent_recognition":
        if not tracker._recognize_started:
            tracker._recognize_started = True
            tracker.start_step("recognize_intent", "正在识别问题类型")
        return

    if node == "quality_check":
        tracker.start_step("quality_review", "正在审核回答质量")
        return

    if node == "response_assembly":
        tracker.start_step("generate_answer", "正在生成回答")
        return

    if node == "fallback_response":
        tracker._branch = "fallback"
        if tracker._recognize_started:
            tracker.complete_step("recognize_intent")
        suffix = _fallback_suffix(state)
        tracker.start_step("prepare_fallback", f"正在准备说明 · {suffix}")
        return

    if node == "clarification_response":
        tracker._branch = "clarify"
        return

    if node == "rag_retrieval":
        route_target = str(state.get("route_target", ""))
        tracker.on_rag_started(route_target, supplement=bool(state.get("supplement_mode")))
        return


def emit_node_complete_status(
    state: AgentState,
    node: str,
    result: dict[str, Any] | None = None,
) -> None:
    """Push progress step completion events after a node finishes."""
    tracker = get_progress_tracker(state)
    if tracker is None:
        return
    output = result or {}

    if node == "context_preprocess":
        tracker.complete_step("understand_query")
        return

    if node == "slot_extraction":
        tracker.complete_step("recognize_intent")
        return

    if node == "clarification_check":
        if output.get("need_clarification"):
            tracker._branch = "clarify"
            tracker.complete_step("recognize_intent")
            merged_state: dict[str, Any] = dict(state)
            merged_state.update(output)
            suffix = _clarify_suffix(merged_state)
            tracker.start_step("clarify_info", f"正在确认关键信息 · {suffix}")
        return

    if node == "routing_decision":
        route_target = str(output.get("route_target", state.get("route_target", "")))
        execution_plan = output.get("execution_plan") or state.get("execution_plan") or {}
        if not isinstance(execution_plan, dict):
            execution_plan = {}
        tracker.on_routing_complete(route_target, execution_plan)
        return

    if node == "rag_retrieval":
        route_target = str(state.get("route_target", ""))
        tracker.on_rag_finished(route_target)
        return

    if node == "quality_check":
        tracker.complete_step("quality_review")
        return

    if node == "clarification_response":
        tracker.complete_step("clarify_info")
        return

    if node == "fallback_response":
        tracker.complete_step("prepare_fallback")
        return

    if node == "response_assembly":
        if tracker._stream_started:
            tracker.complete_step("generate_answer")
        return


def emit_tool_progress_start(
    state: AgentState,
    tool_names: list[str],
    slots: dict[str, Any],
) -> None:
    tracker = get_progress_tracker(state)
    if tracker is not None:
        tracker.on_tool_started(tool_names, slots)


def emit_tool_progress_end(state: AgentState, tool_names: list[str]) -> None:
    tracker = get_progress_tracker(state)
    if tracker is not None:
        tracker.on_tool_finished(tool_names)


def build_status_event(phase: StreamPhase, label: str) -> dict[str, Any]:
    """Legacy status event — kept for backward compatibility in tests."""
    return {"event": "status", "data": {"phase": phase, "label": label}}


def emit_stream_phase(
    stream_callback: Any,
    phase: StreamPhase,
    label: str | None = None,
) -> None:
    """Legacy phase emitter — no-op for progress timeline."""
    _ = (stream_callback, phase, label)


def on_content_delta(state: AgentState) -> None:
    """Trigger timeline fold when the first answer token arrives."""
    tracker = get_progress_tracker(state)
    if tracker is not None:
        tracker.on_response_stream_start()
