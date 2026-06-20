"""API route registrations."""

from .chat import router as chat_router
from .config_status import config_router, data_sources_router
from .demo import router as demo_router
from .health import router as health_router
from .layout import router as layout_router
from .sessions import router as sessions_router
from .traces import router as traces_router

__all__ = [
    "chat_router",
    "config_router",
    "data_sources_router",
    "demo_router",
    "health_router",
    "layout_router",
    "sessions_router",
    "traces_router",
]
