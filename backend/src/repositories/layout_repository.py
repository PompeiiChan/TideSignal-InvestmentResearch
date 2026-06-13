"""Database access for layout preferences."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import LayoutPreferenceRecord


class LayoutRepository:
    """Repository for single-user layout preferences."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self) -> LayoutPreferenceRecord | None:
        """Return the single layout preference row."""
        result = await self.db.execute(select(LayoutPreferenceRecord).where(LayoutPreferenceRecord.id == 1))
        return result.scalar_one_or_none()

    async def save(self, preference: LayoutPreferenceRecord) -> LayoutPreferenceRecord:
        """Persist layout preferences."""
        self.db.add(preference)
        await self.db.flush()
        await self.db.refresh(preference)
        return preference
