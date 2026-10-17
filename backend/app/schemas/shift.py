from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from backend.app.schemas.base import CamelModel


import re

def standardize_shift_description(v: Optional[str]) -> Optional[str]:
    """
    Standardizes shift description to remove time ambiguity (e.g. 12:00 - 4:00 -> 12:00 PM – 04:00 PM).
    Preserves custom notes and clearly formats overnight shifts.
    """
    if not v:
        return v
    trimmed = v.strip()

    # Ambiguous afternoon pattern (e.g., '12:00 - 4:00', '12:00-4:00', '12:00 - 04:00')
    ambiguous_afternoon = re.compile(r"^12:00\s*-\s*0?4:00(\s.*)?$", re.IGNORECASE)
    match = ambiguous_afternoon.match(trimmed)
    if match:
        extra = match.group(1) or ""
        return f"12:00 PM – 04:00 PM (12:00 – 16:00) Afternoon Shift{extra}"

    return trimmed


class ShiftBase(CamelModel):
    name: str = Field(..., min_length=1, max_length=50, description="Shift name (e.g. Morning, Afternoon, Evening, Night)")
    description: Optional[str] = Field(None, max_length=500, description="Optional description with unambiguous 12h/24h hours")

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Shift name cannot be empty or blank")
        return trimmed

    @field_validator("description")
    @classmethod
    def standardize_desc(cls, v: Optional[str]) -> Optional[str]:
        return standardize_shift_description(v)


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(CamelModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Shift name cannot be empty or blank")
            return trimmed
        return v

    @field_validator("description")
    @classmethod
    def standardize_desc(cls, v: Optional[str]) -> Optional[str]:
        return standardize_shift_description(v)


class ShiftResponse(ShiftBase):
    id: int
    created_at: datetime
