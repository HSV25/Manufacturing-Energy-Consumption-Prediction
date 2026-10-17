import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from backend.app.database import get_db
from backend.app.models.product import Product
from backend.app.models.machine_type import MachineType
from backend.app.models.shift import Shift
from backend.app.models.production_batch import ProductionBatch
from backend.app.models.energy_prediction import EnergyPrediction
from backend.app.schemas.dashboard import DashboardStats
from backend.app.schemas.prediction import PredictionHistoryItem
from backend.app.schemas.production_batch import ProductionBatchResponse
from backend.ml.predict import predictor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Retrieve operational dashboard summary metrics and recent activity."""
    total_products = db.query(Product).count()
    total_machine_types = db.query(MachineType).count()
    total_shifts = db.query(Shift).count()
    total_batches = db.query(ProductionBatch).count()

    completed_batches = (
        db.query(ProductionBatch)
        .filter(ProductionBatch.actual_energy_consumed_kwh.isnot(None))
        .count()
    )
    pending_batches = total_batches - completed_batches

    total_predictions = db.query(EnergyPrediction).count()

    avg_predicted = (
        db.query(func.avg(EnergyPrediction.estimated_energy_kwh)).scalar()
    )
    avg_actual = (
        db.query(func.avg(ProductionBatch.actual_energy_consumed_kwh))
        .filter(ProductionBatch.actual_energy_consumed_kwh.isnot(None))
        .scalar()
    )

    # Recent predictions (latest 5)
    recent_pred_records = (
        db.query(EnergyPrediction)
        .options(joinedload(EnergyPrediction.production_batch))
        .order_by(EnergyPrediction.created_at.desc())
        .limit(5)
        .all()
    )
    recent_predictions = [
        PredictionHistoryItem(
            id=r.id,
            production_batch_id=r.production_batch_id,
            product_id=r.product_id,
            product_name=r.product_name,
            quantity=r.quantity,
            machine_hours=r.machine_hours,
            machine_type_id=r.machine_type_id,
            machine_type_name=r.machine_type_name,
            shift_id=r.shift_id,
            shift_name=r.shift_name,
            estimated_energy_kwh=r.estimated_energy_kwh,
            actual_energy_kwh=r.production_batch.actual_energy_consumed_kwh if r.production_batch else None,
            model_version=r.model_version,
            created_at=r.created_at,
            batch_number=r.production_batch.batch_number if r.production_batch else None,
        )
        for r in recent_pred_records
    ]

    # Recent batches (latest 5)
    recent_batch_records = (
        db.query(ProductionBatch)
        .options(
            joinedload(ProductionBatch.product),
            joinedload(ProductionBatch.machine_type),
            joinedload(ProductionBatch.shift),
        )
        .order_by(ProductionBatch.production_date.desc(), ProductionBatch.id.desc())
        .limit(5)
        .all()
    )
    recent_batches = [
        ProductionBatchResponse.model_validate(b) for b in recent_batch_records
    ]

    return DashboardStats(
        total_products=total_products,
        total_machine_types=total_machine_types,
        total_shifts=total_shifts,
        total_batches=total_batches,
        completed_batches=completed_batches,
        pending_batches=pending_batches,
        total_predictions=total_predictions,
        average_predicted_energy_kwh=round(avg_predicted, 2) if avg_predicted else None,
        average_actual_energy_kwh=round(avg_actual, 2) if avg_actual else None,
        recent_predictions=recent_predictions,
        recent_batches=recent_batches,
    )


@router.get("/model-status")
def get_model_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retrieve current ML model lifecycle information, test evaluation metrics,
    and detect whether any configured database categories require model retraining.
    """
    info = predictor.get_info()

    # Query database categories
    configured_machines = [m.name for m in db.query(MachineType).order_by(MachineType.name.asc()).all()]
    configured_shifts = [s.name for s in db.query(Shift).order_by(Shift.name.asc()).all()]

    supported_machines = info.get("supported_machine_types", [])
    supported_shifts = info.get("supported_shifts", [])

    unsupported_machines = [
        m for m in configured_machines
        if not any(sm.lower() == m.lower() for sm in supported_machines)
    ]
    unsupported_shifts = [
        s for s in configured_shifts
        if not any(ss.lower() == s.lower() for ss in supported_shifts)
    ]

    info["configured_machine_types"] = configured_machines
    info["configured_shifts"] = configured_shifts
    info["unsupported_configured_machines"] = unsupported_machines
    info["unsupported_configured_shifts"] = unsupported_shifts
    info["retraining_required"] = len(unsupported_machines) > 0 or len(unsupported_shifts) > 0

    return info


@router.post("/retrain-model")
def retrain_model_endpoint(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Administrative endpoint to retrain the ML model on all currently configured
    machine types and shifts from the database.
    Atomically swaps the active model upon passing candidate validation.
    """
    from backend.ml.train_model import retrain_with_categories

    configured_machines = [m.name for m in db.query(MachineType).all()]
    configured_shifts = [s.name for s in db.query(Shift).all()]
    if not configured_machines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No configured machine types found in database to train.",
        )

    try:
        metrics = retrain_with_categories(
            machine_types=configured_machines,
            shifts=configured_shifts if configured_shifts else None,
        )
        predictor.reload()
        return {
            "success": True,
            "message": f"Successfully retrained model for {len(configured_machines)} machine types and {len(configured_shifts)} shifts.",
            "model_version": metrics.get("model_version"),
            "metrics": metrics.get("metrics"),
            "supported_machine_types": metrics.get("known_categories", {}).get("machine_types", []),
            "supported_shifts": metrics.get("known_categories", {}).get("shifts", []),
        }
    except Exception as e:
        logger.error(f"Retraining failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model retraining failed: {str(e)}. Previous model remains active.",
        )
