from typing import List, Optional
from backend.app.schemas.base import CamelModel
from backend.app.schemas.prediction import PredictionHistoryItem
from backend.app.schemas.production_batch import ProductionBatchResponse


class DashboardStats(CamelModel):
    total_products: int = 0
    total_machine_types: int = 0
    total_shifts: int = 0
    total_batches: int = 0
    completed_batches: int = 0
    pending_batches: int = 0
    total_predictions: int = 0
    average_predicted_energy_kwh: Optional[float] = None
    average_actual_energy_kwh: Optional[float] = None
    recent_predictions: List[PredictionHistoryItem] = []
    recent_batches: List[ProductionBatchResponse] = []
