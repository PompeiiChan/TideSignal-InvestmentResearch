"""Demo deployment API models."""

from pydantic import BaseModel, Field


class DemoQuotaRead(BaseModel):
    enabled: bool
    limit: int = Field(ge=0)
    used: int = Field(ge=0)
    remaining: int = Field(ge=0)
    reset_date: str
    visitor_id: str = ""
