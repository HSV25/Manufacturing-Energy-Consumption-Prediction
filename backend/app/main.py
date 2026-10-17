import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.config import CORS_ORIGINS, DEBUG
from backend.app.database import engine, Base, get_db
from backend.app.models import (
    Product,
    MachineType,
    Shift,
    ProductionBatch,
    EnergyPrediction,
)
from backend.app.api.products import router as products_router
from backend.app.api.machine_types import router as machine_types_router
from backend.app.api.shifts import router as shifts_router
from backend.app.api.production_batches import router as production_batches_router
from backend.app.api.predictions import router as predictions_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.schemas.prediction import PredictionRequest, PredictionResponse
from backend.app.services.prediction_service import process_prediction
from backend.ml.predict import predictor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("manufacturing_energy_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema is created
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized.")

    # Check and log model readiness
    if predictor.is_ready():
        logger.info(f"ML Model is loaded and ready (version {predictor.model_version}).")
    else:
        logger.warning(f"ML Model is not ready ({predictor.load_error}). Attempting automatic build from historical dataset...")
        try:
            from backend.ml.train_model import train_and_evaluate, DEFAULT_DATA_PATH
            if DEFAULT_DATA_PATH.exists():
                train_and_evaluate(data_path=DEFAULT_DATA_PATH)
                predictor.reload()
                if predictor.is_ready():
                    logger.info(f"ML Model successfully built and activated (version {predictor.model_version}).")
        except Exception as e:
            logger.error(f"Automatic model build failed: {e}")

    yield
    logger.info("Application shutdown.")


app = FastAPI(
    title="Manufacturing Energy Consumption Prediction System",
    description="REST API and Supervised Machine Learning Inference for Factory Electricity Estimation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler to prevent raw stack trace leakage
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error handling {request.method} {request.url.path}: {exc}", exc_info=DEBUG)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the administrator."},
    )


# Health Check
@app.get("/health", tags=["Health"])
def health_check():
    """System health and ML service readiness check."""
    return {
        "status": "healthy",
        "service": "Manufacturing Energy Consumption Prediction API",
        "model_ready": predictor.is_ready(),
        "model_version": predictor.model_version,
    }


# Mandatory Prediction Endpoint required by Assessment Specification: POST /predict-energy
@app.post(
    "/predict-energy",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prediction"],
    summary="Official Prediction Endpoint",
)
def predict_energy_direct(payload: PredictionRequest, db: Session = Depends(get_db)):
    """
    Mandatory official assessment prediction endpoint.
    Accepts: quantity, machineHours, machineType, shift.
    Returns: estimatedEnergy, unit.
    """
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


# Also alias to /api/predict-energy for frontend consistency
@app.post(
    "/api/predict-energy",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prediction"],
    include_in_schema=False,
)
def predict_energy_alias(payload: PredictionRequest, db: Session = Depends(get_db)):
    return predict_energy_direct(payload=payload, db=db)


# Mount REST API Routers under /api
app.include_router(products_router, prefix="/api")
app.include_router(machine_types_router, prefix="/api")
app.include_router(shifts_router, prefix="/api")
app.include_router(production_batches_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
