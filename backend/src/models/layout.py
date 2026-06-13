"""Layout preference API DTOs."""

from pydantic import BaseModel


class LayoutPreferencesUpdate(BaseModel):
    """Request body for updating layout preferences."""

    sidebar_width: int
    trace_panel_width: int


class WidthRange(BaseModel):
    """Allowed width range."""

    min: int
    max: int


class LayoutPreferencesRead(BaseModel):
    """Layout preferences returned to the frontend."""

    sidebar_width: int
    sidebar_width_range: WidthRange
    trace_panel_width: int
    trace_panel_width_range: WidthRange
    updated_at: str
