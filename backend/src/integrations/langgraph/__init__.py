"""LangGraph integration for investment research orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import LangGraphRunner

__all__ = ["LangGraphRunner", "is_langgraph_enabled"]


def __getattr__(name: str) -> object:
    if name == "LangGraphRunner":
        from .runner import LangGraphRunner

        return LangGraphRunner
    if name == "is_langgraph_enabled":
        from .runner import is_langgraph_enabled

        return is_langgraph_enabled
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
