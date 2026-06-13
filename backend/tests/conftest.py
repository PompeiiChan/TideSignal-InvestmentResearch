"""Shared pytest fixtures."""

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest import MonkeyPatch

from backend.src.integrations.llm.models import (
    AnswerResult,
    IntentResult,
    LLMCallMeta,
    QualityCheckResult,
)
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.models import RagHit, RagRetrievalResult
from backend.src.services.rag.service import RagService


def _meta(model: str = "deepseek-chat") -> LLMCallMeta:
    return LLMCallMeta(
        model=model,
        latency_ms=120,
        prompt_tokens=80,
        completion_tokens=160,
        total_tokens=240,
        finish_reason="stop",
        raw_json={"provider": "siliconflow", "usage": {"total_tokens": 240}},
    )


def _quality() -> QualityCheckResult:
    return QualityCheckResult(
        overall_result="PASS",
        compliance_scan={"summary": "未命中黑名单表达", "blacklist_expressions_found": []},
        citation_check={"summary": "引用完整", "citation_count": 1},
        data_consistency={"summary": "时间口径已标注"},
        format_check={"summary": "富响应结构完整"},
        risk_tip_present=True,
        blacklist_expressions_found=[],
        meta=_meta(),
    )


def _risk_notice() -> str:
    return "以上内容仅为信息整理，不构成投资建议。"


_DEMO_STOCKS: dict[str, tuple[str, str]] = {
    "泸州老窖": ("000568.SZ", "泸州老窖"),
    "宁德时代": ("300750.SZ", "宁德时代"),
    "寒武纪": ("688256.SH", "寒武纪"),
    "海天味业": ("603288.SH", "海天味业"),
}


def _stock_subject_from_query(query: str) -> tuple[str, str] | None:
    for name, (code, _) in _DEMO_STOCKS.items():
        if name in query:
            return name, code
    if "白酒" in query:
        return "泸州老窖", "000568.SZ"
    return None


