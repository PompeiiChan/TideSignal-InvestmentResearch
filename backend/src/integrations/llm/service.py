"""High-level LLM workflows: intent, answer, quality check."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any, cast

from pycore.core import get_logger

from ...services.rag.models import RagHit
from ...services.rag.service import rag_citations_for_quality
from ...services.system_time import resolve_system_time
from ...settings import AppSettings, get_settings
from .client import LLMClientError, SiliconFlowLLMClient
from .models import AnswerResult, IntentResult, LLMCallMeta, QualityCheckResult, ResponseKind
from .prompts import (
    answer_stream_system_prompt,
    answer_system_prompt,
    intent_system_prompt,
    quality_system_prompt,
)

logger = get_logger()

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_VALID_KINDS = {"calculator", "stock", "data", "hotspot"}
_MODEL_OWN_KNOWLEDGE_SOURCE = {"type": "knowledge", "label": "模型自有知识，可能存在错误"}
_AGENT_LABELS = {
    "chit_chat": "测算组件",
    "stock_agent": "问股助手",
    "data_agent": "问数助手",
    "hotspot_agent": "热点助手",
}


class LLMNotConfiguredError(RuntimeError):
    """Raised when required LLM configuration is missing."""


class LLMService:
    """Orchestrates intent recognition, answer generation and quality checks."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        return self._output_credentials_ready() and self._intent_credentials_ready() and bool(
            self._intent_model_name()
        )

    def _intent_model_name(self) -> str:
        intent_model = self.settings.llm_intent_model.strip()
        if intent_model:
            return intent_model
        return self.settings.llm_model.strip()

    def _output_credentials_ready(self) -> bool:
        return bool(
            self.settings.llm_api_key.strip()
            and self.settings.llm_base_url.strip()
            and self.settings.llm_model.strip()
        )

    def _intent_credentials_ready(self) -> bool:
        return bool(
            self.settings.llm_intent_api_key.strip()
            and self.settings.llm_intent_base_url.strip()
            and self._intent_model_name()
        )

    def _client_for(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        role: str,
        timeout: float | None = None,
    ) -> SiliconFlowLLMClient:
        if not api_key.strip() or not base_url.strip():
            raise LLMNotConfiguredError(f"LLM {role} 配置不完整，请检查对应 API Key 与 Base URL")
        if not model.strip():
            raise LLMNotConfiguredError(f"LLM {role} 模型未配置")
        resolved_timeout = timeout
        if resolved_timeout is None:
            try:
                resolved_timeout = float(self.settings.llm_timeout.strip())
            except (TypeError, ValueError, AttributeError):
                resolved_timeout = 120.0
        return SiliconFlowLLMClient(
            api_key=api_key.strip(),
            base_url=base_url.strip(),
            model=model.strip(),
            timeout=resolved_timeout,
        )

    def _intent_client(self) -> SiliconFlowLLMClient:
        return self._client_for(
            api_key=self.settings.llm_intent_api_key,
            base_url=self.settings.llm_intent_base_url,
            model=self._intent_model_name(),
            role="意图识别",
        )

    def _output_client(self) -> SiliconFlowLLMClient:
        return self._client_for(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            model=self.settings.llm_model,
            role="主输出",
        )

    def _assembly_client(self) -> SiliconFlowLLMClient:
        assembly_model = self.settings.llm_assembly_model.strip()
        model = assembly_model or self.settings.llm_model
        assembly_timeout_raw = self.settings.llm_assembly_timeout.strip()
        timeout: float | None = None
        if assembly_timeout_raw:
            try:
                timeout = float(assembly_timeout_raw)
            except (TypeError, ValueError):
                timeout = None
        return self._client_for(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            model=model,
            role="回答组装",
            timeout=timeout,
        )

    async def recognize_intent(self, query: str) -> IntentResult:
        client = self._intent_client()
        time_ctx = resolve_system_time(self.settings)
        body = await client.chat_completion(
            [
                {"role": "system", "content": intent_system_prompt(time_ctx)},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
            max_tokens=1024,
            json_mode=True,
        )
        parsed = self._parse_json_payload(client.extract_message_content(body))
        response_kind = self._normalize_kind(parsed.get("response_kind"))
        sub_agent = str(parsed.get("sub_agent", "data_agent"))
        meta = self._to_meta(client, body, parsed)
        return IntentResult(
            response_kind=response_kind,
            intent_level_1=str(parsed.get("intent_level_1", "信息查询")),
            intent_level_2=str(parsed.get("intent_level_2", "综合整理")),
            subject_type=str(parsed.get("subject_type", "market")),
            subject_name=str(parsed.get("subject_name", query[:40])),
            action_type=str(parsed.get("action_type", "查询")),
            risk_level=str(parsed.get("risk_level", "medium")),
            route_reason=str(parsed.get("route_reason", "根据用户问题选择对应助手。")),
            sub_agent=sub_agent,
            agent_label=str(parsed.get("agent_label", _AGENT_LABELS.get(sub_agent, "投研助手"))),
            meta=meta,
        )

    async def generate_answer(self, query: str, intent: IntentResult) -> AnswerResult:
        client = self._output_client()
        time_ctx = resolve_system_time(self.settings)
        user_prompt = (
            f"用户问题：{query}\n"
            f"意图：{intent.intent_level_1}/{intent.intent_level_2}\n"
            f"response_kind：{intent.response_kind}\n"
            f"主体：{intent.subject_name}"
        )
        body = await client.chat_completion(
            [
                {"role": "system", "content": answer_system_prompt(time_ctx)},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=2048,
            json_mode=True,
        )
        parsed = self._parse_json_payload(client.extract_message_content(body))
        response_kind = self._normalize_kind(parsed.get("response_kind", intent.response_kind))
        content = str(parsed.get("content", "")).strip() or "以下是对您问题的整理。"
        raw_blocks = parsed.get("rich_blocks")
        blocks = raw_blocks if isinstance(raw_blocks, list) else []
        rich_blocks = self.enrich_rich_blocks(content, cast(list[dict[str, Any]], blocks), response_kind)
        meta = self._to_meta(client, body, parsed)
        return AnswerResult(
            content=content,
            response_kind=response_kind,
            rich_blocks=rich_blocks,
            meta=meta,
        )

    async def generate_answer_stream(
        self,
        query: str,
        intent: IntentResult,
        rag_context: str = "",
    ) -> AsyncIterator[str]:
        """Stream markdown answer text from the output model."""
        client = self._output_client()
        user_prompt = (
            f"用户问题：{query}\n"
            f"意图：{intent.intent_level_1}/{intent.intent_level_2}\n"
            f"主体：{intent.subject_name}\n"
        )
        if rag_context.strip():
            user_prompt += f"\n{rag_context.strip()}\n"
        user_prompt += "请直接输出 Markdown 正文；若提供了知识库参考片段，请优先引用其中的事实与 time_period 口径。"
        time_ctx = resolve_system_time(self.settings)
        async for delta in client.chat_completion_stream(
            [
                {"role": "system", "content": answer_stream_system_prompt(time_ctx)},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=2048,
        ):
            yield delta

    def build_answer_from_stream(
        self,
        query: str,
        intent: IntentResult,
        content: str,
        rag_hits: list[RagHit] | None = None,
    ) -> AnswerResult:
        """Build structured answer from streamed markdown body."""
        normalized = content.strip() or "以下是对您问题的整理。"
        response_kind = intent.response_kind
        rich_blocks = self.enrich_rich_blocks(normalized, [], response_kind, rag_hits)
        return AnswerResult(
            content=normalized,
            response_kind=response_kind,
            rich_blocks=rich_blocks,
            meta=LLMCallMeta(
                model=self.settings.llm_model,
                latency_ms=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                finish_reason="stop",
                raw_json={"provider": "siliconflow", "stream": True, "query": query[:120]},
            ),
        )

    async def quality_check(
        self,
        query: str,
        answer: AnswerResult,
        *,
        rag_hits: list[RagHit] | None = None,
    ) -> QualityCheckResult:
        client = self._intent_client()
        time_ctx = resolve_system_time(self.settings)
        payload = {
            "system_context": time_ctx.to_dict(),
            "query": query,
            "content": answer.content,
            "rich_blocks": answer.rich_blocks,
            "rag_citations": rag_citations_for_quality(rag_hits or []),
            "check_stage": "pre_assembly",
        }
        body = await client.chat_completion(
            [
                {"role": "system", "content": quality_system_prompt(time_ctx)},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.0,
            max_tokens=1024,
            json_mode=True,
        )
        parsed = self._parse_json_payload(client.extract_message_content(body))
        overall = str(parsed.get("overall_result", "PASS")).upper()
        if overall not in {"PASS", "FAIL", "REVISE"}:
            overall = "PASS"
        blacklist = parsed.get("blacklist_expressions_found")
        if not isinstance(blacklist, list):
            blacklist = []
        revision_suggestions = parsed.get("revision_suggestions")
        if not isinstance(revision_suggestions, list):
            revision_suggestions = []
        meta = self._to_meta(client, body, parsed)
        return QualityCheckResult(
            overall_result=cast(Any, overall),
            compliance_scan=self._as_dict(parsed.get("compliance_scan"), "合规扫描完成"),
            citation_check=self._as_dict(parsed.get("citation_check"), "引用检查完成"),
            data_consistency=self._as_dict(parsed.get("data_consistency"), "数据口径已标注"),
            format_check=self._as_dict(parsed.get("format_check"), "富响应结构完整"),
            risk_tip_present=bool(parsed.get("risk_tip_present", True)),
            blacklist_expressions_found=[str(item) for item in blacklist],
            revision_suggestions=[str(item) for item in revision_suggestions],
            writing_quality=self._as_dict(parsed.get("writing_quality"), "写作质量检查完成"),
            meta=meta,
        )

    def _to_meta(
        self,
        client: SiliconFlowLLMClient,
        body: dict[str, Any],
        parsed: dict[str, Any],
    ) -> LLMCallMeta:
        call_meta = client.build_call_meta(body)
        return LLMCallMeta(
            model=call_meta["model"] or client.model,
            latency_ms=call_meta["latency_ms"],
            prompt_tokens=call_meta["prompt_tokens"],
            completion_tokens=call_meta["completion_tokens"],
            total_tokens=call_meta["total_tokens"],
            finish_reason=call_meta["finish_reason"],
            raw_json={"provider": call_meta["provider"], "parsed": parsed, "usage": body.get("usage", {})},
        )

    @staticmethod
    def _parse_json_payload(content: str) -> dict[str, Any]:
        text = content.strip()
        match = _JSON_BLOCK_RE.search(text)
        if match:
            text = match.group(1).strip()

        candidates = [text]
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            candidates.append(text[start : end + 1])

        last_error: json.JSONDecodeError | None = None
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                last_error = exc
                continue
            if isinstance(parsed, dict):
                return parsed

        logger.error("Failed to parse LLM JSON payload", detail=text[:300])
        raise LLMClientError("LLM 返回内容无法解析为 JSON") from last_error

    @staticmethod
    def _normalize_kind(value: Any) -> ResponseKind:
        kind = str(value or "data").strip().lower()
        if kind not in _VALID_KINDS:
            return "data"
        return cast(ResponseKind, kind)

    @staticmethod
    def _as_dict(value: Any, default_summary: str) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {"summary": default_summary}

    @staticmethod
    def _is_markdown_table_line(line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") or bool(re.search(r"\|.+\|", stripped))

    @classmethod
    def split_body_paragraphs(cls, content: str) -> list[str]:
        text = content.strip()
        if not text:
            return []
        parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        if len(parts) > 1:
            return parts
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return [text]

        grouped: list[str] = []
        table_buffer: list[str] = []

        def flush_table() -> None:
            if table_buffer:
                grouped.append("\n".join(table_buffer))
                table_buffer.clear()

        for line in lines:
            if cls._is_markdown_table_line(line):
                table_buffer.append(line)
            else:
                flush_table()
                grouped.append(line)
        flush_table()
        return grouped if grouped else [text]

    @classmethod
    def enrich_rich_blocks(
        cls,
        content: str,
        blocks: list[dict[str, Any]],
        response_kind: ResponseKind,
        rag_hits: list[RagHit] | None = None,
    ) -> list[dict[str, Any]]:
        """Keep only interactive ranking_table / calculator blocks; citations and risk live in content."""
        _ = content, response_kind, rag_hits
        enriched: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type", ""))
            raw_payload = block.get("payload")
            payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
            if block_type in {"ranking_table", "calculator", "sector_heatmap", "scenario_calculator"} and payload:
                enriched.append(block)
        return enriched

    @staticmethod
    def default_blocks(
        content: str,
        response_kind: ResponseKind,
        rag_hits: list[RagHit] | None = None,
    ) -> list[dict[str, Any]]:
        """No default rich blocks; answer body, citations and risk are in Markdown content."""
        _ = content, response_kind, rag_hits
        return []
