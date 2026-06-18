"""Data source and runtime configuration status DTOs."""

from typing import Literal

from pydantic import BaseModel

SourceType = Literal["announcement", "report", "financial", "market", "qa", "knowledge"]
DataSourceStatusValue = Literal["ready", "mocked", "missing"]
ModelStatusValue = Literal["ready", "mocked", "missing"]
PromptAgent = Literal["master_agent", "hotspot_agent", "data_agent", "stock_agent", "quality_check"]
PromptStatus = Literal["default", "custom"]


class MockDataSourceRead(BaseModel):
    """One local data source shown on the data explanation page."""

    type: SourceType
    name: str
    path: str
    status: DataSourceStatusValue
    sample_count: int


class RagStatusRead(BaseModel):
    """RAG runtime status."""

    mode: Literal["mock", "semantic"]
    embedding_provider: str
    rerank_provider: str
    status: Literal["mocked", "ready"]
    chunk_count: int = 0
    indexed_files: int = 0


class DataSourceStatusRead(BaseModel):
    """Response for GET /api/data-sources/status."""

    mock_data: list[MockDataSourceRead]
    rag: RagStatusRead


class ModelConfigStatusRead(BaseModel):
    """One model/provider configuration status."""

    name: str
    fields: list[str]
    status: ModelStatusValue
    missing_fields: list[str]


class PromptStatusRead(BaseModel):
    """One prompt module status."""

    agent: PromptAgent
    name: str
    status: PromptStatus


class ComplianceRulesRead(BaseModel):
    """Compliance rule status shown in settings."""

    blacklist_expressions: list[str]
    risk_tip_required: bool
    citation_required: bool


class OrchestrationStatusRead(BaseModel):
    """LangGraph orchestration readiness status."""

    name: Literal["langgraph"]
    env: str
    status: Literal["ready", "blocked"]
    missing_requirements: list[str]


class ConfigStatusRead(BaseModel):
    """Response for GET /api/config/status."""

    models: list[ModelConfigStatusRead]
    prompts: list[PromptStatusRead]
    compliance_rules: ComplianceRulesRead
    orchestration: OrchestrationStatusRead
