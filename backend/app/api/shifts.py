from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.shift import Shift
from backend.app.models.production_batch import ProductionBatch
from backend.app.schemas.shift import ShiftCreate, ShiftUpdate, ShiftResponse

router = APIRouter(prefix="/shifts", tags=["Shifts"])


@router.get("", response_model=List[ShiftResponse])
def get_shifts(db: Session = Depends(get_db)):
    """Retrieve all shifts."""
    return db.query(Shift).order_by(Shift.id.asc()).all()


@router.get("/{shift_id}", response_model=ShiftResponse)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    """Retrieve a single shift by ID."""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with ID {shift_id} not found",
        )
    return shift


@router.post("", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_shift(payload: ShiftCreate, db: Session = Depends(get_db)):
    """Create a new shift."""
    existing = db.query(Shift).filter(Shift.name.ilike(payload.name.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Shift '{payload.name.strip()}' already exists.",
        )

    shift = Shift(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


@router.put("/{shift_id}", response_model=ShiftResponse)
def update_shift(shift_id: int, payload: ShiftUpdate, db: Session = Depends(get_db)):
    """Update an existing shift."""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with ID {shift_id} not found",
        )

    if payload.name is not None:
        new_name = payload.name.strip()
        existing = (
            db.query(Shift)
            .filter(Shift.name.ilike(new_name), Shift.id != shift_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Shift '{new_name}' already exists.",
            )
        shift.name = new_name

    if payload.description is not None:
        shift.description = payload.description.strip() if payload.description else None

    db.commit()
    db.refresh(shift)
    return shift


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    """Delete a shift if not referenced by any production batch."""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with ID {shift_id} not found",
        )

    referenced_count = db.query(ProductionBatch).filter(ProductionBatch.shift_id == shift_id).count()
    if referenced_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete shift '{shift.name}' because it is referenced by {referenced_count} production batch(es).",
        )

    db.delete(shift)
    db.commit()
    return None
