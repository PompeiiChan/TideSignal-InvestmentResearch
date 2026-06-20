"""FastAPI application entrypoint built with PyCore APIServer."""

from pycore.api import (
    APIConfig,
    APIServer,
    ErrorHandlerMiddleware,
    RequestContextMiddleware,
)
from pycore.core import Logger, LoggerConfig, LogLevel

from .api.routes import (
    chat_router,
    config_router,
    data_sources_router,
    demo_router,
    health_router,
    layout_router,
    sessions_router,
    traces_router,
)
from .db.session import async_session_maker, close_db, init_db
from .services.session_service import SessionService
from .settings import get_settings

settings = get_settings()

Logger.configure(
    LoggerConfig(
        level=LogLevel.DEBUG if settings.debug else LogLevel.INFO,
        console_enabled=True,
        file_enabled=False,
        app_name=settings.app_name,
    )
)

server = APIServer(
    APIConfig(
        title=settings.app_title,
        description="Backend API for the smart investment research MVP.",
        version=settings.version,
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        cors_enabled=True,
        cors_origins=settings.cors_origins,
        cors_methods=["*"],
        cors_headers=["*"],
    )
)
server.on_startup(init_db)


async def _seed_showcase_rich_blocks() -> None:
    async with async_session_maker() as db:
        service = SessionService(db)
        await service.ensure_client_showcase_sessions()
        await service.ensure_showcase_rich_blocks()
        await service.ensure_seed_data()


server.on_startup(_seed_showcase_rich_blocks)
server.on_shutdown(close_db)
server.add_middleware(ErrorHandlerMiddleware, debug=settings.debug)
server.add_middleware(RequestContextMiddleware)
server.include_router(health_router)
server.include_router(demo_router)
server.include_router(sessions_router)
server.include_router(layout_router)
server.include_router(chat_router)
server.include_router(traces_router)
server.include_router(data_sources_router)
server.include_router(config_router)

app = server.app
