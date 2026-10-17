from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from backend.app.schemas.base import CamelModel


class MachineTypeBase(CamelModel):
    name: str = Field(..., min_length=1, max_length=100, description="Machine type name (e.g. CNC, Lathe, Milling Machine)")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Machine type name cannot be empty or blank")
        return trimmed


class MachineTypeCreate(MachineTypeBase):
    pass


class MachineTypeUpdate(CamelModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Machine type name cannot be empty or blank")
            return trimmed
        return v


class MachineTypeResponse(MachineTypeBase):
    id: int
    created_at: datetime