def _case_for_query(query: str) -> tuple[IntentResult, AnswerResult]:
    if any(keyword in query for keyword in ("回报", "收益", "测算", "买入")):
        intent = IntentResult(
            response_kind="calculator",
            intent_level_1="参数测算",
            intent_level_2="收益率测算",
            subject_type="formula",
            subject_name="用户输入参数",
            action_type="测算",
            risk_level="medium",
            route_reason="用户请求收益测算。",
            sub_agent="chit_chat",
            agent_label="测算组件",
            meta=_meta(),
        )
        answer = AnswerResult(
            content=(
                "已生成可交互测算组件，你可以调整买入价、情景价和持仓数量。\n\n"
                "### 参考来源\n\n"
                "- 用户输入参数（本轮会话）\n\n"
                "测算结果仅基于用户输入参数和本地公式实时计算，不构成投资建议。"
            ),
            response_kind="calculator",
            rich_blocks=[
                {
                    "type": "calculator",
                    "title": "收益率测算组件",
                    "payload": {
                        "fields": [
                            {"key": "buy_price", "label": "买入价", "value": 15, "unit": "元"},
                            {"key": "target_price", "label": "情景价", "value": 20, "unit": "元"},
                        ],
                        "results": [{"key": "return_rate", "label": "收益率", "value": "33.27%"}],
                    },
                    "sources": [],
                    "risk_notice": "测算结果仅基于用户输入参数和本地公式实时计算，不构成投资建议。",
                },
            ],
            meta=_meta(),
        )
        return intent, answer

    stock_subject = _stock_subject_from_query(query)
    if stock_subject is not None:
        stock_name, stock_code = stock_subject
        analysis = (
            f"从公开信息整理看，{stock_name}的核心经营与财务指标需要结合最新披露口径理解。"
            "收入与利润趋势、毛利率与 ROE 变化、经营现金流质量，以及当前估值与行业位置，"
            "共同决定基本面是改善、稳定还是承压。"
        )
        intent = IntentResult(
            response_kind="stock",
            intent_level_1="个股分析",
            intent_level_2="基本面摘要",
            subject_type="stock",
            subject_name=f"{stock_name} / {stock_code}",
            action_type="基本面分析",
            risk_level="medium",
            route_reason="用户询问个股基本面。",
            sub_agent="stock_agent",
            agent_label="问股助手",
            meta=_meta(),
        )
        answer = AnswerResult(
            content=(
                f"以下是对{stock_name}基本面的信息整理。\n\n"
                f"### 核心判断\n\n"
                f"- **经营与财务**：{analysis}\n\n"
                f"### 参考来源\n\n"
                f"- 模型整理（2025年报）\n\n"
                f"以上为个股基本面信息整理，不构成投资建议。"
            ),
            response_kind="stock",
            rich_blocks=[],
            meta=_meta(),
        )
        return intent, answer

    if any(keyword in query for keyword in ("热点", "政策", "催化", "机器人")):
        intent = IntentResult(
            response_kind="hotspot",
            intent_level_1="热点归因",
            intent_level_2="产业催化梳理",
            subject_type="sector",
            subject_name="机器人板块",
            action_type="归因",
            risk_level="medium",
            route_reason="用户询问热点催化。",
            sub_agent="hotspot_agent",
            agent_label="热点助手",
            meta=_meta(),
        )
        answer = AnswerResult(
            content=(
                "下面整理热点归因摘要。\n\n"
                "### 催化因素\n\n"
                "- **政策与订单**：机器人板块热度来自政策与订单预期。\n\n"
                "### 参考来源\n\n"
                "- 模型整理（本轮会话）\n\n"
                f"{_risk_notice()}"
            ),
            response_kind="hotspot",
            rich_blocks=[],
            meta=_meta(),
        )
        return intent, answer

    intent = IntentResult(
        response_kind="data",
        intent_level_1="行情查询",
        intent_level_2="板块排行",
        subject_type="sector",
        subject_name="半导体板块",
        action_type="排名",
        risk_level="low",
        route_reason="用户请求行情排名。",
        sub_agent="data_agent",
        agent_label="问数助手",
        meta=_meta(),
    )
    answer = AnswerResult(
        content=(
            "下面是相关行情数据整理。\n\n"
            "### 参考来源\n\n"
            "- 模型整理（本轮会话）\n\n"
            f"{_risk_notice()}"
        ),
        response_kind="data",
        rich_blocks=[
            {
                "type": "ranking_table",
                "title": "半导体板块涨幅排行",
                "payload": {
                    "columns": ["排名", "股票名称", "代码", "涨跌幅", "现价", "成交额"],
                    "rows": [
                        {
                            "rank": 1,
                            "name": "寒武纪",
                            "code": "688256",
                            "change_pct": "+8.76%",
                            "price": "287.50",
                            "turnover": "42.1亿",
                        }
                    ],
                },
                "sources": [{"type": "market", "label": "模型整理", "time": "本轮会话"}],
                "risk_notice": _risk_notice(),
            },
        ],
        meta=_meta(),
    )
    return intent, answer


def _quality_payload() -> dict[str, Any]:
    return {
        "overall_result": "PASS",
        "compliance_scan": {"summary": "通过"},
        "citation_check": {"summary": "通过"},
        "data_consistency": {"summary": "一致"},
        "format_check": {"summary": "完整"},
        "risk_tip_present": True,
        "blacklist_expressions_found": [],
    }


