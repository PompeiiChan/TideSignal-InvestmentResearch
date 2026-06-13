"""Services for data source and configuration status pages."""

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
from .rag.chunker import resolve_kb_root
from .rag.service import RagService

FALLBACK_SAMPLE_COUNTS = {
    "market": 20,
    "financial": 12,
    "report": 8,
    "announcement": 10,
    "knowledge": 30,
}

DATA_SOURCES = [
    ("market", "行情数据", "market"),
    ("financial", "财务数据", "financial"),
    ("report", "研报数据", "reports"),
    ("announcement", "公告数据", "announcements"),
    ("knowledge", "投研知识库", "knowledge-base"),
]

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
        """Return local mock data, knowledge-base and RAG status."""
        base_path = self._resolve_backend_path(self.settings.mock_data_path)
        kb_root = resolve_kb_root(self.settings.local_kb_path, BACKEND_ROOT)
        kb_display = self.settings.local_kb_path.strip() or "data/knowledge-base"
        rag_service = RagService(self.settings)
        sources: list[MockDataSourceRead] = []
        for source_type, name, folder_name in DATA_SOURCES:
            if source_type == "knowledge":
                configured_path = kb_display.strip("/")
                source_path = kb_root
                sample_count = rag_service.markdown_file_count()
                status: DataSourceStatusValue = "ready" if sample_count > 0 else "missing"
            else:
                configured_path = self._display_path(self.settings.mock_data_path, folder_name)
                source_path = base_path / folder_name
                sample_count = self._sample_count(source_path, source_type)
                status = "ready" if source_path.exists() else "mocked"
            sources.append(
                MockDataSourceRead(
                    type=source_type,  # type: ignore[arg-type]
                    name=name,
                    path=configured_path,
                    status=status,
                    sample_count=sample_count,
                )
            )

        rag_ready = rag_service.is_ready()
        return DataSourceStatusRead(
            mock_data=sources,
            rag=RagStatusRead(
                mode="semantic" if rag_ready else "mock",
                embedding_provider="siliconflow-qwen",
                rerank_provider="siliconflow-qwen",
                status="ready" if rag_ready else "mocked",
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
                    "硅基流动 Embedding / 千问",
                    {
                        "EMBEDDING_API_KEY": self.settings.embedding_api_key,
                        "EMBEDDING_BASE_URL": self.settings.embedding_base_url,
                        "EMBEDDING_MODEL": self.settings.embedding_model,
                        "EMBEDDING_DIM": self.settings.embedding_dim,
                    },
                ),
                self._model_status(
                    "硅基流动 Rerank / 千问",
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

    def _resolve_backend_path(self, configured_path: str) -> Path:
        path = Path(configured_path)
        return path if path.is_absolute() else BACKEND_ROOT / path

    def _display_path(self, base_path: str, folder_name: str) -> str:
        normalized = base_path.strip().strip("/")
        return f"{normalized}/{folder_name}" if normalized else folder_name

    def _sample_count(self, path: Path, source_type: str) -> int:
        if not path.exists():
            return FALLBACK_SAMPLE_COUNTS[source_type]
        return sum(1 for item in path.rglob("*") if item.is_file())
