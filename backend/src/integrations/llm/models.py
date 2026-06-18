"""Typed models for LLM integration results."""

from dataclasses import dataclass, field
from typing import Any, Literal

ResponseKind = Literal["calculator", "stock", "data", "hotspot"]


@dataclass
class LLMCallMeta:
    """Observability metadata for one LLM HTTP call."""

    model: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str
    raw_json: dict[str, Any]


@dataclass
class IntentResult:
    """Structured intent recognition output."""

    response_kind: ResponseKind
    intent_level_1: str
    intent_level_2: str
    subject_type: str
    subject_name: str
    action_type: str
    risk_level: str
    route_reason: str
    sub_agent: str
    agent_label: str
    meta: LLMCallMeta


@dataclass
class AnswerResult:
    """Structured answer generation output."""

    content: str
    response_kind: ResponseKind
    rich_blocks: list[dict[str, Any]]
    meta: LLMCallMeta


@dataclass
class QualityCheckResult:
    """Structured quality and compliance check output."""

    overall_result: Literal["PASS", "FAIL", "REVISE"]
    compliance_scan: dict[str, Any]
    citation_check: dict[str, Any]
    data_consistency: dict[str, Any]
    format_check: dict[str, Any]
    risk_tip_present: bool
    blacklist_expressions_found: list[str] = field(default_factory=list)
    revision_suggestions: list[str] = field(default_factory=list)
    writing_quality: dict[str, Any] = field(default_factory=dict)
    meta: LLMCallMeta | None = None
