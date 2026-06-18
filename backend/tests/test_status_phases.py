"""Tests for user-facing progress timeline SSE events."""

from __future__ import annotations

from src.integrations.langgraph.status_phases import (
    ProgressTimelineTracker,
    emit_node_complete_status,
    emit_node_entry_status,
    emit_tool_progress_end,
    emit_tool_progress_start,
)


def _collect_events() -> tuple[list[dict], ProgressTimelineTracker]:
    events: list[dict] = []

    def callback(event: dict) -> None:
        events.append(event)

    tracker = ProgressTimelineTracker(callback)
    return events, tracker


def test_main_flow_step_sequence() -> None:
    events, tracker = _collect_events()
    state = {"progress_tracker": tracker, "route_target": "stock_analysis_agent", "slots": {"stock_name": "泸州老窖"}}

    emit_node_entry_status(state, "context_preprocess")
    emit_node_complete_status(state, "context_preprocess")
    emit_node_entry_status(state, "intent_recognition")
    emit_node_complete_status(state, "slot_extraction")
    emit_node_complete_status(state, "routing_decision", {
        "route_target": "stock_analysis_agent",
        "execution_plan": {"needs_tool": True, "needs_rag": True},
    })
    emit_tool_progress_start(state, ["mock_financial_profile_lookup"], {"stock_name": "泸州老窖"})
    emit_tool_progress_end(state, ["mock_financial_profile_lookup"])
    emit_node_entry_status(state, "rag_retrieval")
    emit_node_complete_status(state, "rag_retrieval")
    emit_node_entry_status(state, "quality_check")
    emit_node_complete_status(state, "quality_check")
    emit_node_entry_status(state, "response_assembly")
    tracker.on_response_stream_start()

    event_names = [event["event"] for event in events]
    assert "step_start" in event_names
    assert "step_complete" in event_names
    assert "response_stream_start" in event_names

    labels = [
        event["data"]["step"]["label"]
        for event in events
        if event["event"] == "step_start" and "step" in event["data"]
    ]
    assert "正在理解您的问题" in labels
    assert "正在识别问题类型" in labels
    assert any("问股分析" in label for label in labels)
    assert "正在获取相关资料" in labels
    assert "正在审核回答质量" in labels
    assert "正在生成回答" in labels


def test_clarification_branch_stops_before_expert_match() -> None:
    events, tracker = _collect_events()
    state = {
        "progress_tracker": tracker,
        "intent_confidence": 0.4,
        "missing_slots": ["stock_name"],
    }

    emit_node_entry_status(state, "context_preprocess")
    emit_node_complete_status(state, "context_preprocess")
    emit_node_entry_status(state, "intent_recognition")
    emit_node_complete_status(state, "slot_extraction")
    emit_node_complete_status(state, "clarification_check", {"need_clarification": True})

    labels = [
        event["data"]["step"]["label"]
        for event in events
        if event["event"] == "step_start"
    ]
    assert any("正在确认关键信息" in label for label in labels)
    assert not any("正在匹配投研专家" in label for label in labels)
    assert not any("正在获取相关资料" in label for label in labels)


def test_fallback_branch_suffix() -> None:
    events, tracker = _collect_events()
    state = {
        "progress_tracker": tracker,
        "intent_id": "prediction_request",
    }

    emit_node_entry_status(state, "context_preprocess")
    emit_node_complete_status(state, "context_preprocess")
    emit_node_entry_status(state, "intent_recognition")
    emit_node_complete_status(state, "slot_extraction")
    emit_node_complete_status(state, "routing_decision", {
        "route_target": "fallback_response",
        "execution_plan": {"needs_tool": False, "needs_rag": False},
    })
    emit_node_entry_status(state, "fallback_response")
    emit_node_complete_status(state, "fallback_response")

    labels = [
        event["data"]["step"]["label"]
        for event in events
        if event["event"] == "step_start"
    ]
    assert any("正在准备说明" in label and "无法提供预测性结论" in label for label in labels)
    assert not any("正在匹配投研专家" in label for label in labels)


def test_response_stream_start_emits_summary() -> None:
    events, tracker = _collect_events()
    tracker._expert_label = "问股分析"
    tracker.on_response_stream_start()

    payload = next(event for event in events if event["event"] == "response_stream_start")["data"]
    assert payload["summary"] == "问股分析"
