"""Trace detail business service."""

from typing import Any, Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TraceRecord
from ..integrations.llm.models import AnswerResult, IntentResult, QualityCheckResult
from ..models.chat import TraceSummaryMetadata, TraceSummaryRead
from ..models.trace import RawTraceStepRead, TraceMetadataRead, TraceRead, TraceStepRead
from ..repositories.trace_repository import TraceRepository
from .rag.models import RagRetrievalResult
from .session_service import _now
from .system_time import resolve_system_time

ResponseKind = Literal["calculator", "stock", "data", "hotspot"]


class TraceNotFoundError(ValueError):
    """Raised when a trace cannot be found."""


class TraceStepNotFoundError(ValueError):
    """Raised when a trace step cannot be found."""


class TraceService:
    """Business logic for fallback Trace details."""

    def __init__(self, db: AsyncSession):
        self.repo = TraceRepository(db)

    async def create_fallback_trace(
        self,
        trace_id: str,
        session_id: str,
        message_id: str,
        user_query: str,
        response_kind: ResponseKind,
    ) -> TraceRecord:
        """Persist a full fallback trace that can be read by the management panel."""
        metadata = self._metadata(response_kind, user_query)
        trace = TraceRecord(
            id=trace_id,
            session_id=session_id,
            message_id=message_id,
            user_query=user_query,
            status="success",
            steps=self._steps(user_query, response_kind),
            trace_metadata=metadata,
            created_at=_now(),
        )
        return await self.repo.create_trace(trace)

    async def create_llm_trace(
        self,
        trace_id: str,
        session_id: str,
        message_id: str,
        user_query: str,
        intent: IntentResult,
        answer: AnswerResult,
        quality: QualityCheckResult,
        rag: RagRetrievalResult | None = None,
    ) -> TraceRecord:
        """Persist a trace with real LLM call metadata for the management panel."""
        response_kind = answer.response_kind
        profile = {
            "sub_agent": intent.sub_agent,
            "agent_label": intent.agent_label,
            "intent_level_1": intent.intent_level_1,
            "intent_level_2": intent.intent_level_2,
            "subject_type": intent.subject_type,
            "subject_name": intent.subject_name,
            "action_type": intent.action_type,
            "risk_level": intent.risk_level,
            "route_reason": intent.route_reason,
        }
        rag_result = rag or RagRetrievalResult(query=user_query)
        rag_hits = [hit.model_dump() for hit in rag_result.hits]
        system_time = resolve_system_time()
        tool_call = self._tool_call(response_kind)
        total_latency = (
            intent.meta.latency_ms
            + rag_result.latency_ms
            + answer.meta.latency_ms
            + (quality.meta.latency_ms if quality.meta else 0)
        )
        metadata = {
            "total_latency_ms": total_latency,
            "tool_calls_count": 0 if response_kind == "calculator" else 1,
            "quality_check_result": quality.overall_result,
            "model_versions": {
                "master_bot": intent.meta.model,
                "intent_recognition": intent.meta.model,
                "answer_generation": answer.meta.model,
                "quality_check": quality.meta.model if quality.meta else intent.meta.model,
                "rag": rag_result.model or ("semantic" if rag_result.embedding_connected else "mock"),
            },
        }
        quality_payload = {
            "overall_result": quality.overall_result,
            "compliance_scan": quality.compliance_scan,
            "citation_check": quality.citation_check,
            "data_consistency": quality.data_consistency,
            "format_check": quality.format_check,
            "risk_tip_present": quality.risk_tip_present,
            "blacklist_expressions_found": quality.blacklist_expressions_found,
        }
        trace = TraceRecord(
            id=trace_id,
            session_id=session_id,
            message_id=message_id,
            user_query=user_query,
            status="success",
            steps=[
                {
                    "step_id": "step_001",
                    "step_index": 1,
                    "name": "上下文预处理",
                    "node": "preprocessing",
                    "status": "success",
                    "latency_ms": 24,
                    "summary": (
                        f"加载当前会话与本轮 Query；系统基准日 {system_time.current_date}（{system_time.source}）。"
                    ),
                    "detail_sections": [
                        {
                            "title": "预处理结果",
                            "items": [
                                {"label": "输入", "value": "用户 Query 与当前会话"},
                                {"label": "系统日期", "value": system_time.current_date},
                                {"label": "时区", "value": system_time.timezone},
                                {"label": "输出", "value": "进入 LLM 意图识别"},
                            ],
                        }
                    ],
                    "input": {"query": user_query},
                    "output": {"llm_connected": True, "system_context": system_time.to_dict()},
                    "raw_json": {
                        "node": "preprocessing",
                        "query": user_query,
                        "system_context": system_time.to_dict(),
                    },
                    "error": None,
                },
                {
                    "step_id": "step_002",
                    "step_index": 2,
                    "name": "意图识别",
                    "node": "llm_intent_recognition",
                    "status": "success",
                    "latency_ms": intent.meta.latency_ms,
                    "summary": (
                        f"识别为{profile['intent_level_1']} / {profile['intent_level_2']}，"
                        f"抽取主体：{profile['subject_name']}。"
                    ),
                    "detail_sections": [
                        {
                            "title": "意图与槽位",
                            "items": [
                                {"label": "一级意图", "value": profile["intent_level_1"]},
                                {"label": "二级意图", "value": profile["intent_level_2"]},
                                {"label": "主体", "value": profile["subject_name"]},
                                {"label": "模型", "value": intent.meta.model},
                            ],
                        }
                    ],
                    "input": {"query": user_query},
                    "output": {
                        "global_slots": self._global_slots(profile),
                        "routing_output": self._routing_output(profile),
                    },
                    "raw_json": {
                        "node": "llm_intent_recognition",
                        "response_kind": response_kind,
                        "model": intent.meta.model,
                        "usage": intent.meta.raw_json.get("usage", {}),
                        "global_slots": self._global_slots(profile),
                        "routing_output": self._routing_output(profile),
                    },
                    "error": None,
                },
                {
                    "step_id": "step_003",
                    "step_index": 3,
                    "name": "路由决策",
                    "node": "router",
                    "status": "success",
                    "latency_ms": 18,
                    "summary": f"路由到{profile['agent_label']}，进入对应任务处理。",
                    "detail_sections": [
                        {
                            "title": "路由结果",
                            "items": [
                                {"label": "路由目标", "value": profile["agent_label"]},
                                {"label": "理由", "value": profile["route_reason"]},
                                {"label": "编排模式", "value": "LLM 意图路由"},
                            ],
                        }
                    ],
                    "input": {"routing_output": self._routing_output(profile)},
                    "output": {"selected_agent": profile["sub_agent"], "langgraph_connected": False},
                    "raw_json": {
                        "node": "router",
                        "routing_output": self._routing_output(profile),
                        "langgraph_connected": False,
                    },
                    "error": None,
                },
                {
                    "step_id": "step_004",
                    "step_index": 4,
                    "name": "工具调用",
                    "node": "tool_call",
                    "status": "success",
                    "latency_ms": tool_call["latency_ms"],
                    "summary": tool_call["description"],
                    "detail_sections": [
                        {
                            "title": "工具调用结果",
                            "items": [
                                {"label": "工具", "value": tool_call["tool_name"]},
                                {"label": "状态", "value": tool_call["status"]},
                                {"label": "说明", "value": tool_call["description"]},
                            ],
                        }
                    ],
                    "input": {"request": tool_call["request"]},
                    "output": {"response": tool_call["response"]},
                    "raw_json": {"node": "tool_call", "tool_call": tool_call},
                    "error": None,
                },
                self._rag_step(user_query, rag_result, rag_hits),
                {
                    "step_id": "step_006",
                    "step_index": 6,
                    "name": "质检合规",
                    "node": "llm_quality_check",
                    "status": "success",
                    "latency_ms": quality.meta.latency_ms if quality.meta else 0,
                    "summary": (
                        f"检查黑名单表达、引用完整性、时间口径和风险提示，结果 {quality.overall_result}。"
                    ),
                    "detail_sections": [
                        {
                            "title": "质检结果",
                            "items": [
                                {"label": "结果", "value": quality.overall_result},
                                {"label": "引用", "value": quality.citation_check.get("summary", "")},
                                {
                                    "label": "风险提示",
                                    "value": "已添加" if quality.risk_tip_present else "缺失",
                                },
                            ],
                        }
                    ],
                    "input": {"query": user_query, "answer_preview": answer.content[:120]},
                    "output": {"quality_check": quality_payload},
                    "raw_json": {
                        "node": "llm_quality_check",
                        "model": quality.meta.model if quality.meta else answer.meta.model,
                        "quality_check": quality_payload,
                    },
                    "error": None,
                },
                {
                    "step_id": "step_007",
                    "step_index": 7,
                    "name": "回答组装",
                    "node": "llm_response_generation",
                    "status": "success",
                    "latency_ms": answer.meta.latency_ms,
                    "summary": "由 LLM 生成富响应、引用来源和风险提示。",
                    "detail_sections": [
                        {
                            "title": "输出结果",
                            "items": [
                                {"label": "助手", "value": profile["agent_label"]},
                                {"label": "模型", "value": answer.meta.model},
                                {"label": "输出形态", "value": "富响应 + 风险提示 + 来源"},
                            ],
                        }
                    ],
                    "input": {"quality_check_result": quality.overall_result},
                    "output": {"rich_blocks_count": len(answer.rich_blocks), "llm_connected": True},
                    "raw_json": {
                        "node": "llm_response_generation",
                        "model": answer.meta.model,
                        "usage": answer.meta.raw_json.get("usage", {}),
                        "rich_blocks_count": len(answer.rich_blocks),
                    },
                    "error": None,
                },
            ],
            trace_metadata=metadata,
            created_at=_now(),
        )
        return await self.repo.create_trace(trace)

    async def create_langgraph_trace(
        self,
        trace_id: str,
        session_id: str,
        message_id: str,
        user_query: str,
        steps: list[dict[str, Any]],
    ) -> TraceRecord:
        """Persist a LangGraph trace from recorder-produced steps."""
        total_latency = sum(int(step.get("latency_ms", 0)) for step in steps)
        tool_calls_count = sum(
            1
            for step in steps
            if step.get("node") == "tool_call" and step.get("status") == "success"
        )
        quality_result = "PASS"
        for step in reversed(steps):
            if step.get("node") == "quality_check":
                output = step.get("output", {})
                if isinstance(output, dict):
                    payload = output.get("quality_check_payload", output)
                    if isinstance(payload, dict):
                        quality_result = str(
                            payload.get("overall_result", payload.get("quality_status", "PASS"))
                        )
                break
        metadata = {
            "total_latency_ms": total_latency,
            "tool_calls_count": tool_calls_count,
            "quality_check_result": quality_result,
            "model_versions": {"langgraph": "local"},
            "langgraph_connected": True,
        }
        trace = TraceRecord(
            id=trace_id,
            session_id=session_id,
            message_id=message_id,
            user_query=user_query,
            status="success",
            steps=steps,
            trace_metadata=metadata,
            created_at=_now(),
        )
        return await self.repo.create_trace(trace)

    async def get_trace(self, trace_id: str) -> TraceRead:
        """Return a full trace detail DTO."""
        trace = await self.repo.get_trace(trace_id)
        if trace is None:
            raise TraceNotFoundError("Trace 不存在")
        return self._to_trace_read(trace)

    async def get_step_raw(self, trace_id: str, step_id: str) -> RawTraceStepRead:
        """Return one trace step raw JSON payload."""
        trace = await self.repo.get_trace(trace_id)
        if trace is None:
            raise TraceNotFoundError("Trace 不存在")
        for step in trace.steps:
            if step.get("step_id") == step_id:
                return RawTraceStepRead(
                    trace_id=trace.id,
                    step_id=step_id,
                    raw_json=cast(dict[str, Any], step.get("raw_json", {})),
                )
        raise TraceStepNotFoundError("Trace 节点不存在")

    def to_summary(self, trace: TraceRecord) -> TraceSummaryRead:
        """Convert a trace record to the chat response summary."""
        metadata = TraceMetadataRead.model_validate(trace.trace_metadata)
        return TraceSummaryRead(
            id=trace.id,
            status=cast(Any, trace.status),
            metadata=TraceSummaryMetadata(
                total_latency_ms=metadata.total_latency_ms,
                tool_calls_count=metadata.tool_calls_count,
                quality_check_result=metadata.quality_check_result,
                model_versions=metadata.model_versions,
            ),
        )

    def _metadata(self, response_kind: str, query: str) -> dict[str, Any]:
        profile = self._profile(response_kind)
        quality_result = self._quality_check(query, self._rag_hits(response_kind))["overall_result"]
        return {
            "total_latency_ms": 620 if response_kind == "calculator" else 1480,
            "tool_calls_count": 0 if response_kind == "calculator" else 2,
            "quality_check_result": quality_result,
            "model_versions": {
                "master_bot": "local-master",
                profile["sub_agent"]: "local-agent",
                "rag": "mock-rag",
                "quality_check": "rule-based",
            },
        }

    def _steps(self, query: str, response_kind: str) -> list[dict[str, Any]]:
        profile = self._profile(response_kind)
        rag_hits = self._rag_hits(response_kind)
        tool_call = self._tool_call(response_kind)
        quality_check = self._quality_check(query, rag_hits)
        return [
            {
                "step_id": "step_001",
                "step_index": 1,
                "name": "上下文预处理",
                "node": "fallback_preprocessing",
                "status": "success",
                "latency_ms": 38,
                "summary": "加载当前会话与本轮 Query，确认本次输入。",
                "detail_sections": [
                    {
                        "title": "预处理结果",
                        "items": [
                            {"label": "输入", "value": "用户 Query 与当前会话"},
                            {"label": "输出", "value": "进入本地路由"},
                        ],
                    }
                ],
                "input": {"query": query},
                "output": {"fallback_mode": True},
                "raw_json": {"node": "fallback_preprocessing", "query": query, "fallback_mode": True},
                "error": None,
            },
            {
                "step_id": "step_002",
                "step_index": 2,
                "name": "意图识别",
                "node": "fallback_intent_recognition",
                "status": "success",
                "latency_ms": 126,
                "summary": f"识别为{profile['intent_level_1']} / {profile['intent_level_2']}，抽取主体：{profile['subject_name']}。",
                "detail_sections": [
                    {
                        "title": "意图与槽位",
                        "items": [
                            {"label": "一级意图", "value": profile["intent_level_1"]},
                            {"label": "二级意图", "value": profile["intent_level_2"]},
                            {"label": "主体", "value": profile["subject_name"]},
                            {"label": "风险等级", "value": profile["risk_level"]},
                        ],
                    }
                ],
                "input": {"query": query},
                "output": {"global_slots": self._global_slots(profile), "routing_output": self._routing_output(profile)},
                "raw_json": {
                    "node": "fallback_intent_recognition",
                    "response_kind": response_kind,
                    "global_slots": self._global_slots(profile),
                    "routing_output": self._routing_output(profile),
                    "fallback_mode": True,
                },
                "error": None,
            },
            {
                "step_id": "step_003",
                "step_index": 3,
                "name": "路由决策",
                "node": "fallback_router",
                "status": "success",
                "latency_ms": 92,
                "summary": f"路由到{profile['agent_label']}，进入对应任务处理。",
                "detail_sections": [
                    {
                        "title": "路由结果",
                        "items": [
                            {"label": "路由目标", "value": profile["agent_label"]},
                            {"label": "理由", "value": profile["route_reason"]},
                            {"label": "编排模式", "value": "本地任务链路"},
                        ],
                    }
                ],
                "input": {"routing_output": self._routing_output(profile)},
                "output": {"selected_agent": profile["sub_agent"], "langgraph_connected": False},
                "raw_json": {
                    "node": "fallback_router",
                    "routing_output": self._routing_output(profile),
                    "langgraph_connected": False,
                    "blocked_conditions": ["LANGGRAPH_ENV", "完整 LangGraph 流转图"],
                },
                "error": None,
            },
            {
                "step_id": "step_004",
                "step_index": 4,
                "name": "工具调用",
                "node": "fallback_tool_call",
                "status": "success",
                "latency_ms": 310,
                "summary": tool_call["description"],
                "detail_sections": [
                    {
                        "title": "工具调用结果",
                        "items": [
                            {"label": "工具", "value": tool_call["tool_name"]},
                            {"label": "状态", "value": tool_call["status"]},
                            {"label": "说明", "value": tool_call["description"]},
                        ],
                    }
                ],
                "input": {"request": tool_call["request"]},
                "output": {"response": tool_call["response"]},
                "raw_json": {"node": "fallback_tool_call", "tool_call": tool_call},
                "error": None,
            },
            {
                "step_id": "step_005",
                "step_index": 5,
                "name": "RAG 命中",
                "node": "mock_rag_retrieval",
                "status": "success",
                "latency_ms": 284,
                "summary": f"模拟命中 {len(rag_hits)} 条本地 Markdown 依据，Embedding / Rerank 尚未真实接入。",
                "detail_sections": [
                    {
                        "title": "命中文档",
                        "items": [
                            {"label": "文档标题", "value": rag_hits[0]["title"]},
                            {"label": "来源类型", "value": rag_hits[0]["source_type"]},
                            {"label": "相关性说明", "value": rag_hits[0]["relevance_reason"]},
                        ],
                    }
                ],
                "input": {"query": query, "embedding_provider": "siliconflow-qwen"},
                "output": {"rag_hits": rag_hits, "rerank_mode": "static_fallback"},
                "raw_json": {
                    "node": "mock_rag_retrieval",
                    "rag_hits": rag_hits,
                    "embedding_connected": False,
                    "rerank_connected": False,
                },
                "error": None,
            },
            {
                "step_id": "step_006",
                "step_index": 6,
                "name": "质检合规",
                "node": "fallback_quality_check",
                "status": "success",
                "latency_ms": 148,
                "summary": f"检查黑名单表达、引用完整性、时间口径和风险提示，结果 {quality_check['overall_result']}。",
                "detail_sections": [
                    {
                        "title": "质检结果",
                        "items": [
                            {"label": "结果", "value": quality_check["overall_result"]},
                            {"label": "引用", "value": quality_check["citation_check"]["summary"]},
                            {"label": "风险提示", "value": "已添加" if quality_check["risk_tip_present"] else "缺失"},
                        ],
                    }
                ],
                "input": {"query": query, "rag_hits": rag_hits},
                "output": {"quality_check": quality_check},
                "raw_json": {"node": "fallback_quality_check", "quality_check": quality_check},
                "error": None,
            },
            {
                "step_id": "step_007",
                "step_index": 7,
                "name": "回答组装",
                "node": "fallback_response_builder",
                "status": "success",
                "latency_ms": 210,
                "summary": "生成富响应、引用来源和风险提示。",
                "detail_sections": [
                    {
                        "title": "输出结果",
                        "items": [
                            {"label": "助手", "value": profile["agent_label"]},
                            {"label": "输出形态", "value": "富响应 + 风险提示 + 来源"},
                        ],
                    }
                ],
                "input": {"quality_check_result": quality_check["overall_result"]},
                "output": {"fallback_mode": True, "rich_blocks_ready": True},
                "raw_json": {
                    "node": "fallback_response_builder",
                    "fallback_mode": True,
                    "blocked_conditions": [
                        "LLM_API_KEY",
                        "EMBEDDING_API_KEY",
                        "RERANK_API_KEY",
                        "LOCAL_KB_PATH",
                        "LANGGRAPH_ENV",
                    ],
                },
                "error": None,
            },
        ]

    def _profile(self, response_kind: str) -> dict[str, str]:
        profiles = {
            "calculator": {
                "sub_agent": "chit_chat",
                "agent_label": "测算组件",
                "intent_level_1": "参数测算",
                "intent_level_2": "收益率测算",
                "subject_type": "formula",
                "subject_name": "用户输入参数",
                "action_type": "测算",
                "risk_level": "medium",
                "route_reason": "用户请求收益或盈亏测算，使用本地公式即可完成。",
            },
            "stock": {
                "sub_agent": "stock_agent",
                "agent_label": "问股助手",
                "intent_level_1": "个股分析",
                "intent_level_2": "基本面摘要",
                "subject_type": "stock",
                "subject_name": "宁德时代 / 300750",
                "action_type": "基本面分析",
                "risk_level": "medium",
                "route_reason": "用户询问个股经营质量和财务指标，需要问股助手处理。",
            },
            "hotspot": {
                "sub_agent": "hotspot_agent",
                "agent_label": "热点助手",
                "intent_level_1": "热点归因",
                "intent_level_2": "产业催化梳理",
                "subject_type": "sector",
                "subject_name": "机器人板块",
                "action_type": "归因",
                "risk_level": "medium",
                "route_reason": "用户询问热点或政策催化，需要热点助手做信息归因。",
            },
            "data": {
                "sub_agent": "data_agent",
                "agent_label": "问数助手",
                "intent_level_1": "行情查询",
                "intent_level_2": "板块排行",
                "subject_type": "sector",
                "subject_name": "半导体板块",
                "action_type": "排名",
                "risk_level": "low",
                "route_reason": "用户请求客观行情排名，不需要主观投资判断。",
            },
        }
        return profiles.get(response_kind, profiles["data"])

    def _global_slots(self, profile: dict[str, str]) -> dict[str, Any]:
        return {
            "intent_type": profile["intent_level_1"],
            "subject_type": profile["subject_type"],
            "subject_name": profile["subject_name"],
            "time_range": "今天",
            "action_type": profile["action_type"],
            "risk_level": profile["risk_level"],
            "is_compound": False,
            "missing_slots": [],
        }

    def _routing_output(self, profile: dict[str, str]) -> dict[str, Any]:
        return {
            "is_multi_intent": False,
            "sub_agent": profile["sub_agent"],
            "intent_level_1": profile["intent_level_1"],
            "intent_level_2": profile["intent_level_2"],
            "reason": profile["route_reason"],
        }

    def _rag_step(
        self,
        user_query: str,
        rag_result: RagRetrievalResult,
        rag_hits: list[dict[str, Any]],
    ) -> dict[str, Any]:
        rerank_label = "已启用" if rag_result.rerank_connected else "未启用"
        if rag_result.rerank_before and not rag_result.rerank_connected:
            rerank_label = "调用失败，已降级 hybrid"
        if rag_hits:
            top_hit = rag_hits[0]
            if rag_result.rerank_connected:
                summary = (
                    f"混合检索命中 {len(rag_hits)} 条本地知识库片段，"
                    f"经 Rerank 重排后最高相关文档：{top_hit.get('title', '未知文档')}。"
                )
            elif rag_result.rerank_before:
                summary = (
                    f"混合检索命中 {len(rag_hits)} 条本地知识库片段，"
                    f"Rerank 失败后降级 hybrid，最高相关文档：{top_hit.get('title', '未知文档')}。"
                )
            else:
                summary = (
                    f"语义检索命中 {len(rag_hits)} 条本地知识库片段，"
                    f"最高相关文档：{top_hit.get('title', '未知文档')}。"
                )
            detail_items = [
                {"label": "模式", "value": rag_result.mode},
                {"label": "Rerank", "value": rerank_label},
                {"label": "命中数", "value": str(len(rag_hits))},
                {"label": "文档标题", "value": str(top_hit.get("title", ""))},
                {"label": "来源类型", "value": str(top_hit.get("source_type", ""))},
                {"label": "相关性", "value": str(top_hit.get("relevance_reason", ""))},
                {"label": "相似度", "value": str(top_hit.get("score", ""))},
            ]
        else:
            summary = "本轮未命中本地知识库片段，回答由模型直接生成。"
            detail_items = [
                {"label": "模式", "value": rag_result.mode},
                {"label": "Rerank", "value": rerank_label},
                {"label": "命中数", "value": "0"},
                {"label": "Embedding", "value": "已连接" if rag_result.embedding_connected else "未连接"},
            ]
        detail_sections: list[dict[str, Any]] = [{"title": "检索状态", "items": detail_items}]
        if rag_result.rerank_before:
            detail_sections.append(
                {
                    "title": "重排前候选",
                    "items": [
                        {
                            "label": f"#{index}",
                            "value": (
                                f"{item.title}（chunk_id={item.chunk_id}，hybrid_score={item.score}）"
                            ),
                        }
                        for index, item in enumerate(rag_result.rerank_before, start=1)
                    ],
                }
            )
        if rag_result.rerank_after:
            detail_sections.append(
                {
                    "title": "重排后结果",
                    "items": [
                        {
                            "label": f"#{index}",
                            "value": (
                                f"{item.title}（chunk_id={item.chunk_id}，rerank_score={item.score}）"
                            ),
                        }
                        for index, item in enumerate(rag_result.rerank_after, start=1)
                    ],
                }
            )
        return {
            "step_id": "step_005",
            "step_index": 5,
            "name": "RAG 命中",
            "node": "rag_retrieval",
            "status": "success",
            "latency_ms": rag_result.latency_ms,
            "summary": summary,
            "detail_sections": detail_sections,
            "input": {"query": user_query},
            "output": {"rag_hits": rag_hits},
            "raw_json": rag_result.to_trace_payload(),
            "error": None,
        }

    def _tool_call(self, response_kind: str) -> dict[str, Any]:
        if response_kind == "calculator":
            return {
                "id": "tool_local_calculator",
                "tool_name": "local_return_calculator",
                "description": "使用本地公式完成收益率测算，未调用外部服务。",
                "request": {"fields": ["buy_price", "target_price", "share_count", "fee_rate"]},
                "response": {"status": "computed", "external_service": False},
                "status": "success",
                "latency_ms": 42,
            }
        tool_names = {
            "stock": "mock_financial_profile_lookup",
            "hotspot": "hotspot_signal_lookup",
            "data": "market_ranking_lookup",
        }
        return {
            "id": f"tool_{response_kind}_fallback",
            "tool_name": tool_names.get(response_kind, "market_ranking_lookup"),
            "description": (
                "问数走东财 push2；热点走同花顺信号+东财快讯/巨潮公告（失败时降级知识库素材），"
                "基于 third_party/a-stock-data 适配。"
            ),
            "request": {"mode": "fallback", "response_kind": response_kind},
            "response": {"rows": 3, "source": "backend embedded fallback samples"},
            "status": "success",
            "latency_ms": 310,
        }

    def _rag_hits(self, response_kind: str) -> list[dict[str, Any]]:
        hits = {
            "stock": {
                "doc_id": "rag_stock_300750_001",
                "title": "宁德时代 2025 年报与机构观点摘要",
                "source_type": "financial",
                "path": "data/knowledge-base/stocks/300750-summary.md",
                "score": 0.86,
                "snippet": "营收、利润与 ROE 仍处行业前列，但价格竞争和海外政策需持续关注。",
                "relevance_reason": "命中公司名称、财务指标和基本面分析意图。",
            },
            "hotspot": {
                "doc_id": "rag_hotspot_robotics_001",
                "title": "机器人产业链政策与订单催化摘要",
                "source_type": "report",
                "path": "data/knowledge-base/hotspots/robotics-policy.md",
                "score": 0.82,
                "snippet": "产业政策、订单预期和国产替代是近期关注度提升的主要线索。",
                "relevance_reason": "命中热点主题、政策催化和产业链归因意图。",
            },
            "calculator": {
                "doc_id": "rag_calculator_risk_001",
                "title": "收益测算组件风险提示模板",
                "source_type": "qa",
                "path": "data/knowledge-base/compliance/calculator-risk.md",
                "score": 0.78,
                "snippet": "参数测算只展示公式结果，不构成投资建议。",
                "relevance_reason": "命中测算场景和风险提示要求。",
            },
            "data": {
                "doc_id": "rag_market_semiconductor_001",
                "title": "半导体板块行情口径说明",
                "source_type": "market",
                "path": "data/knowledge-base/market/semiconductor-ranking.md",
                "score": 0.84,
                "snippet": "排行数据按本地模拟行情截面生成，包含涨跌幅、现价和成交额。",
                "relevance_reason": "命中半导体板块、涨幅排行和行情查询意图。",
            },
        }
        return [
            hits.get(response_kind, hits["data"]),
            {
                "doc_id": "rag_compliance_notice_001",
                "title": "投研回答合规与引用检查规则",
                "source_type": "knowledge",
                "path": "data/knowledge-base/compliance/answer-checklist.md",
                "score": 0.76,
                "snippet": "回答必须包含来源、时间口径和不构成投资建议提示。",
                "relevance_reason": "用于验证引用完整性、风险提示和格式合规。",
            },
        ]

    def _quality_check(self, query: str, rag_hits: list[dict[str, Any]]) -> dict[str, Any]:
        blacklist = [word for word in ("建议买入", "推荐", "值得关注", "重点关注", "逢低关注") if word in query]
        overall_result = "FAIL" if blacklist else "PASS"
        return {
            "overall_result": overall_result,
            "compliance_scan": {
                "summary": "未命中黑名单表达" if not blacklist else "命中黑名单表达，已降级为风险提示",
                "blacklist_expressions_found": blacklist,
            },
            "citation_check": {
                "summary": f"引用完整，包含 {len(rag_hits)} 条模拟 RAG 命中",
                "citation_count": len(rag_hits),
            },
            "data_consistency": {"summary": "数据时间口径已标注为本地模拟数据"},
            "format_check": {"summary": "富响应、引用来源和风险提示均已生成"},
            "risk_tip_present": True,
            "blacklist_expressions_found": blacklist,
        }

    def _to_trace_read(self, trace: TraceRecord) -> TraceRead:
        return TraceRead(
            id=trace.id,
            session_id=trace.session_id,
            message_id=trace.message_id,
            user_query=trace.user_query,
            status=cast(Any, trace.status),
            steps=[TraceStepRead.model_validate(step) for step in trace.steps],
            metadata=TraceMetadataRead.model_validate(trace.trace_metadata),
        )
