from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from backend.app.database import get_db
from backend.app.models.production_batch import ProductionBatch
from backend.app.models.product import Product
from backend.app.models.machine_type import MachineType
from backend.app.models.shift import Shift
from backend.app.schemas.production_batch import (
    ProductionBatchCreate,
    ProductionBatchUpdate,
    ProductionBatchResponse,
)
from backend.app.schemas.prediction import PredictionResponse
from backend.app.services.prediction_service import predict_for_saved_batch

router = APIRouter(prefix="/production-batches", tags=["Production Batches"])


@router.get("", response_model=List[ProductionBatchResponse])
def get_production_batches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Search by batch number"),
    product_id: Optional[int] = Query(None),
    machine_type_id: Optional[int] = Query(None),
    shift_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve production batches with optional filtering and pagination."""
    query = (
        db.query(ProductionBatch)
        .options(
            joinedload(ProductionBatch.product),
            joinedload(ProductionBatch.machine_type),
            joinedload(ProductionBatch.shift),
        )
    )

    if search:
        query = query.filter(ProductionBatch.batch_number.ilike(f"%{search.strip()}%"))
    if product_id:
        query = query.filter(ProductionBatch.product_id == product_id)
    if machine_type_id:
        query = query.filter(ProductionBatch.machine_type_id == machine_type_id)
    if shift_id:
        query = query.filter(ProductionBatch.shift_id == shift_id)

    return (
        query.order_by(ProductionBatch.production_date.desc(), ProductionBatch.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{batch_id}", response_model=ProductionBatchResponse)
def get_production_batch(batch_id: int, db: Session = Depends(get_db)):
    """Retrieve a single production batch by ID."""
    batch = (
        db.query(ProductionBatch)
        .options(
            joinedload(ProductionBatch.product),
            joinedload(ProductionBatch.machine_type),
            joinedload(ProductionBatch.shift),
        )
        .filter(ProductionBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production batch with ID {batch_id} not found",
        )
    return batch


@router.post("", response_model=ProductionBatchResponse, status_code=status.HTTP_201_CREATED)
def create_production_batch(payload: ProductionBatchCreate, db: Session = Depends(get_db)):
    """Create a new production batch."""
    # Check duplicate batch number
    clean_batch_num = payload.batch_number.strip()
    existing = db.query(ProductionBatch).filter(ProductionBatch.batch_number == clean_batch_num).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Batch number '{clean_batch_num}' already exists.",
        )

    # Validate foreign keys
    if not db.query(Product).filter(Product.id == payload.product_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with ID {payload.product_id} does not exist.",
        )
    if not db.query(MachineType).filter(MachineType.id == payload.machine_type_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Machine type with ID {payload.machine_type_id} does not exist.",
        )
    if not db.query(Shift).filter(Shift.id == payload.shift_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Shift with ID {payload.shift_id} does not exist.",
        )

    batch = ProductionBatch(
        batch_number=clean_batch_num,
        product_id=payload.product_id,
        quantity=payload.quantity,
        machine_hours=payload.machine_hours,
        machine_type_id=payload.machine_type_id,
        shift_id=payload.shift_id,
        production_date=payload.production_date,
        actual_energy_consumed_kwh=payload.actual_energy_consumed_kwh,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Reload with relationships
    return get_production_batch(batch.id, db)


@router.put("/{batch_id}", response_model=ProductionBatchResponse)
def update_production_batch(batch_id: int, payload: ProductionBatchUpdate, db: Session = Depends(get_db)):
    """Update an existing production batch or enter actual energy consumed."""
    batch = db.query(ProductionBatch).filter(ProductionBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production batch with ID {batch_id} not found",
        )

    if payload.batch_number is not None:
        clean_num = payload.batch_number.strip()
        existing = (
            db.query(ProductionBatch)
            .filter(ProductionBatch.batch_number == clean_num, ProductionBatch.id != batch_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Batch number '{clean_num}' already exists.",
            )
        batch.batch_number = clean_num

    if payload.product_id is not None:
        if not db.query(Product).filter(Product.id == payload.product_id).first():
            raise HTTPException(status_code=400, detail=f"Product with ID {payload.product_id} does not exist.")
        batch.product_id = payload.product_id

    if payload.machine_type_id is not None:
        if not db.query(MachineType).filter(MachineType.id == payload.machine_type_id).first():
            raise HTTPException(status_code=400, detail=f"Machine type with ID {payload.machine_type_id} does not exist.")
        batch.machine_type_id = payload.machine_type_id

    if payload.shift_id is not None:
        if not db.query(Shift).filter(Shift.id == payload.shift_id).first():
            raise HTTPException(status_code=400, detail=f"Shift with ID {payload.shift_id} does not exist.")
        batch.shift_id = payload.shift_id

    if payload.quantity is not None:
        batch.quantity = payload.quantity
    if payload.machine_hours is not None:
        batch.machine_hours = payload.machine_hours
    if payload.production_date is not None:
        batch.production_date = payload.production_date
    if payload.actual_energy_consumed_kwh is not None:
        batch.actual_energy_consumed_kwh = payload.actual_energy_consumed_kwh

    db.commit()
    db.refresh(batch)

    return get_production_batch(batch.id, db)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_batch(batch_id: int, db: Session = Depends(get_db)):
    """Delete a production batch safely."""
    batch = db.query(ProductionBatch).filter(ProductionBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production batch with ID {batch_id} not found",
        )

    db.delete(batch)
    db.commit()
    return None


@router.post("/{batch_id}/predict", response_model=PredictionResponse)
def predict_batch_energy(batch_id: int, db: Session = Depends(get_db)):
    """Workflow B: Calculate and save energy prediction for an existing production batch."""
    return predict_for_saved_batch(db=db, batch_id=batch_id)
