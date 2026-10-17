import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.energy_prediction import EnergyPrediction
from backend.app.models.production_batch import ProductionBatch
from backend.app.models.product import Product
from backend.app.models.machine_type import MachineType
from backend.app.models.shift import Shift
from backend.ml.predict import predictor

logger = logging.getLogger(__name__)


def process_prediction(
    db: Session,
    quantity: float,
    machine_hours: float,
    machine_type_name: str,
    shift_name: str,
    product_id: Optional[int] = None,
    product_name: Optional[str] = None,
    production_batch_id: Optional[int] = None,
    save_to_db: bool = True,
) -> Dict[str, Any]:
    """
    Validates business inputs, verifies database entities, checks active model support,
    executes ML inference, and persists the prediction audit record.
    """
    # 1. Numeric and string input validation
    if quantity is None or quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Quantity must be a positive number greater than 0, received: {quantity}",
        )

    if machine_hours is None or machine_hours <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Machine hours must be a positive number greater than 0, received: {machine_hours}",
        )

    if not machine_type_name or not str(machine_type_name).strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Machine type must not be blank",
        )

    if not shift_name or not str(shift_name).strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Shift must not be blank",
        )

    machine_type_clean = str(machine_type_name).strip()
    shift_clean = str(shift_name).strip()

    # 2. Authoritative Database Existence Validation
    machine_type_obj = (
        db.query(MachineType)
        .filter(MachineType.name.ilike(machine_type_clean))
        .first()
    )
    if not machine_type_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Machine type '{machine_type_name}' does not exist in the database. "
                "Please configure it in Master Data first."
            ),
        )

    shift_obj = (
        db.query(Shift)
        .filter(Shift.name.ilike(shift_clean))
        .first()
    )
    if not shift_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Shift '{shift_name}' does not exist in the database. "
                "Please configure it in Master Data first."
            ),
        )

    # 3. Model Readiness Verification
    if not predictor.is_ready():
        if not predictor.load_model():
            try:
                from backend.ml.train_model import train_and_evaluate, DEFAULT_DATA_PATH
                if DEFAULT_DATA_PATH.exists():
                    logger.warning("Attempting automatic model rebuild from historical dataset...")
                    train_and_evaluate(data_path=DEFAULT_DATA_PATH)
                    predictor.reload()
            except Exception as e:
                logger.error(f"Automatic model rebuild failed: {e}")

        if not predictor.is_ready():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Energy prediction model is not trained or unavailable ({predictor.load_error}). Please run the model training script.",
            )

    # 4. Check whether configured entity is represented in the active model
    canonical_machine_name = machine_type_obj.name
    canonical_shift_name = shift_obj.name

    if not predictor.is_machine_type_supported(canonical_machine_name):
        supported_machines = predictor.get_supported_machine_types()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Machine type '{canonical_machine_name}' is registered in the database, "
                f"but the active prediction model ({predictor.model_version}) has not been trained for this category. "
                f"Currently supported machine types: {', '.join(supported_machines)}. "
                f"Please retrain the model with representative data for '{canonical_machine_name}'."
            ),
        )

    if not predictor.is_shift_supported(canonical_shift_name):
        supported_shifts = predictor.get_supported_shifts()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Shift '{canonical_shift_name}' is registered in the database, "
                f"but the active prediction model ({predictor.model_version}) has not been trained for this shift. "
                f"Currently supported shifts: {', '.join(supported_shifts)}."
            ),
        )

    # Resolve optional product details
    resolved_product_id = product_id
    resolved_product_name = product_name
    if product_id and not product_name:
        prod_obj = db.query(Product).filter(Product.id == product_id).first()
        if prod_obj:
            resolved_product_name = prod_obj.name
    elif product_name and not product_id:
        prod_obj = db.query(Product).filter(Product.name.ilike(product_name.strip())).first()
        if prod_obj:
            resolved_product_id = prod_obj.id

    # 5. Run ML prediction inference
    try:
        prediction_result = predictor.predict(
            quantity=quantity,
            machine_hours=machine_hours,
            machine_type=canonical_machine_name,
            shift=canonical_shift_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Prediction failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}",
        )

    # 6. Persist audit record in EnergyPredictions table
    saved_record_id = None
    saved_created_at = None
    if save_to_db:
        db_prediction = EnergyPrediction(
            production_batch_id=production_batch_id,
            product_id=resolved_product_id,
            product_name=resolved_product_name,
            quantity=quantity,
            machine_hours=machine_hours,
            machine_type_id=machine_type_obj.id,
            machine_type_name=canonical_machine_name,
            shift_id=shift_obj.id,
            shift_name=canonical_shift_name,
            estimated_energy_kwh=prediction_result["estimated_energy"],
            model_version=prediction_result["model_version"],
        )
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)
        saved_record_id = db_prediction.id
        saved_created_at = db_prediction.created_at

    return {
        "estimated_energy": prediction_result["estimated_energy"],
        "unit": prediction_result["unit"],
        "model_version": prediction_result["model_version"],
        "prediction_id": saved_record_id,
        "created_at": saved_created_at,
    }


def predict_for_saved_batch(db: Session, batch_id: int) -> Dict[str, Any]:
    """
    Workflow B: Predict energy consumption for an existing production batch.
    """
    batch = db.query(ProductionBatch).filter(ProductionBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production batch with ID {batch_id} not found",
        )

    machine_type_name = batch.machine_type.name if batch.machine_type else "Unknown"
    shift_name = batch.shift.name if batch.shift else "Unknown"
    product_name = batch.product.name if batch.product else None

    return process_prediction(
        db=db,
        quantity=batch.quantity,
        machine_hours=batch.machine_hours,
        machine_type_name=machine_type_name,
        shift_name=shift_name,
        product_id=batch.product_id,
        product_name=product_name,
        production_batch_id=batch.id,
        save_to_db=True,
    )
