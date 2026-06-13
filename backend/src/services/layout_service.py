"""Layout preference business service."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import LayoutPreferenceRecord
from ..models.layout import LayoutPreferencesRead, WidthRange
from ..repositories.layout_repository import LayoutRepository
from ..settings import get_settings

SIDEBAR_MIN = 240
SIDEBAR_MAX = 420
TRACE_PANEL_MIN = 380
TRACE_PANEL_MAX = 640
DEFAULT_SIDEBAR_WIDTH = 288
DEFAULT_TRACE_PANEL_WIDTH = 488


def _now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().timezone))


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(get_settings().timezone))
    return value.isoformat(timespec="seconds")


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


class LayoutService:
    """Business logic for layout preferences."""

    def __init__(self, db: AsyncSession):
        self.repo = LayoutRepository(db)
        self.db = db

    async def get_preferences(self) -> LayoutPreferencesRead:
        """Return current preferences, creating defaults if needed."""
        record = await self.repo.get()
        if record is None:
            record = LayoutPreferenceRecord(
                id=1,
                sidebar_width=DEFAULT_SIDEBAR_WIDTH,
                trace_panel_width=DEFAULT_TRACE_PANEL_WIDTH,
                updated_at=_now(),
            )
            await self.repo.save(record)
            await self.db.commit()
        return self._to_read(record)

    async def update_preferences(
        self,
        sidebar_width: int,
        trace_panel_width: int,
    ) -> LayoutPreferencesRead:
        """Persist validated preferences."""
        if sidebar_width < SIDEBAR_MIN or sidebar_width > SIDEBAR_MAX:
            raise ValueError("sidebar_width 必须在 240 到 420 之间")
        if trace_panel_width < TRACE_PANEL_MIN or trace_panel_width > TRACE_PANEL_MAX:
            raise ValueError("trace_panel_width 必须在 380 到 640 之间")
        record = await self.repo.get()
        if record is None:
            record = LayoutPreferenceRecord(id=1, updated_at=_now())
        record.sidebar_width = _clamp(sidebar_width, SIDEBAR_MIN, SIDEBAR_MAX)
        record.trace_panel_width = _clamp(trace_panel_width, TRACE_PANEL_MIN, TRACE_PANEL_MAX)
        record.updated_at = _now()
        await self.repo.save(record)
        await self.db.commit()
        return self._to_read(record)

    def _to_read(self, record: LayoutPreferenceRecord) -> LayoutPreferencesRead:
        return LayoutPreferencesRead(
            sidebar_width=record.sidebar_width,
            sidebar_width_range=WidthRange(min=SIDEBAR_MIN, max=SIDEBAR_MAX),
            trace_panel_width=record.trace_panel_width,
            trace_panel_width_range=WidthRange(min=TRACE_PANEL_MIN, max=TRACE_PANEL_MAX),
            updated_at=_iso(record.updated_at),
        )
