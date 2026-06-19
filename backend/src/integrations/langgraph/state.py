"""LangGraph AgentState definition aligned with langgraph-flow.md."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state for the investment research LangGraph workflow."""

    # --- Request context (injected by Runner at graph entry) ---
    session_id: str
    message_id: str
    trace_id: str
    user_query: str
    chat_history: list[dict[str, str]]
    user_profile: dict[str, Any]
    request_meta: dict[str, Any]
    system_context: dict[str, str]

    # --- context_preprocess output ---
    normalized_query: str
    context_pack: dict[str, Any]
    history_summary: str
    risk_hint: str

    # --- intent_recognition output ---
    intent_id: str
    intent_name: str
    intent_confidence: float
    candidate_intents: list[dict[str, Any]]
    missing_slots: list[str]

    # --- Session pending slot carryover (injected by Runner) ---
    pending_slots: dict[str, Any]
    pending_intent_id: str
    pending_slot_confidence: dict[str, float]

    # --- slot_extraction output ---
    slots: dict[str, Any]
    active_slots: dict[str, Any]
    slot_confidence: dict[str, float]
    ambiguous_slots: list[str]
    inherited_slot_keys: list[str]
    overridden_slot_keys: list[str]
    conversation_context: dict[str, Any]

    # --- clarification_check output ---
    need_clarification: bool
    clarification_reason: str
    clarification_questions: list[str]

    # --- query_rewrite output (T-014) ---
    retrieval_query: str
    rewrite_method: str
    retrieval_query_changed: bool

    # --- clarification_response output ---
    next_expected_slots: list[str]

    # --- routing_decision output ---
    route_target: str
    route_targets: list[str]
    route_reason: str
    execution_plan: dict[str, Any]
    multi_agent_mode: bool
    multi_agent_stock_phase_done: bool
    multi_agent_data_phase_done: bool
    agent_summaries: dict[str, str]
    is_multi_intent: bool

    # --- Sub-agent output ---
    agent_result: str
    agent_tool_names: list[str]
    evidence_list: list[dict[str, Any]]
    followup_need: bool
    data_table: list[dict[str, Any]]
    data_source: str
    analysis_dimensions: list[str]
    quoted_chunks: list[dict[str, Any]]
    doc_citations: list[dict[str, Any]]
    document_id: str

    # --- tool_call output ---
    tool_params: dict[str, Any]
    tool_result: dict[str, Any]
    tool_status: Literal["success", "failed", "skipped"]
    tool_latency: int
    tool_error: str | None

    # --- rag_retrieval output ---
    retrieval_config: dict[str, Any]
    retrieved_chunks: list[dict[str, Any]]
    retrieval_score: float
    citations: list[dict[str, Any]]
    low_confidence_flag: bool
    rag_hits: list[dict[str, Any]]

    # --- evidence_merge output ---
    evidence_pack: dict[str, Any]
    citation_map: dict[str, Any]
    conflict_points: list[str]
    accumulated_rag_hits: list[dict[str, Any]]
    accumulated_tool_result: dict[str, Any]
    evidence_supplement_done: bool

    # --- evidence gap loop ---
    should_enrich_evidence: bool
    evidence_gaps: list[dict[str, Any]]
    gap_enrichment_plan: dict[str, Any]
    supplement_mode: bool
    supplement_rag_queries: list[str]
    supplement_rag_filters: dict[str, str]
    supplement_tool_names: list[str]

    # --- quality_check output ---
    quality_status: Literal["pass", "revise", "reject"]
    quality_score: float
    risk_level: str
    revision_suggestions: list[str]
    quality_check_payload: dict[str, Any]

    # --- Final output ---
    final_response: str
    response_meta: dict[str, Any]
    fallback_reason: str
    rich_blocks: list[dict[str, Any]]
    response_kind: str

    # --- Trace and runtime ---
    trace_steps: Annotated[list[dict[str, Any]], operator.add]
    current_node: str
    error: str | None
    stream_callback: Any
    progress_tracker: Any
