"""Trace step recorder for LangGraph node execution."""

from __future__ import annotations

from typing import Any, Literal

NODE_DISPLAY_NAMES: dict[str, str] = {
    "context_preprocess": "上下文预处理",
    "intent_recognition": "意图识别",
    "slot_extraction": "槽位抽取",
    "clarification_check": "澄清判断",
    "clarification_response": "澄清回复",
    "routing_decision": "路由决策",
    "hotspot_agent": "热点解读 Agent",
    "data_query_agent": "问数 Agent",
    "stock_analysis_agent": "问股 Agent",
    "document_qa_agent": "文档问答 Agent",
    "tool_call": "工具调用",
    "rag_retrieval": "RAG 检索",
    "evidence_merge": "证据聚合",
    "evidence_gap_check": "证据缺口判断",
    "gap_planner": "补数规划",
    "multi_agent_handoff": "多 Agent 切换",
    "quality_check": "质检合规",
    "response_assembly": "回答组装",
    "fallback_response": "兜底回复",
    "END": "流程结束",
}


class TraceRecorder:
    """Build TraceStep dicts aligned with langgraph-flow.md node IDs."""

    @staticmethod
    def record(
        *,
        node: str,
        step_index: int,
        status: Literal["success", "failed"],
        latency_ms: int,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        summary: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Return a complete trace step dict for persistence."""
        step_id = f"step_{step_index:03d}"
        return {
            "step_id": step_id,
            "step_index": step_index,
            "name": NODE_DISPLAY_NAMES.get(node, node),
            "node": node,
            "status": status,
            "latency_ms": latency_ms,
            "summary": summary,
            "detail_sections": [],
            "input": input_data,
            "output": output_data,
            "raw_json": {
                "node": node,
                "input": input_data,
                "output": output_data,
                "latency_ms": latency_ms,
            },
            "error": error,
        }