def _extract_query_from_messages(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        content = str(message.get("content", ""))
        if content.startswith("用户问题："):
            first_line = content.split("\n", 1)[0]
            query = first_line.removeprefix("用户问题：").strip()
            if query:
                return query
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            if content and len(content) < 240:
                return content
            continue
        if isinstance(payload, dict):
            for key in ("normalized_query", "query", "user_query"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return ""


def _langgraph_responses_for_query(query: str) -> list[dict[str, Any]]:
    if any(keyword in query for keyword in ("回报", "收益", "测算", "买入")):
        return [
            {
                "intent_id": "data_query",
                "intent_confidence": 0.92,
                "candidate_intents": [{"intent_id": "data_query", "confidence": 0.92}],
                "missing_slots": [],
            },
            {
                "slots": {
                    "buy_price": 15,
                    "sell_price": 20,
                    "share_count": 1000,
                    "fee_rate": 0.0003,
                    "metric": "收益率测算",
                },
                "slot_confidence": {},
                "ambiguous_slots": [],
            },
            {
                "agent_result": "收益率测算",
                "tool_params": {
                    "buy_price": 15,
                    "sell_price": 20,
                    "share_count": 1000,
                    "fee_rate": 0.0003,
                },
            },
            _quality_payload(),
        ]

    stock_subject = _stock_subject_from_query(query)
    if stock_subject is not None:
        stock_name, stock_code = stock_subject
        return [
            {
                "intent_id": "stock_analysis",
                "intent_confidence": 0.9,
                "candidate_intents": [{"intent_id": "stock_analysis", "confidence": 0.9}],
                "missing_slots": [],
            },
            {
                "slots": {"stock_name": stock_name, "stock_code": stock_code},
                "slot_confidence": {},
                "ambiguous_slots": [],
            },
            {
                "agent_result": f"{stock_name}基本面分析",
                "tool_params": {"stock_name": stock_name, "stock_code": stock_code},
            },
            _quality_payload(),
        ]

    if any(keyword in query for keyword in ("热点", "政策", "催化", "机器人")):
        return [
            {
                "intent_id": "hotspot_analysis",
                "intent_confidence": 0.88,
                "candidate_intents": [{"intent_id": "hotspot_analysis", "confidence": 0.88}],
                "missing_slots": [],
            },
            {
                "slots": {"topic": "机器人", "industry": "机器人"},
                "slot_confidence": {},
                "ambiguous_slots": [],
            },
            {
                "agent_result": "机器人板块受政策与订单催化。",
                "tool_params": {"topic": "机器人"},
            },
            _quality_payload(),
        ]

    return [
        {
            "intent_id": "data_query",
            "intent_confidence": 0.9,
            "candidate_intents": [{"intent_id": "data_query", "confidence": 0.9}],
            "missing_slots": [],
        },
        {
            "slots": {"metric": "涨幅排行", "industry": "半导体"},
            "slot_confidence": {},
            "ambiguous_slots": [],
        },
        {
            "agent_result": "查询半导体板块涨幅排行。",
            "tool_params": {"industry": "半导体", "metric": "涨幅排行"},
        },
        _quality_payload(),
    ]


@pytest.fixture(autouse=True)
def enable_langgraph_local(monkeypatch: MonkeyPatch) -> None:
    """Enable LangGraph for chat-related tests."""
    monkeypatch.setattr(
        "backend.src.services.chat_service.is_langgraph_enabled",
        lambda settings=None: True,
    )
    monkeypatch.setattr(
        "backend.src.integrations.langgraph.runner.is_langgraph_enabled",
        lambda settings=None: True,
    )


@pytest.fixture
def mock_llm_service() -> LLMService:
    """Return an LLM service with query-aware mocked responses."""
    service = LLMService()

    async def recognize_intent(query: str) -> IntentResult:
        intent, _ = _case_for_query(query)
        return intent

    async def generate_answer(query: str, intent: IntentResult) -> AnswerResult:
        _, answer = _case_for_query(query)
        return answer

    async def quality_check(
        query: str,
        answer: AnswerResult,
        *,
        rag_hits: list | None = None,
    ) -> QualityCheckResult:
        return _quality()

    async def generate_answer_stream(
        query: str,
        intent: IntentResult,
        rag_context: str = "",
    ) -> AsyncIterator[str]:
        _, answer = _case_for_query(query)
        body = answer.content
        chunk_size = 12
        for index in range(0, len(body), chunk_size):
            yield body[index : index + chunk_size]

    def build_answer_from_stream(
        query: str,
        intent: IntentResult,
        content: str,
        rag_hits: list[RagHit] | None = None,
    ) -> AnswerResult:
        _, answer = _case_for_query(query)
        normalized = content.strip() or answer.content
        return AnswerResult(
            content=normalized,
            response_kind=answer.response_kind,
            rich_blocks=answer.rich_blocks,
            meta=answer.meta,
        )

    class MockIntentClient:
        def __init__(self, owner: LLMService) -> None:
            self._owner = owner

        async def chat_completion(self, messages: list[dict[str, Any]], **_kwargs: Any) -> dict[str, Any]:
            query = _extract_query_from_messages(messages)
            responses = _langgraph_responses_for_query(query)
            index = self._owner._intent_call_count  # type: ignore[attr-defined]
            self._owner._intent_call_count = index + 1  # type: ignore[attr-defined]
            payload = responses[min(index, len(responses) - 1)]
            return {
                "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
                "usage": {},
            }

        @staticmethod
        def extract_message_content(body: dict[str, Any]) -> str:
            return str(body["choices"][0]["message"]["content"])

    class MockOutputClient:
        async def chat_completion_stream(
            self,
            messages: list[dict[str, Any]],
            **_kwargs: Any,
        ) -> AsyncIterator[str]:
            query = _extract_query_from_messages(messages)
            _, answer = _case_for_query(query)
            body = answer.content
            chunk_size = 12
            for index in range(0, len(body), chunk_size):
                yield body[index : index + chunk_size]

    service._intent_call_count = 0  # type: ignore[attr-defined]
    service.is_configured = lambda: True  # type: ignore[method-assign]
    service._intent_client = lambda: MockIntentClient(service)  # type: ignore[method-assign, assignment, return-value]
    service._output_client = lambda: MockOutputClient()  # type: ignore[method-assign, assignment, return-value]
    service.recognize_intent = AsyncMock(side_effect=recognize_intent)  # type: ignore[method-assign]
    service.generate_answer = AsyncMock(side_effect=generate_answer)  # type: ignore[method-assign]
    service.generate_answer_stream = generate_answer_stream  # type: ignore[method-assign]
    service.build_answer_from_stream = build_answer_from_stream  # type: ignore[method-assign]
    service.quality_check = AsyncMock(side_effect=quality_check)  # type: ignore[method-assign]
    return service


def _rag_hits_for_query(query: str) -> list[RagHit]:
    if any(keyword in query for keyword in ("热点", "政策", "催化", "机器人")):
        return [
            RagHit(
                doc_id="event_ashare_202606",
                title="2026 年 6 月 A股阶段性热点",
                source_type="market",
                path="hotspots/2026-06-market-hotspots.md",
                score=0.84,
                snippet="科技主线从高潮进入震荡验证期，资金围绕低位、红利、防御做快速轮动。",
                relevance_reason="命中市场热点文档",
                chunk_id="event_ashare_202606_001_000",
            )
        ]
    if any(keyword in query for keyword in ("宁德", "基本面", "个股", "财报")):
        return [
            RagHit(
                doc_id="300750-ningdeshidai-financial-2025A-2026Q1",
                title="宁德时代 2025 年报与 2026 一季报财务摘要",
                source_type="financial",
                path="financials/300750-ningdeshidai-financial-2025A-2026Q1.md",
                score=0.88,
                snippet="营业收入与净利润规模仍处行业前列，经营性现金流保持为正。",
                relevance_reason="命中样本公司财报文档",
                chunk_id="300750_fin_001",
            )
        ]
    if any(keyword in query for keyword in ("白酒", "行业", "研报")):
        return [
            RagHit(
                doc_id="baijiu-industry-report-2026",
                title="白酒行业 2026 年行业研报摘要",
                source_type="report",
                path="industry-reports/baijiu-industry-report-2026.md",
                score=0.81,
                snippet="高端白酒批价与渠道库存仍是行业关注核心。",
                relevance_reason="命中行业研报文档",
                chunk_id="baijiu_report_001",
            )
        ]
    if any(keyword in query for keyword in ("海天", "公司研报", "味业")):
        return [
            RagHit(
                doc_id="603288-haitianweiye-company-report-2026",
                title="海天味业 2026 年公司研报摘要",
                source_type="report",
                path="company-reports/603288-haitianweiye-company-report-2026.md",
                score=0.79,
                snippet="调味品龙头渠道与成本控制能力仍是核心观察点。",
                relevance_reason="命中公司研报文档",
                chunk_id="haitian_report_001",
            )
        ]
    return []


@pytest.fixture
def mock_rag_service() -> RagService:
    service = RagService()

    async def retrieve(query: str, top_k: int = 5) -> RagRetrievalResult:
        hits = _rag_hits_for_query(query)[:top_k]
        return RagRetrievalResult(
            hits=hits,
            latency_ms=48,
            embedding_connected=bool(hits),
            index_chunk_count=120,
            query=query,
            model="mock-embedding",
            mode="semantic" if hits else "mock",
        )

    service.retrieve = retrieve  # type: ignore[method-assign]
    service.is_ready = lambda: True  # type: ignore[method-assign]
    service.has_index = lambda: True  # type: ignore[method-assign]
    service.markdown_file_count = lambda: 36  # type: ignore[method-assign]
    return service


@pytest.fixture(autouse=True)
def patch_chat_llm_service(
    mock_llm_service: LLMService,
    mock_rag_service: RagService,
    monkeypatch: MonkeyPatch,
) -> None:
    """Ensure chat query tests do not require real upstream LLM credentials."""
    monkeypatch.setattr(
        "backend.src.services.chat_service.LLMService",
        lambda *args, **kwargs: mock_llm_service,
    )
    monkeypatch.setattr(
        "backend.src.services.chat_service.RagService",
        lambda *args, **kwargs: mock_rag_service,
    )
