from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from backend.app.schemas.base import CamelModel


class PredictionRequest(CamelModel):
    quantity: float = Field(..., gt=0, description="Production quantity, must be greater than 0")
    machine_hours: float = Field(..., gt=0, description="Machine running hours, must be greater than 0")
    machine_type: str = Field(..., min_length=1, max_length=100, description="Machine type name (e.g. CNC, Lathe, Milling Machine)")
    shift: str = Field(..., min_length=1, max_length=50, description="Shift name (e.g. Morning, Evening, Night)")

    # Optional context fields
    product_id: Optional[int] = Field(None, gt=0, description="Optional associated product ID")
    product_name: Optional[str] = Field(None, max_length=100, description="Optional associated product name")
    production_batch_id: Optional[int] = Field(None, gt=0, description="Optional associated production batch ID")

    @field_validator("machine_type", "shift")
    @classmethod
    def validate_non_blank_strings(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Value cannot be blank")
        return trimmed


class PredictionResponse(CamelModel):
    estimated_energy: float = Field(..., description="Estimated energy consumption in kWh")
    unit: str = Field(default="kWh", description="Energy unit")
    model_version: str = Field(default="v1.0.0", description="Model version used for inference")
    prediction_id: Optional[int] = Field(None, description="Database ID of saved prediction record")
    created_at: Optional[datetime] = Field(None, description="Timestamp when prediction was calculated and persisted")


class PredictionHistoryItem(CamelModel):
    id: int
    production_batch_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: float
    machine_hours: float
    machine_type_id: Optional[int] = None
    machine_type_name: str
    shift_id: Optional[int] = None
    shift_name: str
    estimated_energy_kwh: float
    actual_energy_kwh: Optional[float] = None
    model_version: str
    created_at: datetime
    batch_number: Optional[str] = None


class BatchPredictionRequest(CamelModel):
    notes: Optional[str] = None
