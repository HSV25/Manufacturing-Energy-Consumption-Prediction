from backend.app.schemas.base import CamelModel
from backend.app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from backend.app.schemas.machine_type import MachineTypeCreate, MachineTypeUpdate, MachineTypeResponse
from backend.app.schemas.shift import ShiftCreate, ShiftUpdate, ShiftResponse
from backend.app.schemas.production_batch import ProductionBatchCreate, ProductionBatchUpdate, ProductionBatchResponse
from backend.app.schemas.prediction import PredictionRequest, PredictionResponse, PredictionHistoryItem, BatchPredictionRequest
from backend.app.schemas.dashboard import DashboardStats

__all__ = [
    "CamelModel",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "MachineTypeCreate",
    "MachineTypeUpdate",
    "MachineTypeResponse",
    "ShiftCreate",
    "ShiftUpdate",
    "ShiftResponse",
    "ProductionBatchCreate",
    "ProductionBatchUpdate",
    "ProductionBatchResponse",
    "PredictionRequest",
    "PredictionResponse",
    "PredictionHistoryItem",
    "BatchPredictionRequest",
    "DashboardStats",
]
