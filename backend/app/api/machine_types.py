from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.machine_type import MachineType
from backend.app.models.production_batch import ProductionBatch
from backend.app.schemas.machine_type import MachineTypeCreate, MachineTypeUpdate, MachineTypeResponse

router = APIRouter(prefix="/machine-types", tags=["Machine Types"])


@router.get("", response_model=List[MachineTypeResponse])
def get_machine_types(db: Session = Depends(get_db)):
    """Retrieve all machine types."""
    return db.query(MachineType).order_by(MachineType.name.asc()).all()


@router.get("/{machine_type_id}", response_model=MachineTypeResponse)
def get_machine_type(machine_type_id: int, db: Session = Depends(get_db)):
    """Retrieve a single machine type by ID."""
    machine_type = db.query(MachineType).filter(MachineType.id == machine_type_id).first()
    if not machine_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine type with ID {machine_type_id} not found",
        )
    return machine_type


@router.post("", response_model=MachineTypeResponse, status_code=status.HTTP_201_CREATED)
def create_machine_type(payload: MachineTypeCreate, db: Session = Depends(get_db)):
    """Create a new machine type."""
    existing = db.query(MachineType).filter(MachineType.name.ilike(payload.name.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Machine type '{payload.name.strip()}' already exists.",
        )

    machine_type = MachineType(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(machine_type)
    db.commit()
    db.refresh(machine_type)
    return machine_type


@router.put("/{machine_type_id}", response_model=MachineTypeResponse)
def update_machine_type(machine_type_id: int, payload: MachineTypeUpdate, db: Session = Depends(get_db)):
    """Update an existing machine type."""
    machine_type = db.query(MachineType).filter(MachineType.id == machine_type_id).first()
    if not machine_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine type with ID {machine_type_id} not found",
        )

    if payload.name is not None:
        new_name = payload.name.strip()
        existing = (
            db.query(MachineType)
            .filter(MachineType.name.ilike(new_name), MachineType.id != machine_type_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Machine type '{new_name}' already exists.",
            )
        machine_type.name = new_name

    if payload.description is not None:
        machine_type.description = payload.description.strip() if payload.description else None

    db.commit()
    db.refresh(machine_type)
    return machine_type


@router.delete("/{machine_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine_type(machine_type_id: int, db: Session = Depends(get_db)):
    """Delete a machine type if not referenced by any production batch."""
    machine_type = db.query(MachineType).filter(MachineType.id == machine_type_id).first()
    if not machine_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine type with ID {machine_type_id} not found",
        )

    referenced_count = db.query(ProductionBatch).filter(ProductionBatch.machine_type_id == machine_type_id).count()
    if referenced_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete machine type '{machine_type.name}' because it is referenced by {referenced_count} production batch(es).",
        )

    db.delete(machine_type)
    db.commit()
    return None
