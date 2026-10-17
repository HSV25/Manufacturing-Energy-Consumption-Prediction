from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from backend.app.database import get_db
from backend.app.models.energy_prediction import EnergyPrediction
from backend.app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    PredictionHistoryItem,
)
from backend.app.services.prediction_service import process_prediction

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post("", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
def make_prediction(payload: PredictionRequest, db: Session = Depends(get_db)):
    """Workflow A: Submit features and calculate energy prediction, saving an audit record."""
    return process_prediction(
        db=db,
        quantity=payload.quantity,
        machine_hours=payload.machine_hours,
        machine_type_name=payload.machine_type,
        shift_name=payload.shift,
        product_id=payload.product_id,
        product_name=payload.product_name,
        production_batch_id=payload.production_batch_id,
        save_to_db=True,
    )


@router.get("", response_model=List[PredictionHistoryItem])
def get_prediction_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    machine_type: Optional[str] = Query(None),
    shift: Optional[str] = Query(None),
    batch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve historical prediction records with pagination and filters."""
    query = (
        db.query(EnergyPrediction)
        .options(joinedload(EnergyPrediction.production_batch))
    )

    if machine_type:
        query = query.filter(EnergyPrediction.machine_type_name.ilike(f"%{machine_type.strip()}%"))
    if shift:
        query = query.filter(EnergyPrediction.shift_name.ilike(f"%{shift.strip()}%"))
    if batch_id:
        query = query.filter(EnergyPrediction.production_batch_id == batch_id)

    records = (
        query.order_by(EnergyPrediction.created_at.desc(), EnergyPrediction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for r in records:
        batch_num = r.production_batch.batch_number if r.production_batch else None
        actual_kwh = r.production_batch.actual_energy_consumed_kwh if r.production_batch else None
        results.append(
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
                actual_energy_kwh=actual_kwh,
                model_version=r.model_version,
                created_at=r.created_at,
                batch_number=batch_num,
            )
        )
    return results


@router.get("/{prediction_id}", response_model=PredictionHistoryItem)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)):
    """Retrieve a single prediction record by ID."""
    r = (
        db.query(EnergyPrediction)
        .options(joinedload(EnergyPrediction.production_batch))
        .filter(EnergyPrediction.id == prediction_id)
        .first()
    )
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction record with ID {prediction_id} not found",
        )

    batch_num = r.production_batch.batch_number if r.production_batch else None
    actual_kwh = r.production_batch.actual_energy_consumed_kwh if r.production_batch else None
    return PredictionHistoryItem(
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
        actual_energy_kwh=actual_kwh,
        model_version=r.model_version,
        created_at=r.created_at,
        batch_number=batch_num,
    )
