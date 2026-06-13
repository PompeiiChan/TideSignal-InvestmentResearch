"""Prompt templates for investment research LLM tasks."""

from __future__ import annotations

from ._shared import (
    ANSWER_STREAM_SYSTEM_PROMPT_BASE,
    ANSWER_SYSTEM_PROMPT_BASE,
    LEGACY_INTENT_SYSTEM_PROMPT_BASE,
    QUALITY_SYSTEM_PROMPT_BASE,
    answer_stream_system_prompt,
    answer_system_prompt,
    legacy_intent_system_prompt,
    quality_system_prompt,
    with_system_time,
)
from .intent import (
    INTENT_SYSTEM_PROMPT_BASE as LANGGRAPH_INTENT_SYSTEM_PROMPT_BASE,
)
from .intent import intent_system_prompt as langgraph_intent_system_prompt

# Backward-compatible exports for existing LLMService imports
INTENT_SYSTEM_PROMPT_BASE = LEGACY_INTENT_SYSTEM_PROMPT_BASE
INTENT_SYSTEM_PROMPT = LEGACY_INTENT_SYSTEM_PROMPT_BASE
ANSWER_STREAM_SYSTEM_PROMPT = ANSWER_STREAM_SYSTEM_PROMPT_BASE
ANSWER_SYSTEM_PROMPT = ANSWER_SYSTEM_PROMPT_BASE
QUALITY_SYSTEM_PROMPT = QUALITY_SYSTEM_PROMPT_BASE

intent_system_prompt = legacy_intent_system_prompt

__all__ = [
    "ANSWER_STREAM_SYSTEM_PROMPT",
    "ANSWER_STREAM_SYSTEM_PROMPT_BASE",
    "ANSWER_SYSTEM_PROMPT",
    "ANSWER_SYSTEM_PROMPT_BASE",
    "INTENT_SYSTEM_PROMPT",
    "INTENT_SYSTEM_PROMPT_BASE",
    "QUALITY_SYSTEM_PROMPT",
    "QUALITY_SYSTEM_PROMPT_BASE",
    "answer_stream_system_prompt",
    "answer_system_prompt",
    "LANGGRAPH_INTENT_SYSTEM_PROMPT_BASE",
    "intent_system_prompt",
    "langgraph_intent_system_prompt",
    "quality_system_prompt",
    "with_system_time",
]
