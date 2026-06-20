"""Services for data source and configuration status pages."""

import json
from pathlib import Path

from ..integrations.llm.service import LLMService
from ..models.config_status import (
    ComplianceRulesRead,
    ConfigStatusRead,
    DataSourceStatusRead,
    DataSourceStatusValue,
    MockDataSourceRead,
    ModelConfigStatusRead,
    OrchestrationStatusRead,
    PromptStatusRead,
    RagStatusRead,
)
from ..settings import BACKEND_ROOT, get_settings
from .rag.chunker import count_markdown_files, resolve_kb_root
from .rag.service import RagService

MARKET_DATA_API_PATH = "integrations/market_data/eastmoney_client.py (东财 push2)"

PROMPTS = [
    ("master_agent", "总控 Agent"),
    ("hotspot_agent", "热点助手"),
    ("data_agent", "问数助手"),
    ("stock_agent", "问股助手"),
    ("quality_check", "质检模块"),
]

BLACKLIST_EXPRESSIONS = ["建议买入", "推荐", "值得关注", "重点关注", "逢低关注"]


class ConfigStatusService:
    """Read-only status service. Never returns secret values."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_data_sources_status(self) -> DataSourceStatusRead:
        """Return local knowledge-base, tool data sources and RAG status."""
        kb_root = resolve_kb_root(self.settings.local_kb_path, BACKEND_ROOT)
        rag_service = RagService(self.settings)
        financials_dir = kb_root / "financials"
        company_reports_dir = kb_root / "company-reports"
        industry_reports_dir = kb_root / "industry-reports"

        market_count = 0
        financial_count = self._count_md_files(financials_dir)
        report_count = self._count_md_files(company_reports_dir) + self._count_md_files(industry_reports_dir)
        knowledge_count = count_markdown_files(kb_root)

        sources = [
            MockDataSourceRead(
                type="market",
                name="行情数据",
                path=MARKET_DATA_API_PATH,
                status="ready",
                sample_count=market_count,
            ),
            MockDataSourceRead(
                type="financial",
                name="财务数据",
                path=self._kb_display_path("financials"),
                status=self._status_from_count(financial_count),
                sample_count=financial_count,
            ),
            MockDataSourceRead(
                type="financial_live",
                name="新浪财经财报 API",
                path="integrations/market_data/sina_finance_client.py",
                status="ready",
                sample_count=0,
            ),
            MockDataSourceRead(
                type="report",
                name="研报数据",
                path=f"{self._kb_display_path('company-reports')} + industry-reports",
                status=self._status_from_count(report_count),
                sample_count=report_count,
            ),
            MockDataSourceRead(
                type="report_live",
                name="东财研报 reportapi",
                path="integrations/market_data/em_research_report_client.py",
                status="ready",
                sample_count=0,
            ),
            MockDataSourceRead(
                type="consensus_live",
                name="同花顺一致预期",
                path="integrations/market_data/ths_worth_client.py",
                status="ready",
                sample_count=0,
            ),
            MockDataSourceRead(
                type="announcement",
                name="公告与资讯",
                path="integrations/market_data (巨潮公告 + 东财快讯)",
                status="ready",
                sample_count=0,
            ),
            MockDataSourceRead(
                type="announcement_live",
                name="巨潮公告 + 东财快讯",
                path="integrations/market_data/cninfo_client.py + news_client.py",
                status="ready",
                sample_count=0,
            ),
            MockDataSourceRead(
                type="knowledge",
                name="投研知识库",
                path=self._kb_display_path(),
                status=self._status_from_count(knowledge_count),
                sample_count=knowledge_count,
            ),
        ]

        rag_ready = rag_service.is_ready()
        index_meta = self._read_index_meta(kb_root)
        return DataSourceStatusRead(
            mock_data=sources,
            rag=RagStatusRead(
                mode="semantic" if rag_ready else "mock",
                embedding_provider=self._format_siliconflow_provider(
                    self.settings.embedding_model,
                    "Embedding 未配置",
                ),
                rerank_provider=self._format_siliconflow_provider(
                    self.settings.rerank_model,
                    "Rerank 未配置",
                ),
                status="ready" if rag_ready else "mocked",
                chunk_count=(
                    int(raw)
                    if isinstance(raw := index_meta.get("chunk_count", 0), (int, float, str))
                    else 0
                ),
                indexed_files=knowledge_count,
            ),
        )

    def get_config_status(self) -> ConfigStatusRead:
        """Return model, prompt, and compliance status without secret values."""
        return ConfigStatusRead(
            orchestration=self._langgraph_status(),
            models=[
                self._model_status(
                    "硅基流动 LLM / 意图识别",
                    {
                        "LLM_INTENT_API_KEY": self.settings.llm_intent_api_key,
                        "LLM_INTENT_BASE_URL": self.settings.llm_intent_base_url,
                        "LLM_INTENT_MODEL": self.settings.llm_intent_model,
                    },
                ),
                self._model_status(
                    "硅基流动 LLM / 主输出",
                    {
                        "LLM_API_KEY": self.settings.llm_api_key,
                        "LLM_BASE_URL": self.settings.llm_base_url,
                        "LLM_MODEL": self.settings.llm_model,
                    },
                ),
                self._model_status(
                    "硅基流动 Embedding",
                    {
                        "EMBEDDING_API_KEY": self.settings.embedding_api_key,
                        "EMBEDDING_BASE_URL": self.settings.embedding_base_url,
                        "EMBEDDING_MODEL": self.settings.embedding_model,
                        "EMBEDDING_DIM": self.settings.embedding_dim,
                    },
                ),
                self._model_status(
                    "硅基流动 Rerank",
                    {
                        "RERANK_API_KEY": self.settings.rerank_api_key,
                        "RERANK_BASE_URL": self.settings.rerank_base_url,
                        "RERANK_MODEL": self.settings.rerank_model,
                    },
                ),
            ],
            prompts=[PromptStatusRead(agent=agent, name=name, status="default") for agent, name in PROMPTS],  # type: ignore[arg-type]
            compliance_rules=ComplianceRulesRead(
                blacklist_expressions=BLACKLIST_EXPRESSIONS,
                risk_tip_required=True,
                citation_required=True,
            ),
        )

    def _langgraph_status(self) -> OrchestrationStatusRead:
        missing: list[str] = []
        if self.settings.langgraph_env.strip() != "local":
            missing.append("LANGGRAPH_ENV 须为 local")
        if not LLMService(self.settings).is_configured():
            missing.append("LLM 主输出/意图识别未配置")
        return OrchestrationStatusRead(
            name="langgraph",
            env=self.settings.langgraph_env.strip(),
            status="ready" if not missing else "blocked",
            missing_requirements=missing,
        )

    def _model_status(self, name: str, fields: dict[str, str]) -> ModelConfigStatusRead:
        missing_fields = [field_name for field_name, value in fields.items() if not value.strip()]
        return ModelConfigStatusRead(
            name=name,
            fields=list(fields.keys()),
            status="ready" if not missing_fields else "mocked",
            missing_fields=missing_fields,
        )

    def _kb_display_path(self, relative: str = "") -> str:
        kb = (self.settings.local_kb_path.strip() or "data/knowledge-base").strip("/")
        rel = relative.strip("/")
        return f"backend/{kb}/{rel}" if rel else f"backend/{kb}"

    def _status_from_count(self, sample_count: int) -> DataSourceStatusValue:
        return "ready" if sample_count > 0 else "missing"

    def _format_siliconflow_provider(self, model: str, fallback: str) -> str:
        model = model.strip()
        if not model:
            return fallback
        return f"siliconflow · {model}"

    def _read_index_meta(self, kb_root: Path) -> dict[str, object]:
        meta_path = kb_root / ".index" / "index_meta.json"
        if not meta_path.is_file():
            return {}
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _count_md_files(self, folder: Path) -> int:
        if not folder.is_dir():
            return 0
        return sum(
            1
            for path in folder.rglob("*.md")
            if path.is_file() and path.name.lower() != "readme.md"
        )
