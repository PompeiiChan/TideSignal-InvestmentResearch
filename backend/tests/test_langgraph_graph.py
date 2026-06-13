"""Tests for LangGraph graph compilation."""

from backend.src.integrations.langgraph.graph import GraphDeps, build_graph
from backend.src.integrations.langgraph.runner import is_langgraph_enabled
from backend.src.integrations.llm.service import LLMService
from backend.src.services.rag.service import RagService
from backend.src.settings import AppSettings


def test_build_graph_compiles() -> None:
    """build_graph returns a compiled graph without raising."""
    deps = GraphDeps(
        llm=LLMService(),
        rag=RagService(),
        settings=AppSettings(),
    )
    compiled = build_graph(deps)
    assert compiled is not None
    assert hasattr(compiled, "ainvoke")


def test_is_langgraph_enabled_only_when_local() -> None:
    """LANGGRAPH_ENV must be exactly local after strip."""
    assert is_langgraph_enabled(AppSettings(langgraph_env="local")) is True
    assert is_langgraph_enabled(AppSettings(langgraph_env="")) is False
    assert is_langgraph_enabled(AppSettings(langgraph_env="cloud")) is False
    assert is_langgraph_enabled(AppSettings(langgraph_env="  ")) is False
