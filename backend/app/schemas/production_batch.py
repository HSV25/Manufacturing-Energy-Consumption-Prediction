from datetime import datetime, date
from typing import Optional
from pydantic import Field, field_validator
from backend.app.schemas.base import CamelModel
from backend.app.schemas.product import ProductResponse
from backend.app.schemas.machine_type import MachineTypeResponse
from backend.app.schemas.shift import ShiftResponse


class ProductionBatchBase(CamelModel):
    batch_number: str = Field(..., min_length=1, max_length=50, description="Unique batch identifier")
    product_id: int = Field(..., gt=0, description="Product ID")
    quantity: float = Field(..., gt=0, description="Production quantity (must be positive)")
    machine_hours: float = Field(..., gt=0, description="Machine running hours (must be positive)")
    machine_type_id: int = Field(..., gt=0, description="Machine Type ID")
    shift_id: int = Field(..., gt=0, description="Shift ID")
    production_date: date = Field(..., description="Production date (YYYY-MM-DD)")
    actual_energy_consumed_kwh: Optional[float] = Field(None, ge=0, description="Actual energy consumed in kWh (nullable before completion)")

    @field_validator("batch_number")
    @classmethod
    def validate_batch_number(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Batch number cannot be blank")
        return trimmed


class ProductionBatchCreate(ProductionBatchBase):
    pass


class ProductionBatchUpdate(CamelModel):
    batch_number: Optional[str] = Field(None, min_length=1, max_length=50)
    product_id: Optional[int] = Field(None, gt=0)
    quantity: Optional[float] = Field(None, gt=0)
    machine_hours: Optional[float] = Field(None, gt=0)
    machine_type_id: Optional[int] = Field(None, gt=0)
    shift_id: Optional[int] = Field(None, gt=0)
    production_date: Optional[date] = None
    actual_energy_consumed_kwh: Optional[float] = Field(None, ge=0)

    @field_validator("batch_number")
    @classmethod
    def validate_batch_number_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Batch number cannot be blank")
            return trimmed
        return v


class ProductionBatchResponse(ProductionBatchBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # Expanded relations for UI convenience
    product: Optional[ProductResponse] = None
    machine_type: Optional[MachineTypeResponse] = None
    shift: Optional[ShiftResponse] = None
