"""Project database session based on the PyCore database session template."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pycore.core import get_logger

from ..settings import get_settings
from .models import Base

settings = get_settings()
logger = get_logger()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a project database session for FastAPI dependencies."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Yield a project database session as an async context manager."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def ensure_schema_columns() -> None:
    """Apply lightweight SQLite migrations for columns added after initial deploy."""
    from sqlalchemy import text

    async with engine.begin() as conn:

        def _migrate(connection) -> None:
            result = connection.execute(text("PRAGMA table_info(investment_sessions)"))
            columns = {row[1] for row in result}
            if "context_state" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE investment_sessions "
                        "ADD COLUMN context_state JSON NOT NULL DEFAULT '{}'"
                    )
                )

        await conn.run_sync(_migrate)


async def init_db() -> None:
    """Create project tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_schema_columns()
    logger.info("Database initialized")


async def close_db() -> None:
    """Dispose the project database engine."""
    await engine.dispose()
    logger.info("Database connection closed")
