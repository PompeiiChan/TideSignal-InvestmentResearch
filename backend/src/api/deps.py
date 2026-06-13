"""Project API dependencies based on the PyCore dependency template."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Expose the project database session for route-level dependencies."""
    async for session in get_db():
        yield session
