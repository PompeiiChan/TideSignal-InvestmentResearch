"""Application settings loaded through PyCore ConfigManager."""

from functools import lru_cache
from pathlib import Path
from typing import cast

from dotenv import dotenv_values
from pydantic import Field

from pycore.core import BaseSettings, ConfigManager

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = BACKEND_ROOT / "config" / "app.toml"
ENV_FILE_PATH = BACKEND_ROOT / ".env"

_ENV_FIELD_MAP: dict[str, str] = {
    "LLM_API_KEY": "llm_api_key",
    "LLM_BASE_URL": "llm_base_url",
    "LLM_MODEL": "llm_model",
    "LLM_TIMEOUT": "llm_timeout",
    "LLM_ASSEMBLY_MODEL": "llm_assembly_model",
    "LLM_ASSEMBLY_TIMEOUT": "llm_assembly_timeout",
    "LLM_INTENT_API_KEY": "llm_intent_api_key",
    "LLM_INTENT_BASE_URL": "llm_intent_base_url",
    "LLM_INTENT_MODEL": "llm_intent_model",
    "EMBEDDING_API_KEY": "embedding_api_key",
    "EMBEDDING_BASE_URL": "embedding_base_url",
    "EMBEDDING_MODEL": "embedding_model",
    "EMBEDDING_DIM": "embedding_dim",
    "EMBEDDING_TIMEOUT": "embedding_timeout",
    "RERANK_API_KEY": "rerank_api_key",
    "RERANK_BASE_URL": "rerank_base_url",
    "RERANK_MODEL": "rerank_model",
    "LANGGRAPH_ENV": "langgraph_env",
    "LOCAL_KB_PATH": "local_kb_path",
    "MOCK_DATA_PATH": "mock_data_path",
    "REFERENCE_DATE": "reference_date",
}

_INT_ENV_FIELD_MAP: dict[str, str] = {
    "SHORT_TERM_QA_ROUNDS": "short_term_qa_rounds",
}


class AppSettings(BaseSettings):
    """Runtime settings for the FastAPI application."""

    app_name: str = "smart-investment-research-api"
    app_title: str = "Smart Investment Research API"
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8099
    debug: bool = False
    timezone: str = "Asia/Shanghai"
    database_url: str = "sqlite+aiosqlite:///./data/smart_investment.db"
    mock_data_path: str = "data/mock"
    local_kb_path: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout: str = "120"
    llm_assembly_model: str = ""
    llm_assembly_timeout: str = ""
    llm_intent_api_key: str = ""
    llm_intent_base_url: str = ""
    llm_intent_model: str = ""
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = ""
    embedding_dim: str = ""
    embedding_timeout: str = "180"
    rerank_api_key: str = ""
    rerank_base_url: str = ""
    rerank_model: str = ""
    langgraph_env: str = ""
    reference_date: str = ""
    short_term_qa_rounds: int = 5
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5199",
            "http://127.0.0.1:5199",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        ]
    )


def normalize_sqlite_url(database_url: str) -> str:
    """Resolve relative SQLite database paths from the backend directory."""
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        return database_url

    raw_path = database_url.removeprefix(prefix)
    if raw_path.startswith("/") or raw_path == ":memory:":
        return database_url

    db_path = (BACKEND_ROOT / raw_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"{prefix}{db_path}"


def _apply_env_overrides(settings: AppSettings) -> AppSettings:
    """Overlay sensitive runtime values from backend/.env onto ConfigManager settings."""
    if not ENV_FILE_PATH.exists():
        return settings

    env_values = dotenv_values(ENV_FILE_PATH)
    for env_key, attr_name in _ENV_FIELD_MAP.items():
        raw_value = env_values.get(env_key)
        if raw_value is None:
            continue
        value = str(raw_value).strip()
        if value:
            setattr(settings, attr_name, value)
    for env_key, attr_name in _INT_ENV_FIELD_MAP.items():
        raw_value = env_values.get(env_key)
        if raw_value is None:
            continue
        value = str(raw_value).strip()
        if value:
            setattr(settings, attr_name, int(value))
    return settings


@lru_cache(maxsize=1)
def get_settings(config_path: Path | None = None) -> AppSettings:
    """Load settings from an explicit config file through ConfigManager."""
    manager = ConfigManager[AppSettings]()
    manager.load(AppSettings, config_path or DEFAULT_CONFIG_PATH)
    settings = cast(AppSettings, manager.settings)
    settings.database_url = normalize_sqlite_url(settings.database_url)
    return _apply_env_overrides(settings)
